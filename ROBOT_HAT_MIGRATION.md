# PiCar-X Robot Hat v4 Migration Guide

## Overview

The PiCar-X project has been refactored to use the **robot-hat** library instead of direct GPIO manipulation and Adafruit PCA9685 library. This provides better abstraction, improved compatibility, and simplified hardware management for the Sunfounder Robot Hat v4.

## What Changed

### 1. Dependencies

**Before:**
```
RPi.GPIO==0.7.0
adafruit-circuitpython-pca9685
```

**After:**
```
robot-hat
```

The `robot-hat` library provides a unified interface for all Robot Hat v4 components.

### 2. Motor Control

**Before (Direct GPIO):**
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(MOTOR_LEFT_FORWARD, GPIO.OUT)
pwm = GPIO.PWM(MOTOR_LEFT_FORWARD, 1000)
pwm.start(0)
pwm.ChangeDutyCycle(speed)
```

**After (robot-hat Motors):**
```python
from robot_hat import Motors

motors = Motors()
motors.set_left_id(1)
motors.set_right_id(2)
motors.left.speed(speed)
motors.right.speed(speed)
```

### 3. Servo Control

**Before (Adafruit PCA9685):**
```python
import board
import busio
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.channels[0].duty_cycle = value
```

**After (robot-hat Servo):**
```python
from robot_hat import Servo

pan_servo = Servo("P0")
pan_servo.angle(45)
```

### 4. Configuration

**Before:**
- GPIO pins defined by BCM numbering (e.g., 17, 18, 27, 22)
- PWM frequency configured separately
- I2C servo channels by index (0-15)

**After:**
- Pins use robot-hat naming (P0-P11 for servos, D0-D16 for GPIO)
- Motors use M1, M2 naming
- All hardware abstracted through robot-hat API

New config format in `config/config.py`:
```python
MOTOR_LEFT = "M1"
MOTOR_RIGHT = "M2"
SERVO_PAN_PIN = "P0"
SERVO_TILT_PIN = "P1"
```

## Hardware Mapping

### Motor Configuration (robot-hat)
- **M1**: Left motor
- **M2**: Right motor
- Speed range: -100 to 100 (negative = backward)

### Servo Configuration (robot-hat)
- **P0**: Pan servo (horizontal)
- **P1**: Tilt servo (vertical)
- Angle range: -90 to 90 degrees

## Benefits of Migration

1. **Simplified Hardware Abstraction**: Single library instead of multiple dependencies
2. **Better MCU Integration**: Direct access to Robot Hat v4 onboard MCU features
3. **Improved I2C Communication**: Unified I2C handling through robot-hat
4. **PWM Optimization**: MCU handles PWM directly instead of Raspberry Pi GPIO
5. **Reduced GPIO Load**: Pi GPIO usage is minimized
6. **Official Support**: Using SunFounder's official library for their hardware

## API Changes

### MotorController

```python
# Initialize
motor_ctrl = get_motor_controller()

# Set speeds (-100 to 100)
motor_ctrl.set_speed(left_speed, right_speed)
motor_ctrl.forward(speed=100)
motor_ctrl.backward(speed=100)
motor_ctrl.stop()

# Cleanup
motor_ctrl.cleanup()
```

### ServoController

```python
# Initialize
servo_ctrl = get_servo_controller()

# Set angles (-90 to 90 degrees)
servo_ctrl.set_pan(angle)
servo_ctrl.set_tilt(angle)
servo_ctrl.set_position(pan, tilt)
servo_ctrl.center()

# Cleanup
servo_ctrl.cleanup()
```

## Testing

Both controllers remain fully compatible with simulation mode. When `robot-hat` is not available:

```bash
# Simulation mode (works on any system)
python backend/app.py
# Output: Warning: robot_hat not available - running in simulation mode
```

## Installation on Raspberry Pi

1. Install robot-hat library:
```bash
sudo pip3 install robot-hat
```

Or use the provided installation methods:
```bash
uv pip install -r requirements.txt
```

2. Enable I2C interface:
```bash
sudo raspi-config
# → Interface Options → I2C → Enable
```

3. Enable Camera (if not already):
```bash
sudo raspi-config
# → Interface Options → Camera → Enable
```

## Troubleshooting

### I2C Communication Issues
```bash
# Check I2C devices
i2cdetect -y 1

# MCU should appear at address 0x14
```

### Motor Not Moving
- Ensure Motor Hat is powered with 6.0V-8.4V
- Check I2C communication with `i2cdetect`
- Verify motor connections to M1, M2 ports

### Servo Jitter
- Check power supply (should be stable 6.0V-8.4V)
- Verify servo connections to P0, P1 ports
- Check for loose servo horns

## References

- [robot-hat Documentation](https://github.com/sunfounder/robot-hat)
- [Robot Hat v4 Hardware](https://github.com/sunfounder/robot-hat/docs/hardware_introduction.rst)
- [robot-hat API Reference](https://github.com/sunfounder/robot-hat/docs/api)
