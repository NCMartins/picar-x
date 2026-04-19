"""Steering controller for PiCar-X front wheel steering."""

import inspect
import threading
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

try:
    from robot_hat import Servo, PWMFactory, PWMDriverConfig
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: robot_hat not available - steering in simulation mode")


class SteeringController:
    """Controls front wheel steering angle."""

    def __init__(self):
        self.angle = STEERING_CENTER_ANGLE
        self.servo = None
        self.pwm_driver = None
        self.lock = threading.Lock()
        self.initialized = False

        if HARDWARE_AVAILABLE:
            self._init_servo()

    def _init_servo(self):
        """Initialize steering servo with robot-hat API compatibility."""
        try:
            servo_init_params = inspect.signature(Servo.__init__).parameters
            is_new_api = "driver" in servo_init_params and "channel" in servo_init_params

            if is_new_api:
                pwm_config = PWMDriverConfig(
                    address=0x14,
                    name="Sunfounder",
                    bus=1,
                    frame_width=20000,
                    freq=50,
                )
                self.pwm_driver = PWMFactory.create_pwm_driver(pwm_config)
                self.pwm_driver.set_pwm_freq(50)
                self.servo = Servo(driver=self.pwm_driver, channel=STEERING_SERVO_PIN)
            else:
                channel = int(STEERING_SERVO_PIN[1:])
                self.servo = Servo(channel)

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
            if HARDWARE_AVAILABLE and self.initialized and self.servo:
                try:
                    self.servo.angle(self.angle)
                except Exception as e:
                    print(f"Error setting steering angle: {e}")

    def center(self) -> None:
        """Center steering."""
        self.set_angle(STEERING_CENTER_ANGLE)

    def cleanup(self):
        """Cleanup steering resources."""
        if HARDWARE_AVAILABLE and self.initialized:
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
