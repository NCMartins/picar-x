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

# Dead-man's switch: auto-stop the motors if no new command arrives within
# this many seconds while they're moving (e.g. dropped connection mid-drive).
MOTOR_WATCHDOG_TIMEOUT = 1.0
MOTOR_WATCHDOG_POLL_INTERVAL = 0.2

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


# ==================== Voice Assistant Configuration ====================
# Turns the PiCar into a voice-driven Claude: speech in, robot actions and
# spoken replies out. Everything here is off unless an API key is present,
# so an install that doesn't want it pays nothing for it.

# Claude API key. Read from the environment only - never commit a key.
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Master switch. Set PICAR_VOICE_ENABLED=0 to keep the routes registered but
# permanently refusing, even when a key is present.
VOICE_ENABLED = (
    os.getenv('PICAR_VOICE_ENABLED', '1').lower() not in ('0', 'false', 'no')
    and bool(ANTHROPIC_API_KEY)
)

VOICE_MODEL = os.getenv('PICAR_VOICE_MODEL', 'claude-opus-5')

# Effort trades thinking depth against latency. A voice loop is latency
# critical and the decisions are simple ("drive forward a bit", "what do you
# see"), so 'low' is the right default - raise it if you start asking the car
# to do genuinely multi-step things. Thinking itself stays on (adaptive):
# disabling it on Opus-class models makes them occasionally narrate a tool
# call as plain text instead of emitting a real one, which would silently
# drop a command here.
VOICE_EFFORT = os.getenv('PICAR_VOICE_EFFORT', 'low')

VOICE_MAX_TOKENS = int(os.getenv('PICAR_VOICE_MAX_TOKENS', '8192'))

# Hard ceiling on tool calls per spoken command. Stops a misunderstood
# instruction from turning into an unbounded drive-look-drive loop.
VOICE_MAX_TOOL_CALLS = int(os.getenv('PICAR_VOICE_MAX_TOOL_CALLS', '12'))

# How many conversation turns to keep. Each turn is a user message plus the
# assistant/tool exchange it triggered; older ones are dropped so a long
# session doesn't grow the request without bound.
VOICE_HISTORY_TURNS = int(os.getenv('PICAR_VOICE_HISTORY_TURNS', '12'))

# ---- Motion safety envelope ----
# The agent drives a real vehicle that can roll off a table, so its limits are
# deliberately tighter than the ones a human at the keyboard gets. Every
# motion tool clamps to these and stops itself when it's done; nothing the
# model can say makes the car move faster or longer than this allows.

# Top speed the agent may request (percent). Manual control still allows 100.
VOICE_MAX_SPEED = int(os.getenv('PICAR_VOICE_MAX_SPEED', '45'))

# Speed used when a command doesn't specify one.
VOICE_DEFAULT_SPEED = int(os.getenv('PICAR_VOICE_DEFAULT_SPEED', '30'))

# Longest single uninterrupted movement, in seconds.
VOICE_MAX_MOVE_SECONDS = float(os.getenv('PICAR_VOICE_MAX_MOVE_SECONDS', '2.0'))

# Total movement budget across all tool calls in one spoken command. Prevents
# "drive around the room" from becoming twenty chained 2-second hops.
VOICE_MAX_TOTAL_MOVE_SECONDS = float(
    os.getenv('PICAR_VOICE_MAX_TOTAL_MOVE_SECONDS', '8.0')
)

# How often a movement in progress checks whether it's been aborted.
VOICE_ABORT_POLL_INTERVAL = 0.05

# ---- Speech output ----
# Spoken replies go out of the Robot Hat speaker via espeak-ng. If espeak-ng
# isn't installed the agent still works - the reply just comes back as text
# for the browser to speak instead.
VOICE_TTS_ENABLED = (
    os.getenv('PICAR_VOICE_TTS_ENABLED', '1').lower() not in ('0', 'false', 'no')
)
VOICE_TTS_COMMAND = os.getenv('PICAR_VOICE_TTS_COMMAND', 'espeak-ng')
VOICE_TTS_VOICE = os.getenv('PICAR_VOICE_TTS_VOICE', 'en-us')
VOICE_TTS_WPM = int(os.getenv('PICAR_VOICE_TTS_WPM', '165'))
VOICE_TTS_AMPLITUDE = int(os.getenv('PICAR_VOICE_TTS_AMPLITUDE', '150'))

# ---- Speech input (optional, on-Pi microphone) ----
# The default input path is the browser's Web Speech API: your phone does the
# listening and POSTs text, which needs no extra hardware. Set this to use a
# USB mic plugged into the Pi instead, via faster-whisper.
VOICE_STT_MODEL = os.getenv('PICAR_VOICE_STT_MODEL', 'base.en')
VOICE_STT_DEVICE = os.getenv('PICAR_VOICE_STT_COMPUTE', 'int8')
