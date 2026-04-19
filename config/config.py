"""
Configuration for PiCar-X
"""

# Hardware Configuration
# Motor pins (BCM numbering)
MOTOR_LEFT_FORWARD = 17
MOTOR_LEFT_BACKWARD = 18
MOTOR_RIGHT_FORWARD = 27
MOTOR_RIGHT_BACKWARD = 22

# PWM Configuration
PWM_FREQUENCY = 1000  # 1 kHz
MAX_SPEED = 100  # 0-100%

# Servo Configuration (using PCA9685 or similar)
SERVO_PAN_CHANNEL = 0
SERVO_TILT_CHANNEL = 1
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# Camera Configuration
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
CAMERA_ROTATION = 0
STREAM_PORT = 8000
STREAM_QUALITY = 80  # 0-100

# Flask Configuration
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False

# Streaming Configuration
MJPEG_BOUNDARY = b'--BOUNDARY'
MJPEG_CONTENT_TYPE = 'multipart/x-mixed-replace; boundary=--BOUNDARY'
