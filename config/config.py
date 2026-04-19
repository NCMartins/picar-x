"""
Configuration for PiCar-X
"""

# Hardware Configuration
# Motor pins (using robot-hat naming)
MOTOR_LEFT = "M1"  # Left motor
MOTOR_RIGHT = "M2"  # Right motor

# Servo pins (using robot-hat naming)
SERVO_PAN_PIN = "P0"  # Pan servo
SERVO_TILT_PIN = "P1"  # Tilt servo

# Servo Configuration
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# Motor Configuration
MAX_SPEED = 100  # 0-100%

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
