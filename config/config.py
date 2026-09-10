"""
Configuration for PiCar-X
"""

import os

# Security Configuration
# Set PICAR_AUTH_USERNAME/PICAR_AUTH_PASSWORD to require HTTP Basic Auth on the
# web interface and API. Leave unset for local/trusted-network development
# only - the server will otherwise be reachable by anyone on the network.
AUTH_USERNAME = os.getenv('PICAR_AUTH_USERNAME', '')
AUTH_PASSWORD = os.getenv('PICAR_AUTH_PASSWORD', '')

# Comma-separated list of origins allowed to make cross-origin requests to the
# API, e.g. "http://192.168.1.50:3000,http://localhost:3000". Empty by default
# since the web interface is normally served same-origin and doesn't need CORS.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('PICAR_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]

# Hardware Configuration
# Motor pins (using robot-hat naming)
MOTOR_LEFT = "M1"  # Left motor
MOTOR_RIGHT = "M2"  # Right motor

# Servo pins (using robot-hat naming)
SERVO_PAN_PIN = "P0"  # Pan servo
SERVO_TILT_PIN = "P1"  # Tilt servo
STEERING_SERVO_PIN = "P2"  # Front wheel steering servo

# Servo Configuration
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# Steering Configuration
STEERING_MIN_ANGLE = -35
STEERING_MAX_ANGLE = 35
STEERING_CENTER_ANGLE = 0
STEERING_TURN_ANGLE = 25

# Motor Configuration
MAX_SPEED = 100  # 0-100%
MOTOR_LEFT_DIRECTION = 1
MOTOR_RIGHT_DIRECTION = -1

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
