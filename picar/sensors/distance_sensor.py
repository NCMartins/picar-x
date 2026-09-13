"""Front-facing ultrasonic distance sensor, used to safeguard forward motion.

A single HC-SR04 read blocks for tens of milliseconds in the best case, and
up to its configured timeout when nothing is in range - too slow to do
inline every time something wants to drive, especially with the voice
agent's motor watchdog refresh every 250ms. Instead a background thread
polls continuously and caches the latest reading; ``MotorController`` reads
that cache, never the sensor directly.

The sensor is deliberately independent of any single caller. It exists
below both the manual web controls and the voice agent's movement budget, so
neither path can drive forward through it by construction.
"""

import logging
import threading
import time
from typing import Optional

from config.config import (
    DISTANCE_ECHO_PIN,
    DISTANCE_POLL_INTERVAL,
    DISTANCE_STALE_AFTER,
    DISTANCE_TRIG_PIN,
)
from ..hardware_component import HardwareComponent

try:
    from robot_hat import Pin, Ultrasonic
    ROBOT_HAT_AVAILABLE = True
except ImportError:
    ROBOT_HAT_AVAILABLE = False

HARDWARE_AVAILABLE = ROBOT_HAT_AVAILABLE

logger = logging.getLogger(__name__)
if not ROBOT_HAT_AVAILABLE:
    logger.warning("robot_hat not available - distance sensor running in simulation mode")


class DistanceSensor(HardwareComponent):
    """Polls the front-facing ultrasonic sensor on a background thread.

    ``sensor`` is injectable so tests can drive the polling/staleness logic
    with a fake that has a ``read(times=1)`` method, without real GPIO -
    the same shape as ``robot_hat.Ultrasonic``.
    """

    def __init__(self, sensor=None, auto_start: bool = True):
        super().__init__(HARDWARE_AVAILABLE or sensor is not None)
        self._sensor = sensor
        self._distance_cm: Optional[float] = None
        self._last_read_time: float = 0.0
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        if self.hardware_available:
            if self._sensor is None:
                self._init_sensor()
            else:
                self.initialized = True
            if auto_start and self.ready:
                self.start()

    def _init_sensor(self) -> None:
        try:
            self._sensor = Ultrasonic(Pin(DISTANCE_TRIG_PIN), Pin(DISTANCE_ECHO_PIN))
            self.initialized = True
            logger.info(
                "Distance sensor initialized (trig=%s, echo=%s)",
                DISTANCE_TRIG_PIN, DISTANCE_ECHO_PIN,
            )
        except Exception as e:
            logger.error("Error initializing distance sensor: %s", e)
            self._sensor = None

    # ---------- polling ----------

    def start(self) -> None:
        """Start the background poll thread. Safe to call more than once."""
        if not self.ready or (self._thread is not None and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._poll_loop, name="distance-sensor", daemon=True
        )
        self._thread.start()

    def cleanup(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _poll_loop(self) -> None:
        consecutive_failures = 0
        while not self._stop.is_set():
            try:
                # times=1: a single read, not the library's default retry-10.
                # A failed read is simply tried again next cycle instead of
                # blocking this thread for up to a second.
                self._record_reading(self._sensor.read(times=1))
                consecutive_failures = 0
            except Exception:
                # A sensor that's never been wired up fails every cycle,
                # forever - log once with the traceback, then back off to an
                # occasional reminder instead of flooding the log at 10Hz.
                consecutive_failures += 1
                if consecutive_failures == 1:
                    logger.exception(
                        "Distance sensor read failed; the obstacle safeguard "
                        "will fail open until a reading succeeds"
                    )
                elif consecutive_failures % 100 == 0:
                    logger.warning(
                        "Distance sensor still failing after %d attempts - "
                        "check the wiring on trig=%s echo=%s",
                        consecutive_failures, DISTANCE_TRIG_PIN, DISTANCE_ECHO_PIN,
                    )
            self._stop.wait(DISTANCE_POLL_INTERVAL)

    def _record_reading(self, cm: float) -> None:
        """Update cached state from one raw sensor reading.

        Separate from the poll loop so tests can drive it directly. HC-SR04
        semantics (matching ``robot_hat.Ultrasonic``): -1 means the echo
        timed out, which in practice means nothing is in range - a normal
        "clear ahead" result, not a failure. -2 means the read itself
        failed; the last known distance is kept and staleness takes over if
        failures keep happening.
        """
        if cm == -1:
            with self.lock:
                self._distance_cm = None
                self._last_read_time = time.monotonic()
        elif cm >= 0:
            with self.lock:
                self._distance_cm = cm
                self._last_read_time = time.monotonic()

    # ---------- reading ----------

    @property
    def distance_cm(self) -> Optional[float]:
        """Most recent distance ahead, in cm. None if nothing is in range."""
        with self.lock:
            return self._distance_cm

    @property
    def stale(self) -> bool:
        """True when no reading has landed recently enough to trust."""
        if not self.ready:
            return True
        with self.lock:
            last_read_time = self._last_read_time
        return last_read_time == 0.0 or (time.monotonic() - last_read_time) > DISTANCE_STALE_AFTER

    def is_clear(self, min_distance_cm: float) -> bool:
        """Whether it looks safe to drive forward.

        Fails open (returns True) in simulation mode and whenever readings
        have gone stale - a disconnected sensor or a flaky wire shouldn't
        permanently brick manual driving. That makes this a safeguard, not a
        guarantee: keep the car in sight.
        """
        if min_distance_cm <= 0 or not self.hardware_available:
            return True
        if self.stale:
            return True
        distance = self.distance_cm
        return distance is None or distance >= min_distance_cm


_distance_sensor: Optional[DistanceSensor] = None


def get_distance_sensor() -> DistanceSensor:
    """Get or create the distance sensor singleton."""
    global _distance_sensor
    if _distance_sensor is None:
        _distance_sensor = DistanceSensor()
    return _distance_sensor
