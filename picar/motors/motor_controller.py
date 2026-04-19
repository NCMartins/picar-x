"""
Motor controller for PiCar-X movement control
Handles DC motors for forward/backward and left/right movement
"""

import threading
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
)

try:
    from robot_hat import MotorFactory, I2CDCMotorConfig, PWMDriverConfig
    ROBOT_HAT_AVAILABLE = True
except ImportError:
    ROBOT_HAT_AVAILABLE = False

HARDWARE_AVAILABLE = ROBOT_HAT_AVAILABLE
if not ROBOT_HAT_AVAILABLE:
    print("Warning: robot_hat not available - running in simulation mode")


def _resolve_motor_mapping(motor_name: str) -> Tuple[str, str]:
    """Resolve logical motor name (M1/M2) into PWM channel and direction pin."""
    mapping = {
        "M1": ("P13", "D4"),
        "M2": ("P12", "D5"),
    }
    return mapping.get(motor_name.upper(), mapping["M1"])


class MotorController:
    """Controls DC motors for PiCar-X movement"""
    
    def __init__(self):
        """Initialize motor controller"""
        self.left_speed = 0
        self.right_speed = 0
        self.left_motor = None
        self.right_motor = None
        self.lock = threading.Lock()
        self.initialized = False
        
        if HARDWARE_AVAILABLE:
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
            print("Motor controller initialized successfully")
        except Exception as e:
            print(f"Error initializing motors: {e}")
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
            # Clamp speeds
            left_speed = max(-MAX_SPEED, min(MAX_SPEED, left_speed))
            right_speed = max(-MAX_SPEED, min(MAX_SPEED, right_speed))
            
            self.left_speed = left_speed
            self.right_speed = right_speed
            
            if HARDWARE_AVAILABLE and self.initialized and self.left_motor and self.right_motor:
                self._apply_speed()
    
    def _apply_speed(self):
        """Apply current speeds to motors"""
        try:
            self.left_motor.set_speed(self.left_speed)
            self.right_motor.set_speed(self.right_speed)
        except Exception as e:
            print(f"Error setting motor speeds: {e}")
    
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
        if HARDWARE_AVAILABLE and self.initialized:
            try:
                self.stop()
                if self.left_motor:
                    self.left_motor.close()
                if self.right_motor:
                    self.right_motor.close()
                print("Motor controller cleaned up")
            except Exception as e:
                print(f"Error cleaning up motors: {e}")


# Singleton instance
_motor_controller = None


def get_motor_controller() -> MotorController:
    """Get or create motor controller singleton"""
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller
