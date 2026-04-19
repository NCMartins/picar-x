"""
Servo controller for PiCar-X camera pan/tilt control
Controls camera direction using servos
"""

import threading
from typing import Optional
import sys
from pathlib import Path
import inspect

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    SERVO_PAN_PIN, SERVO_TILT_PIN,
    SERVO_MIN_ANGLE, SERVO_MAX_ANGLE
)

try:
    from robot_hat import Servo, PWMFactory, PWMDriverConfig
    ROBOT_HAT_AVAILABLE = True
except ImportError:
    ROBOT_HAT_AVAILABLE = False

HARDWARE_AVAILABLE = ROBOT_HAT_AVAILABLE
if not ROBOT_HAT_AVAILABLE:
    print("Warning: robot_hat not available - running in simulation mode")


class ServoController:
    """Controls servos for camera pan/tilt movement"""
    
    def __init__(self):
        """Initialize servo controller"""
        self.pan_angle = 0
        self.tilt_angle = 0
        self.pan_servo = None
        self.tilt_servo = None
        self.pwm_driver = None
        self.lock = threading.Lock()
        self.initialized = False
        
        if HARDWARE_AVAILABLE:
            self._init_servos()
    
    def _init_servos(self):
        """Initialize robot_hat Servos"""
        try:
            servo_init_params = inspect.signature(Servo.__init__).parameters
            is_new_api = "driver" in servo_init_params and "channel" in servo_init_params

            if is_new_api:
                # robot-hat v2.3+ API: Servo(driver=..., channel=...)
                pwm_config = PWMDriverConfig(
                    address=0x14,
                    name="Sunfounder",
                    bus=1,
                    frame_width=20000,
                    freq=50,
                )
                self.pwm_driver = PWMFactory.create_pwm_driver(pwm_config)
                self.pwm_driver.set_pwm_freq(50)
                self.pan_servo = Servo(driver=self.pwm_driver, channel=SERVO_PAN_PIN)
                self.tilt_servo = Servo(driver=self.pwm_driver, channel=SERVO_TILT_PIN)
            else:
                # Legacy API compatibility: Servo(channel)
                pan_channel = int(SERVO_PAN_PIN[1:])
                tilt_channel = int(SERVO_TILT_PIN[1:])
                self.pan_servo = Servo(pan_channel)
                self.tilt_servo = Servo(tilt_channel)

            self.initialized = True
            print("Servo controller initialized successfully")
        except Exception as e:
            print(f"Error initializing servos: {e}")
            self.pan_servo = None
            self.tilt_servo = None
            if self.pwm_driver:
                try:
                    self.pwm_driver.close()
                except Exception:
                    pass
            self.pwm_driver = None
    
    def set_pan(self, angle: int) -> None:
        """
        Set pan angle
        
        Args:
            angle: Pan angle (-90 to 90 degrees)
        """
        with self.lock:
            angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
            self.pan_angle = angle
            
            if HARDWARE_AVAILABLE and self.initialized and self.pan_servo:
                self._apply_pan_angle()
    
    def set_tilt(self, angle: int) -> None:
        """
        Set tilt angle
        
        Args:
            angle: Tilt angle (-90 to 90 degrees)
        """
        with self.lock:
            angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
            self.tilt_angle = angle
            
            if HARDWARE_AVAILABLE and self.initialized and self.tilt_servo:
                self._apply_tilt_angle()
    
    def set_position(self, pan: int, tilt: int) -> None:
        """
        Set both pan and tilt angles
        
        Args:
            pan: Pan angle
            tilt: Tilt angle
        """
        self.set_pan(pan)
        self.set_tilt(tilt)
    
    def _apply_pan_angle(self):
        """Apply pan angle to servo"""
        try:
            self.pan_servo.angle(self.pan_angle)
        except Exception as e:
            print(f"Error setting pan servo: {e}")
    
    def _apply_tilt_angle(self):
        """Apply tilt angle to servo"""
        try:
            self.tilt_servo.angle(self.tilt_angle)
        except Exception as e:
            print(f"Error setting tilt servo: {e}")
    
    def center(self) -> None:
        """Center both pan and tilt"""
        self.set_position(0, 0)
    
    def cleanup(self):
        """Cleanup servo resources"""
        if HARDWARE_AVAILABLE and self.initialized:
            try:
                self.center()
                if self.pwm_driver:
                    self.pwm_driver.close()
                print("Servo controller cleaned up")
            except Exception as e:
                print(f"Error cleaning up servos: {e}")


# Singleton instance
_servo_controller = None


def get_servo_controller() -> ServoController:
    """Get or create servo controller singleton"""
    global _servo_controller
    if _servo_controller is None:
        _servo_controller = ServoController()
    return _servo_controller
