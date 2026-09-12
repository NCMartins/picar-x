"""
Motor controller for PiCar-X movement control
Handles DC motors for forward/backward and left/right movement
"""

import logging
import threading
import time
from typing import Optional, Tuple
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    MOTOR_LEFT, MOTOR_RIGHT,
    MAX_SPEED,
    MOTOR_LEFT_DIRECTION,
    MOTOR_RIGHT_DIRECTION,
    MOTOR_WATCHDOG_TIMEOUT,
    MOTOR_WATCHDOG_POLL_INTERVAL,
)
from ..hardware_component import HardwareComponent

try:
    from robot_hat import MotorFactory, I2CDCMotorConfig, PWMDriverConfig
    ROBOT_HAT_AVAILABLE = True
except ImportError:
    ROBOT_HAT_AVAILABLE = False

HARDWARE_AVAILABLE = ROBOT_HAT_AVAILABLE

logger = logging.getLogger(__name__)
if not ROBOT_HAT_AVAILABLE:
    logger.warning("robot_hat not available - running in simulation mode")


def _resolve_motor_mapping(motor_name: str) -> Tuple[str, str]:
    """Resolve logical motor name (M1/M2) into PWM channel and direction pin."""
    mapping = {
        "M1": ("P13", "D4"),
        "M2": ("P12", "D5"),
    }
    return mapping.get(motor_name.upper(), mapping["M1"])


class MotorController(HardwareComponent):
    """Controls DC motors for PiCar-X movement"""

    def __init__(self):
        """Initialize motor controller"""
        super().__init__(HARDWARE_AVAILABLE)
        self.left_speed = 0
        self.right_speed = 0
        self.left_motor = None
        self.right_motor = None

        # Dead-man's switch: auto-stop if no command refreshes the speed
        # within MOTOR_WATCHDOG_TIMEOUT seconds while the motors are moving
        # (e.g. the browser tab crashes or wifi drops mid-drive).
        self._last_command_time = time.monotonic()
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_stop = threading.Event()

        if self.hardware_available:
            self._init_motors()
    
    def _init_motors(self):
        """Initialize robot_hat motors using I2C driver API."""
        try:
            left_channel, left_dir_pin = _resolve_motor_mapping(MOTOR_LEFT)
            right_channel, right_dir_pin = _resolve_motor_mapping(MOTOR_RIGHT)

            driver_cfg = PWMDriverConfig(
                name="Sunfounder",
                bus=1,
                frame_width=20000,
                freq=50,
                address=0x14,
            )

            self.left_motor = MotorFactory.create_i2c_motor(
                config=I2CDCMotorConfig(
                    calibration_direction=MOTOR_LEFT_DIRECTION,
                    name="left_motor",
                    max_speed=MAX_SPEED,
                    driver=driver_cfg,
                    channel=left_channel,
                    dir_pin=left_dir_pin,
                )
            )
            self.right_motor = MotorFactory.create_i2c_motor(
                config=I2CDCMotorConfig(
                    calibration_direction=MOTOR_RIGHT_DIRECTION,
                    name="right_motor",
                    max_speed=MAX_SPEED,
                    driver=driver_cfg,
                    channel=right_channel,
                    dir_pin=right_dir_pin,
                )
            )

            self.initialized = True
            logger.info("Motor controller initialized successfully")
        except Exception as e:
            logger.error("Error initializing motors: %s", e)
            self.left_motor = None
            self.right_motor = None
    
    def set_speed(self, left_speed: int, right_speed: int) -> None:
        """
        Set motor speeds

        Args:
            left_speed: Left motor speed (-100 to 100)
            right_speed: Right motor speed (-100 to 100)
        """
        with self.lock:
            self._set_speed_locked(left_speed, right_speed)

    def _set_speed_locked(self, left_speed: int, right_speed: int) -> None:
        """Set motor speeds. Caller must already hold self.lock."""
        # Clamp speeds
        left_speed = max(-MAX_SPEED, min(MAX_SPEED, left_speed))
        right_speed = max(-MAX_SPEED, min(MAX_SPEED, right_speed))

        self.left_speed = left_speed
        self.right_speed = right_speed
        self._last_command_time = time.monotonic()

        if self.ready and self.left_motor and self.right_motor:
            self._apply_speed()

        self._update_watchdog()

    def _update_watchdog(self) -> None:
        """Start/stop the watchdog thread based on whether motors are moving. Caller must hold self.lock."""
        moving = self.left_speed != 0 or self.right_speed != 0
        if moving:
            if self._watchdog_thread is None or not self._watchdog_thread.is_alive():
                self._watchdog_stop.clear()
                self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
                self._watchdog_thread.start()
        else:
            self._watchdog_stop.set()

    def _watchdog_loop(self) -> None:
        """Auto-stop the motors if no new command arrives before the timeout."""
        while not self._watchdog_stop.wait(MOTOR_WATCHDOG_POLL_INTERVAL):
            with self.lock:
                if self.left_speed == 0 and self.right_speed == 0:
                    return
                if time.monotonic() - self._last_command_time >= MOTOR_WATCHDOG_TIMEOUT:
                    logger.warning(
                        "Motor watchdog: no command received for %ss, stopping motors",
                        MOTOR_WATCHDOG_TIMEOUT,
                    )
                    self._set_speed_locked(0, 0)
                    return

    def _apply_speed(self):
        """Apply current speeds to motors"""
        try:
            self.left_motor.set_speed(self.left_speed)
            self.right_motor.set_speed(self.right_speed)
        except Exception as e:
            logger.error("Error setting motor speeds: %s", e)
    
    def forward(self, speed: int = MAX_SPEED) -> None:
        """Move forward at specified speed"""
        self.set_speed(speed, speed)
    
    def backward(self, speed: int = MAX_SPEED) -> None:
        """Move backward at specified speed"""
        self.set_speed(-speed, -speed)
    
    def stop(self) -> None:
        """Stop all motors"""
        self.set_speed(0, 0)
    
    def cleanup(self):
        """Cleanup motor resources"""
        self._watchdog_stop.set()
        if self.ready:
            try:
                self.stop()
                if self.left_motor:
                    self.left_motor.close()
                if self.right_motor:
                    self.right_motor.close()
                logger.info("Motor controller cleaned up")
            except Exception as e:
                logger.error("Error cleaning up motors: %s", e)


# Singleton instance
_motor_controller = None


def get_motor_controller() -> MotorController:
    """Get or create motor controller singleton"""
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller
