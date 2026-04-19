"""
Motor controller for PiCar-X movement control
Handles DC motors for forward/backward and left/right movement
"""

import threading
from typing import Optional
import sys
from pathlib import Path

# Add config to path
config_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(config_path))

from config.config import (
    MOTOR_LEFT_FORWARD, MOTOR_LEFT_BACKWARD,
    MOTOR_RIGHT_FORWARD, MOTOR_RIGHT_BACKWARD,
    PWM_FREQUENCY, MAX_SPEED
)

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: RPi.GPIO not available - running in simulation mode")


class MotorController:
    """Controls DC motors for PiCar-X movement"""
    
    def __init__(self):
        """Initialize motor controller"""
        self.left_speed = 0
        self.right_speed = 0
        self.pwm_left_forward = None
        self.pwm_left_backward = None
        self.pwm_right_forward = None
        self.pwm_right_backward = None
        self.lock = threading.Lock()
        self.initialized = False
        
        if HARDWARE_AVAILABLE:
            self._init_gpio()
    
    def _init_gpio(self):
        """Initialize GPIO pins for motor control"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup pins as output
            pins = [MOTOR_LEFT_FORWARD, MOTOR_LEFT_BACKWARD,
                   MOTOR_RIGHT_FORWARD, MOTOR_RIGHT_BACKWARD]
            for pin in pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            # Setup PWM on each pin
            self.pwm_left_forward = GPIO.PWM(MOTOR_LEFT_FORWARD, PWM_FREQUENCY)
            self.pwm_left_backward = GPIO.PWM(MOTOR_LEFT_BACKWARD, PWM_FREQUENCY)
            self.pwm_right_forward = GPIO.PWM(MOTOR_RIGHT_FORWARD, PWM_FREQUENCY)
            self.pwm_right_backward = GPIO.PWM(MOTOR_RIGHT_BACKWARD, PWM_FREQUENCY)
            
            # Start PWM at 0%
            for pwm in [self.pwm_left_forward, self.pwm_left_backward,
                       self.pwm_right_forward, self.pwm_right_backward]:
                pwm.start(0)
            
            self.initialized = True
            print("Motor controller initialized successfully")
        except Exception as e:
            print(f"Error initializing GPIO: {e}")
            HARDWARE_AVAILABLE = False
    
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
            
            if HARDWARE_AVAILABLE and self.initialized:
                self._apply_speed()
    
    def _apply_speed(self):
        """Apply current speeds to motors"""
        # Left motor
        if self.left_speed > 0:
            self.pwm_left_forward.ChangeDutyCycle(self.left_speed)
            self.pwm_left_backward.ChangeDutyCycle(0)
        elif self.left_speed < 0:
            self.pwm_left_forward.ChangeDutyCycle(0)
            self.pwm_left_backward.ChangeDutyCycle(abs(self.left_speed))
        else:
            self.pwm_left_forward.ChangeDutyCycle(0)
            self.pwm_left_backward.ChangeDutyCycle(0)
        
        # Right motor
        if self.right_speed > 0:
            self.pwm_right_forward.ChangeDutyCycle(self.right_speed)
            self.pwm_right_backward.ChangeDutyCycle(0)
        elif self.right_speed < 0:
            self.pwm_right_forward.ChangeDutyCycle(0)
            self.pwm_right_backward.ChangeDutyCycle(abs(self.right_speed))
        else:
            self.pwm_right_forward.ChangeDutyCycle(0)
            self.pwm_right_backward.ChangeDutyCycle(0)
    
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
        """Cleanup GPIO resources"""
        if HARDWARE_AVAILABLE and self.initialized:
            try:
                for pwm in [self.pwm_left_forward, self.pwm_left_backward,
                           self.pwm_right_forward, self.pwm_right_backward]:
                    if pwm:
                        pwm.stop()
                GPIO.cleanup()
                print("Motor controller cleaned up")
            except Exception as e:
                print(f"Error cleaning up GPIO: {e}")


# Singleton instance
_motor_controller = None


def get_motor_controller() -> MotorController:
    """Get or create motor controller singleton"""
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller
