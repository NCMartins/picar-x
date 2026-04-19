"""
Servo controller for PiCar-X camera pan/tilt control
Controls camera direction using servos
"""

import threading
from typing import Optional
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    SERVO_PAN_CHANNEL, SERVO_TILT_CHANNEL,
    SERVO_MIN_ANGLE, SERVO_MAX_ANGLE
)

try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: Adafruit PCA9685 not available - running in simulation mode")


class ServoController:
    """Controls servos for camera pan/tilt movement"""
    
    def __init__(self):
        """Initialize servo controller"""
        self.pan_angle = 0
        self.tilt_angle = 0
        self.pca = None
        self.lock = threading.Lock()
        self.initialized = False
        
        if HARDWARE_AVAILABLE:
            self._init_pca9685()
    
    def _init_pca9685(self):
        """Initialize PCA9685 servo driver"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.pca = PCA9685(i2c)
            self.pca.frequency = 50  # 50 Hz for servo control
            self.initialized = True
            print("Servo controller initialized successfully")
        except Exception as e:
            print(f"Error initializing PCA9685: {e}")
            self.pca = None
    
    def set_pan(self, angle: int) -> None:
        """
        Set pan angle
        
        Args:
            angle: Pan angle (-90 to 90 degrees)
        """
        with self.lock:
            angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
            self.pan_angle = angle
            
            if HARDWARE_AVAILABLE and self.initialized and self.pca:
                self._apply_angle(SERVO_PAN_CHANNEL, angle)
    
    def set_tilt(self, angle: int) -> None:
        """
        Set tilt angle
        
        Args:
            angle: Tilt angle (-90 to 90 degrees)
        """
        with self.lock:
            angle = max(SERVO_MIN_ANGLE, min(SERVO_MAX_ANGLE, angle))
            self.tilt_angle = angle
            
            if HARDWARE_AVAILABLE and self.initialized and self.pca:
                self._apply_angle(SERVO_TILT_CHANNEL, angle)
    
    def set_position(self, pan: int, tilt: int) -> None:
        """
        Set both pan and tilt angles
        
        Args:
            pan: Pan angle
            tilt: Tilt angle
        """
        self.set_pan(pan)
        self.set_tilt(tilt)
    
    def _apply_angle(self, channel: int, angle: int):
        """Apply servo angle using PWM pulse width"""
        # Convert angle (-90 to 90) to pulse width (1000 to 2000 microseconds at 50Hz)
        # Center position (0°) = 1500 microseconds (7.5% duty cycle)
        # Min position (-90°) = 1000 microseconds (5% duty cycle)
        # Max position (90°) = 2000 microseconds (10% duty cycle)
        
        pulse_width = 1500 + (angle * 5.55)  # 5.55 microseconds per degree
        duty_cycle = (pulse_width / 20000) * 65535  # Convert to PCA9685 value
        
        try:
            self.pca.channels[channel].duty_cycle = int(duty_cycle)
        except Exception as e:
            print(f"Error setting servo: {e}")
    
    def center(self) -> None:
        """Center both pan and tilt"""
        self.set_position(0, 0)
    
    def cleanup(self):
        """Cleanup servo resources"""
        if self.pca:
            try:
                self.center()
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
