"""Bounded robot primitives the voice agent is allowed to call.

This is the safety boundary between a language model and a vehicle that can
drive itself off a table. The controllers underneath (motors, steering,
servos, camera) happily accept any speed for any length of time; everything
here clamps to the ``VOICE_MAX_*`` envelope in ``config/config.py``, runs for
a bounded time, and stops the motors itself when it's done.

Three properties every motion primitive holds, and that the agent cannot
opt out of:

* **Self-terminating.** A movement runs for a clamped duration and then
  stops. There is no "start driving" primitive, so a dropped connection or a
  model that stops emitting tool calls can't leave the car moving.
* **Interruptible.** Movements sleep in short slices and check an abort
  event between them, so ``/api/voice/stop`` cuts a drive in progress
  instead of waiting for it to finish.
* **Budgeted.** Each spoken command gets a total movement budget. Once it's
  spent, further motion is refused and the refusal is handed back to the
  model as a tool result, so it can explain itself rather than silently
  failing.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from config.config import (
    STEERING_MAX_ANGLE,
    STEERING_MIN_ANGLE,
    SERVO_MAX_ANGLE,
    SERVO_MIN_ANGLE,
    VOICE_ABORT_POLL_INTERVAL,
    VOICE_DEFAULT_SPEED,
    VOICE_MAX_MOVE_SECONDS,
    VOICE_MAX_SPEED,
    VOICE_MAX_TOTAL_MOVE_SECONDS,
)

logger = logging.getLogger(__name__)


class MovementBudgetExceeded(RuntimeError):
    """Raised when a command has used up its total movement allowance."""


class MovementAborted(RuntimeError):
    """Raised when an emergency stop interrupted a movement."""


@dataclass
class ActionRecord:
    """One executed skill, for the UI's activity log and for tests."""

    name: str
    detail: str
    aborted: bool = False
    fields: dict = field(default_factory=dict)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class RobotSkills:
    """The robot's capability surface, as the voice agent sees it.

    Holds no conversation state - it's a thin, stateless-per-command wrapper
    over the existing controller singletons, plus the movement budget and
    abort flag for the command currently running.
    """

    def __init__(self, motor_ctrl, steering_ctrl, servo_ctrl, camera_stream):
        self._motors = motor_ctrl
        self._steering = steering_ctrl
        self._servos = servo_ctrl
        self._camera = camera_stream

        self._abort = threading.Event()
        self._budget_lock = threading.Lock()
        self._spent_seconds = 0.0
        self.actions: list[ActionRecord] = []

    # ---------- command lifecycle ----------

    def begin_command(self) -> None:
        """Reset the per-command movement budget, abort flag and action log."""
        self._abort.clear()
        with self._budget_lock:
            self._spent_seconds = 0.0
        self.actions = []

    def abort(self) -> None:
        """Cut any movement in progress and stop the motors immediately.

        Safe to call from another thread (that's the point) - the Flask
        request handling ``/api/voice/stop`` calls this while the agent
        thread is mid-drive.
        """
        self._abort.set()
        try:
            self._motors.stop()
            self._steering.center()
        except Exception:
            logger.exception("Error stopping motors during abort")

    @property
    def aborted(self) -> bool:
        return self._abort.is_set()

    @property
    def budget_remaining(self) -> float:
        with self._budget_lock:
            return max(0.0, VOICE_MAX_TOTAL_MOVE_SECONDS - self._spent_seconds)

    def _charge_budget(self, seconds: float) -> None:
        """Reserve `seconds` of movement, or refuse if the budget is spent."""
        with self._budget_lock:
            if self._spent_seconds + seconds > VOICE_MAX_TOTAL_MOVE_SECONDS:
                remaining = max(0.0, VOICE_MAX_TOTAL_MOVE_SECONDS - self._spent_seconds)
                raise MovementBudgetExceeded(
                    f"Movement budget for this command is spent "
                    f"({VOICE_MAX_TOTAL_MOVE_SECONDS:.1f}s total, {remaining:.1f}s left). "
                    f"Ask the operator to repeat the command to get a fresh budget."
                )
            self._spent_seconds += seconds

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep in abort-checking slices. Returns False if aborted."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._abort.is_set():
                return False
            remaining = deadline - time.monotonic()
            time.sleep(min(VOICE_ABORT_POLL_INTERVAL, max(0.0, remaining)))
        return not self._abort.is_set()

    def _record(self, name: str, detail: str, aborted: bool = False, **fields) -> ActionRecord:
        record = ActionRecord(name=name, detail=detail, aborted=aborted, fields=fields)
        self.actions.append(record)
        return record

    # ---------- motion ----------

    def drive(
        self,
        direction: str,
        duration_seconds: float = 1.0,
        speed: Optional[int] = None,
        steering_angle: int = 0,
    ) -> str:
        """Drive forward or backward for a bounded time, then stop.

        Returns a human-readable result string that goes straight back to the
        model as the tool result.
        """
        if direction not in ("forward", "backward"):
            raise ValueError("direction must be 'forward' or 'backward'")

        speed = VOICE_DEFAULT_SPEED if speed is None else int(speed)
        speed = int(_clamp(abs(speed), 0, VOICE_MAX_SPEED))
        duration = _clamp(float(duration_seconds), 0.0, VOICE_MAX_MOVE_SECONDS)
        angle = int(_clamp(int(steering_angle), STEERING_MIN_ANGLE, STEERING_MAX_ANGLE))

        if self._abort.is_set():
            raise MovementAborted("Emergency stop is active; movement refused.")

        self._charge_budget(duration)

        self._steering.set_angle(angle)
        if direction == "forward":
            self._motors.forward(speed)
        else:
            self._motors.backward(speed)

        # The motor watchdog in MotorController would stop us anyway if this
        # thread died, but drive the refresh explicitly: the watchdog timeout
        # (1s) is shorter than the longest movement we allow.
        completed = self._drive_for(duration, direction, speed)

        self._motors.stop()
        self._steering.center()

        detail = (
            f"{direction} at {speed}% for {duration:.1f}s"
            + (f", steering {angle}deg" if angle else "")
        )
        if not completed:
            self._record("drive", detail, aborted=True, speed=speed, duration=duration)
            raise MovementAborted(f"Emergency stop during: {detail}")

        self._record("drive", detail, speed=speed, duration=duration, direction=direction)
        return (
            f"Drove {detail} and stopped. "
            f"Movement budget left this command: {self.budget_remaining:.1f}s."
        )

    def _drive_for(self, duration: float, direction: str, speed: int) -> bool:
        """Hold a drive for `duration`, refreshing the motor watchdog.

        The motor controller stops itself if no command arrives within
        MOTOR_WATCHDOG_TIMEOUT, which is shorter than our maximum movement.
        Re-issuing the same speed on each slice keeps a legitimate long
        movement alive without weakening the watchdog for anything else.
        """
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if self._abort.is_set():
                return False
            slice_seconds = min(0.25, max(0.0, deadline - time.monotonic()))
            if not self._sleep_interruptible(slice_seconds):
                return False
            if time.monotonic() < deadline:
                if direction == "forward":
                    self._motors.forward(speed)
                else:
                    self._motors.backward(speed)
        return True

    def turn(
        self,
        direction: str,
        duration_seconds: float = 1.0,
        speed: Optional[int] = None,
        sharpness: float = 1.0,
    ) -> str:
        """Turn left or right by driving forward with the wheels steered.

        The PiCar steers with a front servo, so it turns only while driving -
        it can't pivot in place. `sharpness` (0-1) scales how far the wheels
        are turned.
        """
        if direction not in ("left", "right"):
            raise ValueError("direction must be 'left' or 'right'")

        limit = STEERING_MAX_ANGLE if direction == "right" else abs(STEERING_MIN_ANGLE)
        angle = int(_clamp(abs(sharpness), 0.0, 1.0) * limit)
        if direction == "left":
            angle = -angle

        result = self.drive(
            "forward",
            duration_seconds=duration_seconds,
            speed=speed,
            steering_angle=angle,
        )
        # drive() already logged itself; relabel for a clearer activity log.
        if self.actions:
            self.actions[-1].name = "turn"
            self.actions[-1].detail = f"{direction} ({angle}deg) " + self.actions[-1].detail
        return result

    def stop(self) -> str:
        """Stop the motors and centre the steering."""
        self._motors.stop()
        self._steering.center()
        self._record("stop", "motors stopped, steering centred")
        return "Stopped. Motors at zero, steering centred."

    # ---------- looking ----------

    def look(self, pan: Optional[int] = None, tilt: Optional[int] = None) -> str:
        """Aim the camera. Pan is left/right, tilt is down/up, both in degrees."""
        target_pan = self._servos.pan_angle if pan is None else int(
            _clamp(int(pan), SERVO_MIN_ANGLE, SERVO_MAX_ANGLE)
        )
        target_tilt = self._servos.tilt_angle if tilt is None else int(
            _clamp(int(tilt), SERVO_MIN_ANGLE, SERVO_MAX_ANGLE)
        )
        self._servos.set_position(target_pan, target_tilt)
        # Servos need a moment to travel before a capture is worth taking.
        self._sleep_interruptible(0.4)
        self._record("look", f"camera to pan {target_pan}deg, tilt {target_tilt}deg",
                     pan=target_pan, tilt=target_tilt)
        return f"Camera aimed at pan {target_pan} degrees, tilt {target_tilt} degrees."

    def capture_view(self) -> Optional[bytes]:
        """Grab a single JPEG frame for the model to look at."""
        frame = self._camera.get_frame()
        if frame:
            self._record("see", f"captured a {len(frame)} byte frame", bytes=len(frame))
        return frame

    # ---------- state ----------

    def get_state(self) -> dict:
        """Everything the model can know about the robot's current pose."""
        return {
            "left_motor_speed": self._motors.left_speed,
            "right_motor_speed": self._motors.right_speed,
            "moving": self._motors.left_speed != 0 or self._motors.right_speed != 0,
            "steering_angle": self._steering.angle,
            "camera_pan": self._servos.pan_angle,
            "camera_tilt": self._servos.tilt_angle,
            "camera_available": self._camera.initialized,
            "hardware_connected": self._motors.ready,
            "movement_budget_remaining_seconds": round(self.budget_remaining, 1),
        }
