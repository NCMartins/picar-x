# Using robot-hat Library in PiCar-X

## Quick Start Examples

### Motor Control

```python
from picar.motors import get_motor_controller

motor = get_motor_controller()

# Move forward
motor.forward(speed=80)

# Turn left (left motor slower)
motor.set_speed(50, 100)

# Move backward
motor.backward(speed=60)

# Stop
motor.stop()

# Cleanup when done
motor.cleanup()
```

### Servo Control

```python
from picar.servos import get_servo_controller

servo = get_servo_controller()

# Pan right
servo.set_pan(45)

# Tilt down
servo.set_tilt(-30)

# Move to specific position
servo.set_position(pan=45, tilt=-30)

# Center camera
servo.center()

# Cleanup when done
servo.cleanup()
```

### REST API Endpoints

All endpoints work through the Flask backend and use robot-hat internally:

```bash
# Motors
curl -X POST http://localhost:5000/api/motors/forward -d '{"speed": 100}' -H "Content-Type: application/json"
curl -X POST http://localhost:5000/api/motors/backward -d '{"speed": 80}' -H "Content-Type: application/json"
curl -X POST http://localhost:5000/api/motors/stop
curl -X POST http://localhost:5000/api/motors/set-speed -d '{"left_speed": 50, "right_speed": 80}' -H "Content-Type: application/json"

# Camera
curl -X POST http://localhost:5000/api/camera/pan -d '{"angle": 45}' -H "Content-Type: application/json"
curl -X POST http://localhost:5000/api/camera/tilt -d '{"angle": -30}' -H "Content-Type: application/json"
curl -X POST http://localhost:5000/api/camera/position -d '{"pan": 45, "tilt": -30}' -H "Content-Type: application/json"
curl -X POST http://localhost:5000/api/camera/center
```

## robot-hat Library Features

The library provides comprehensive support for Robot Hat v4:

### Available Classes

```python
from robot_hat import (
    Pin,      # GPIO control
    PWM,      # PWM output
    ADC,      # Analog input
    Motor,    # Single motor
    Motors,   # Motor group
    Servo,    # Servo control
    Robot,    # Robot arm kinematics
    Ultrasonic,  # Distance sensor
    ADXL345,  # Accelerometer
)
```

### GPIO Control (robot-hat Pin)

```python
from robot_hat import Pin

# Using named pins
led = Pin("LED")
user_button = Pin("USER", Pin.IN, Pin.PULL_UP)

# Set/get values
led.on()
led.off()
is_pressed = user_button.value()
```

### PWM Control (robot-hat PWM)

```python
from robot_hat import PWM

# PWM on any channel (0-11 for external, 12-15 onboard motor driver)
pwm = PWM(0)
pwm.freq(1000)  # 1kHz frequency
pwm.pulse_width_percent(50)  # 50% duty cycle
```

### ADC Input (robot-hat ADC)

```python
from robot_hat import ADC

# Read analog inputs A0-A3
battery = ADC("A4")  # Battery voltage
value = battery.read()  # 0-4095
voltage = battery.read_voltage()  # 0-3.3V (scaled to 0-10V)
```

### Advanced Motor Control

```python
from robot_hat import Motors

motors = Motors()
motors.set_left_id(1)
motors.set_right_id(2)

# Direct speed control
motors.left.speed(100)  # Full forward
motors.right.speed(-50)  # Half speed backward

# Access by index
motors[1].speed(75)
motors[2].speed(75)

# Stop all motors
motors.stop()
```

### Servo Arrays

```python
from robot_hat import Servo, Robot

# For robot arms (multiple servos)
robot = Robot([0, 1, 2, 3], name="arm")  # 4 servos on pins 0-3
robot.servo_move([0, 45, -45, 0], speed=50)  # Move to positions
```

## Hardware Specifications (Robot Hat v4)

### Power
- Input: 6.0V-8.4V XH2.54 3pin connector
- Recommended: 7.4V (2S LiPo) or 6xAA batteries

### GPIO Ports
- D0-D16: Digital I/O pins (mapped to Raspberry Pi GPIO)
- Each can be configured as input with pull-up/pull-down

### Motor Driver
- M1, M2: DC motor connectors (0-5A per motor)
- PWM control with direction
- Can handle 6.0V-8.4V input

### Servo Ports
- P0-P11: 12 servo channels (4-6V operation)
- Standard 50Hz PWM servo control
- Simultaneous servo movement support

### Analog Inputs
- A0-A3: 12-bit ADC on onboard MCU
- A4: Battery voltage monitor (10V range)

### I2C Interface
- SH1.0 4-pin connector (QWIIC/STEMMA QT compatible)
- P2.54 4-pin connector (standard I2C)
- MCU I2C address: 0x14

### Special Features
- Onboard MCU: AT32F415 (ARM Cortex-M4 @ 150MHz)
- LED: GPIO26
- User Button: GPIO25
- Reset Button: GPIO16
- I2S Audio Output (3.5mm jack)
- Speaker: 2030 mono speaker

## Common Patterns

### Safe Motor Initialization

```python
try:
    motor = get_motor_controller()
    motor.forward(speed=75)
    # ... operations ...
except Exception as e:
    print(f"Motor error: {e}")
finally:
    motor.cleanup()
```

### Servo Sweep

```python
import time
from picar.servos import get_servo_controller

servo = get_servo_controller()
servo.center()
time.sleep(0.5)

for angle in range(-90, 91, 10):
    servo.set_pan(angle)
    time.sleep(0.1)

servo.center()
servo.cleanup()
```

### Coordinated Movement

```python
from picar.motors import get_motor_controller
from picar.servos import get_servo_controller

motor = get_motor_controller()
servo = get_servo_controller()

# Move forward while panning
servo.set_pan(45)
motor.forward(speed=60)
time.sleep(2)

motor.stop()
servo.center()

motor.cleanup()
servo.cleanup()
```

## Troubleshooting with robot-hat

### Check I2C Communication
```bash
# Verify MCU is detected at 0x14
i2cdetect -y 1

# Output should show:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:                         -- -- -- -- -- -- -- --
# 10: -- -- -- -- 14 -- -- -- -- -- -- -- -- -- -- --
# ...
```

### Reset MCU
```bash
python3 -c "from robot_hat import reset_mcu; reset_mcu()"
```

### Get Device Info
```bash
robot-hat info  # View Robot Hat info
robot-hat version  # View library version
```

## Performance Tips

1. **Motor Control**: Use `set_speed()` for simultaneous control of both motors
2. **Servo Movement**: Group servo updates to reduce I2C traffic
3. **Battery Voltage**: Monitor with `ADC("A4")` for low battery detection
4. **Power Supply**: Use stable 6.0V-8.4V for optimal performance

## References

- [robot-hat GitHub](https://github.com/sunfounder/robot-hat)
- [Robot Hat v4 Specifications](https://github.com/sunfounder/robot-hat/docs/hardware_introduction.rst)
- [robot-hat API Documentation](https://github.com/sunfounder/robot-hat/docs/api.rst)
- [Installation Guide](https://github.com/sunfounder/robot-hat#installation)
