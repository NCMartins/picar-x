"""Steering controller for PiCar-X front wheel steering."""

import json
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    STEERING_SERVO_PIN,
    STEERING_MIN_ANGLE,
    STEERING_MAX_ANGLE,
    STEERING_CENTER_ANGLE,
)
from ..hardware_component import HardwareComponent
from ..pwm import ROBOT_HAT_AVAILABLE, create_pwm_driver, create_servo

HARDWARE_AVAILABLE = ROBOT_HAT_AVAILABLE
if not ROBOT_HAT_AVAILABLE:
    print("Warning: robot_hat not available - steering in simulation mode")


class SteeringController(HardwareComponent):
    """Controls front wheel steering angle."""

    def __init__(self):
        super().__init__(HARDWARE_AVAILABLE)
        self.angle = STEERING_CENTER_ANGLE
        self.calibration_offset = 0
        self._calibration_file = Path(__file__).parent.parent.parent / 'config' / 'steering_calibration.json'
        self.servo = None
        self.pwm_driver = None
        self._load_calibration()

        if self.hardware_available:
            self._init_servo()

    def _load_calibration(self) -> None:
        """Load steering calibration offset from disk if present."""
        try:
            if self._calibration_file.exists():
                with self._calibration_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.calibration_offset = int(data.get('offset', 0))
        except Exception as e:
            print(f"Warning: failed to load steering calibration: {e}")
            self.calibration_offset = 0

    def _save_calibration(self) -> None:
        """Persist steering calibration offset to disk."""
        try:
            self._calibration_file.parent.mkdir(parents=True, exist_ok=True)
            with self._calibration_file.open('w', encoding='utf-8') as f:
                json.dump({'offset': self.calibration_offset}, f, indent=2)
        except Exception as e:
            print(f"Warning: failed to save steering calibration: {e}")

    def _init_servo(self):
        """Initialize steering servo with robot-hat API compatibility."""
        try:
            self.pwm_driver = create_pwm_driver()
            self.servo = create_servo(STEERING_SERVO_PIN, self.pwm_driver)

            self.initialized = True
            self.center()
            print("Steering controller initialized successfully")
        except Exception as e:
            print(f"Error initializing steering servo: {e}")
            self.servo = None
            if self.pwm_driver:
                try:
                    self.pwm_driver.close()
                except Exception:
                    pass
            self.pwm_driver = None

    def set_angle(self, angle: int) -> None:
        """Set steering angle in degrees."""
        with self.lock:
            clamped = max(STEERING_MIN_ANGLE, min(STEERING_MAX_ANGLE, angle))
            self.angle = clamped
            physical_angle = max(
                STEERING_MIN_ANGLE,
                min(STEERING_MAX_ANGLE, self.angle + self.calibration_offset),
            )
            if self.ready and self.servo:
                try:
                    self.servo.angle(physical_angle)
                except Exception as e:
                    print(f"Error setting steering angle: {e}")

    def set_calibration_offset(self, offset: int) -> None:
        """Set and persist calibration offset used for all steering positions."""
        with self.lock:
            self.calibration_offset = int(offset)
            self._save_calibration()
        # Re-apply current logical angle using the new offset.
        self.set_angle(self.angle)

    def reset_calibration(self) -> None:
        """Reset steering calibration offset to zero and persist."""
        self.set_calibration_offset(0)

    def center(self) -> None:
        """Center steering."""
        self.set_angle(STEERING_CENTER_ANGLE)

    def cleanup(self):
        """Cleanup steering resources."""
        if self.ready:
            try:
                self.center()
                if self.pwm_driver:
                    self.pwm_driver.close()
                print("Steering controller cleaned up")
            except Exception as e:
                print(f"Error cleaning up steering: {e}")


_steering_controller = None


def get_steering_controller() -> SteeringController:
    """Get or create steering controller singleton."""
    global _steering_controller
    if _steering_controller is None:
        _steering_controller = SteeringController()
    return _steering_controller
