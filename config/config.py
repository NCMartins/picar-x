"""
Configuration for PiCar-X

Deployment-varying settings are read from the environment, with the values
below as defaults. That keeps one source of truth: a deployment (Ansible, a
systemd unit, a shell profile) overrides what it needs through the
environment instead of shipping its own rewritten copy of this file, which is
how the two drift apart and stop importing.
"""

import os


def _env_int(name: str, default: int) -> int:
    """Read an integer setting, falling back to the default if unparseable."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_flag(name: str, default: bool) -> bool:
    """Read a boolean setting written as 1/0, true/false or yes/no."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ('0', 'false', 'no', '')

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
MOTOR_LEFT = os.getenv('PICAR_MOTOR_LEFT', 'M1')  # Left motor
MOTOR_RIGHT = os.getenv('PICAR_MOTOR_RIGHT', 'M2')  # Right motor

# Servo pins (using robot-hat naming)
SERVO_PAN_PIN = os.getenv('PICAR_SERVO_PAN_PIN', 'P0')  # Pan servo
SERVO_TILT_PIN = os.getenv('PICAR_SERVO_TILT_PIN', 'P1')  # Tilt servo
STEERING_SERVO_PIN = os.getenv('PICAR_STEERING_SERVO_PIN', 'P2')  # Front wheel steering

# Servo Configuration
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90

# Steering Configuration
STEERING_MIN_ANGLE = -35
STEERING_MAX_ANGLE = 35
STEERING_CENTER_ANGLE = 0
STEERING_TURN_ANGLE = 25

# Motor Configuration
MAX_SPEED = _env_int('PICAR_MAX_SPEED', 100)  # 0-100%
MOTOR_LEFT_DIRECTION = _env_int('PICAR_MOTOR_LEFT_DIRECTION', 1)
MOTOR_RIGHT_DIRECTION = _env_int('PICAR_MOTOR_RIGHT_DIRECTION', -1)

# Dead-man's switch: auto-stop the motors if no new command arrives within
# this many seconds while they're moving (e.g. dropped connection mid-drive).
MOTOR_WATCHDOG_TIMEOUT = 1.0
MOTOR_WATCHDOG_POLL_INTERVAL = 0.2

# Camera Configuration
CAMERA_RESOLUTION = (
    _env_int('PICAR_CAMERA_WIDTH', 640),
    _env_int('PICAR_CAMERA_HEIGHT', 480),
)
CAMERA_FRAMERATE = _env_int('PICAR_CAMERA_FRAMERATE', 30)
CAMERA_ROTATION = _env_int('PICAR_CAMERA_ROTATION', 0)
STREAM_PORT = _env_int('PICAR_STREAM_PORT', 8000)
STREAM_QUALITY = _env_int('PICAR_STREAM_QUALITY', 80)  # 0-100

# Flask Configuration
FLASK_HOST = os.getenv('PICAR_FLASK_HOST', '0.0.0.0')
FLASK_PORT = _env_int('PICAR_FLASK_PORT', 5000)
FLASK_DEBUG = _env_flag('PICAR_FLASK_DEBUG', False)

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
VOICE_ENABLED = _env_flag('PICAR_VOICE_ENABLED', True) and bool(ANTHROPIC_API_KEY)

VOICE_MODEL = os.getenv('PICAR_VOICE_MODEL', 'claude-opus-5')

# Effort trades thinking depth against latency. A voice loop is latency
# critical and the decisions are simple ("drive forward a bit", "what do you
# see"), so 'low' is the right default - raise it if you start asking the car
# to do genuinely multi-step things. Thinking itself stays on (adaptive):
# disabling it on Opus-class models makes them occasionally narrate a tool
# call as plain text instead of emitting a real one, which would silently
# drop a command here.
VOICE_EFFORT = os.getenv('PICAR_VOICE_EFFORT', 'low')

VOICE_MAX_TOKENS = _env_int('PICAR_VOICE_MAX_TOKENS', 8192)

# Hard ceiling on tool calls per spoken command. Stops a misunderstood
# instruction from turning into an unbounded drive-look-drive loop.
VOICE_MAX_TOOL_CALLS = _env_int('PICAR_VOICE_MAX_TOOL_CALLS', 12)

# How many conversation turns to keep. Each turn is a user message plus the
# assistant/tool exchange it triggered; older ones are dropped so a long
# session doesn't grow the request without bound.
VOICE_HISTORY_TURNS = _env_int('PICAR_VOICE_HISTORY_TURNS', 12)

# ---- Motion safety envelope ----
# The agent drives a real vehicle that can roll off a table, so its limits are
# deliberately tighter than the ones a human at the keyboard gets. Every
# motion tool clamps to these and stops itself when it's done; nothing the
# model can say makes the car move faster or longer than this allows.

# Top speed the agent may request (percent). Manual control still allows 100.
VOICE_MAX_SPEED = _env_int('PICAR_VOICE_MAX_SPEED', 45)

# Speed used when a command doesn't specify one.
VOICE_DEFAULT_SPEED = _env_int('PICAR_VOICE_DEFAULT_SPEED', 30)

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
VOICE_TTS_ENABLED = _env_flag('PICAR_VOICE_TTS_ENABLED', True)
VOICE_TTS_COMMAND = os.getenv('PICAR_VOICE_TTS_COMMAND', 'espeak-ng')
VOICE_TTS_VOICE = os.getenv('PICAR_VOICE_TTS_VOICE', 'en-us')
VOICE_TTS_WPM = _env_int('PICAR_VOICE_TTS_WPM', 165)
VOICE_TTS_AMPLITUDE = _env_int('PICAR_VOICE_TTS_AMPLITUDE', 150)

# ---- Speech input (optional, on-Pi microphone) ----
# The default input path is the browser's Web Speech API: your phone does the
# listening and POSTs text, which needs no extra hardware. Set this to use a
# USB mic plugged into the Pi instead, via faster-whisper.
VOICE_STT_MODEL = os.getenv('PICAR_VOICE_STT_MODEL', 'base.en')
VOICE_STT_DEVICE = os.getenv('PICAR_VOICE_STT_COMPUTE', 'int8')

# ---- On-board microphone (listen without a phone in the loop) ----
# Off by default: it needs a USB microphone attached and the extra audio
# packages installed (uv pip install -e ".[mic]"). With it on, the car listens
# for its own name continuously and no browser is involved at all.
VOICE_LISTENER_ENABLED = _env_flag('PICAR_VOICE_LISTENER_ENABLED', False)

VOICE_WAKE_WORD = os.getenv('PICAR_VOICE_WAKE_WORD', 'claude')

# 'auto' uses openWakeWord when installed and able to load its model, and
# otherwise matches the wake word in transcribed speech. See
# picar/voice/wakeword.py for what each backend costs.
VOICE_WAKE_BACKEND = os.getenv('PICAR_VOICE_WAKE_BACKEND', 'auto')
VOICE_WAKE_MODEL = os.getenv('PICAR_VOICE_WAKE_MODEL', 'hey_jarvis')
VOICE_WAKE_THRESHOLD = float(os.getenv('PICAR_VOICE_WAKE_THRESHOLD', '0.5'))

# Microphone. Leave the device unset for the system default; set it to a
# device index or a name substring (`python -m sounddevice` lists them).
VOICE_MIC_DEVICE = os.getenv('PICAR_VOICE_MIC_DEVICE') or None
VOICE_MIC_SAMPLE_RATE = _env_int('PICAR_VOICE_MIC_SAMPLE_RATE', 16000)

# Voice activity detection, 0-3. Higher is more aggressive about calling
# something non-speech: raise it in a noisy room, lower it if quiet speech
# gets missed.
VOICE_VAD_AGGRESSIVENESS = _env_int('PICAR_VOICE_VAD_AGGRESSIVENESS', 2)

# Silence that marks the end of an utterance.
VOICE_SEGMENT_SILENCE_MS = _env_int('PICAR_VOICE_SEGMENT_SILENCE_MS', 700)

# Ignore blips shorter than this - a cough or a door shouldn't reach Whisper.
VOICE_MIN_SEGMENT_MS = _env_int('PICAR_VOICE_MIN_SEGMENT_MS', 300)

# Hard cap on one utterance, so a running tap can't be recorded forever.
VOICE_MAX_SEGMENT_SECONDS = float(os.getenv('PICAR_VOICE_MAX_SEGMENT_SECONDS', '12'))

# After a bare wake word ("Claude?"), how long to treat the next thing said as
# the command without needing the name again.
VOICE_COMMAND_WINDOW_SECONDS = float(
    os.getenv('PICAR_VOICE_COMMAND_WINDOW_SECONDS', '6')
)
