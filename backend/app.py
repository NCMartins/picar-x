"""
Flask API for PiCar-X web control
RESTful API for controlling motors, servos, and camera
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import hmac
import logging
import os
import sys
import tempfile
from pathlib import Path

# Add project to path
project_path = Path(__file__).parent.parent
sys.path.insert(0, str(project_path))

from backend.utils import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from config.config import (
    FLASK_HOST, FLASK_PORT, MJPEG_CONTENT_TYPE,
    AUTH_USERNAME, AUTH_PASSWORD, ALLOWED_ORIGINS,
    VOICE_ENABLED, VOICE_MODEL, VOICE_MAX_SPEED, VOICE_MAX_MOVE_SECONDS,
    VOICE_LISTENER_ENABLED, VOICE_WAKE_WORD,
)
from picar import (
    get_motor_controller,
    get_servo_controller,
    get_steering_controller,
    get_camera_stream
)
from picar.voice import (
    ListenerUnavailable,
    TranscriberUnavailable,
    VoiceAgentUnavailable,
    get_listener,
    get_speaker,
    get_transcriber,
    get_voice_agent,
)

app = Flask(__name__,
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app, origins=ALLOWED_ORIGINS)

AUTH_ENABLED = bool(AUTH_USERNAME and AUTH_PASSWORD)
if not AUTH_ENABLED:
    logger.warning(
        "PICAR_AUTH_USERNAME/PICAR_AUTH_PASSWORD are not set. "
        "The web interface and API are UNAUTHENTICATED and controllable by "
        "anyone who can reach this host on the network."
    )


@app.before_request
def require_auth():
    """Require HTTP Basic Auth on every request when credentials are configured."""
    if not AUTH_ENABLED:
        return None

    auth = request.authorization
    valid = (
        auth is not None
        and auth.username is not None
        and auth.password is not None
        and hmac.compare_digest(auth.username, AUTH_USERNAME)
        and hmac.compare_digest(auth.password, AUTH_PASSWORD)
    )
    if not valid:
        return Response(
            'Authentication required', 401,
            {'WWW-Authenticate': 'Basic realm="PiCar-X"'}
        )

# Get controller instances
motor_ctrl = get_motor_controller()
servo_ctrl = get_servo_controller()
steering_ctrl = get_steering_controller()
camera_stream = get_camera_stream()
voice_agent = get_voice_agent()

if not VOICE_ENABLED:
    logger.info(
        "Voice control is off (no ANTHROPIC_API_KEY, or PICAR_VOICE_ENABLED=0). "
        "Manual control is unaffected."
    )
else:
    logger.info("Voice control enabled using model %s", VOICE_MODEL)
    if VOICE_LISTENER_ENABLED:
        # Best effort: a missing microphone or audio library must not stop the
        # server from coming up, since everything else still works without it.
        try:
            get_listener().start()
        except ListenerUnavailable as exc:
            logger.warning("On-board microphone unavailable: %s", exc)
        except Exception:
            logger.exception("Could not start the on-board microphone listener")
    if not AUTH_ENABLED:
        logger.warning(
            "Voice control is enabled but the API is UNAUTHENTICATED. Anyone who "
            "can reach this host can drive the robot and spend your Anthropic API "
            "credits. Set PICAR_AUTH_USERNAME/PICAR_AUTH_PASSWORD."
        )


# ==================== Request Validation ====================

def _get_json_body() -> dict:
    """Parse the request's JSON body, tolerating a missing/empty body.

    Does not raise on malformed JSON or a non-JSON Content-Type - callers
    just get an empty dict and fall back to field defaults.
    """
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _require_number(data: dict, key: str, default):
    """Fetch a numeric field from a parsed JSON body.

    Raises ValueError (turned into a 400 response by the errorhandler
    below) if the field is present but isn't a number.
    """
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{key}' must be a number")
    return value


@app.errorhandler(ValueError)
def handle_bad_request(error):
    """Turn validation errors into a 400 instead of an unhandled 500."""
    return jsonify({'status': 'error', 'message': str(error)}), 400


# ==================== Motor Routes ====================

@app.route('/api/motors/forward', methods=['POST'])
def motor_forward():
    """Move forward"""
    data = _get_json_body()
    speed = _require_number(data, 'speed', 100)
    motor_ctrl.forward(speed)
    return jsonify({'status': 'success', 'action': 'forward', 'speed': speed})


@app.route('/api/motors/backward', methods=['POST'])
def motor_backward():
    """Move backward"""
    data = _get_json_body()
    speed = _require_number(data, 'speed', 100)
    motor_ctrl.backward(speed)
    return jsonify({'status': 'success', 'action': 'backward', 'speed': speed})


@app.route('/api/motors/stop', methods=['POST'])
def motor_stop():
    """Stop motors"""
    motor_ctrl.stop()
    return jsonify({'status': 'success', 'action': 'stop'})


@app.route('/api/motors/set-speed', methods=['POST'])
def set_motor_speed():
    """Set individual motor speeds"""
    data = _get_json_body()
    left_speed = _require_number(data, 'left_speed', 0)
    right_speed = _require_number(data, 'right_speed', 0)
    motor_ctrl.set_speed(left_speed, right_speed)
    return jsonify({
        'status': 'success',
        'left_speed': left_speed,
        'right_speed': right_speed
    })


@app.route('/api/motors/status', methods=['GET'])
def motor_status():
    """Get current motor speeds"""
    return jsonify({
        'left_speed': motor_ctrl.left_speed,
        'right_speed': motor_ctrl.right_speed
    })


# ==================== Steering Routes ====================

@app.route('/api/steering/angle', methods=['POST'])
def steering_set_angle():
    """Set front wheel steering angle."""
    data = _get_json_body()
    angle = _require_number(data, 'angle', 0)
    steering_ctrl.set_angle(angle)
    return jsonify({'status': 'success', 'angle': steering_ctrl.angle})


@app.route('/api/steering/center', methods=['POST'])
def steering_center():
    """Center front wheel steering."""
    steering_ctrl.center()
    return jsonify({'status': 'success', 'angle': steering_ctrl.angle})


@app.route('/api/steering/status', methods=['GET'])
def steering_status():
    """Get current steering angle."""
    return jsonify({
        'angle': steering_ctrl.angle,
        'calibration_offset': steering_ctrl.calibration_offset,
    })


@app.route('/api/steering/calibration', methods=['GET'])
def steering_calibration_status():
    """Get current steering calibration offset."""
    return jsonify({'offset': steering_ctrl.calibration_offset})


@app.route('/api/steering/calibration', methods=['POST'])
def steering_set_calibration():
    """Set steering calibration offset."""
    data = _get_json_body()
    offset = _require_number(data, 'offset', 0)
    steering_ctrl.set_calibration_offset(int(offset))
    return jsonify({
        'status': 'success',
        'offset': steering_ctrl.calibration_offset,
        'angle': steering_ctrl.angle,
    })


@app.route('/api/steering/calibration/reset', methods=['POST'])
def steering_reset_calibration():
    """Reset steering calibration offset to 0."""
    steering_ctrl.reset_calibration()
    return jsonify({'status': 'success', 'offset': steering_ctrl.calibration_offset})


# ==================== Servo Routes ====================

@app.route('/api/camera/pan', methods=['POST'])
def set_pan():
    """Set camera pan angle"""
    data = _get_json_body()
    angle = _require_number(data, 'angle', 0)
    servo_ctrl.set_pan(angle)
    return jsonify({'status': 'success', 'pan': angle})


@app.route('/api/camera/tilt', methods=['POST'])
def set_tilt():
    """Set camera tilt angle"""
    data = _get_json_body()
    angle = _require_number(data, 'angle', 0)
    servo_ctrl.set_tilt(angle)
    return jsonify({'status': 'success', 'tilt': angle})


@app.route('/api/camera/position', methods=['POST'])
def set_camera_position():
    """Set both pan and tilt"""
    data = _get_json_body()
    pan = _require_number(data, 'pan', 0)
    tilt = _require_number(data, 'tilt', 0)
    servo_ctrl.set_position(pan, tilt)
    return jsonify({
        'status': 'success',
        'pan': pan,
        'tilt': tilt
    })


@app.route('/api/camera/center', methods=['POST'])
def center_camera():
    """Center camera (pan=0, tilt=0)"""
    servo_ctrl.center()
    return jsonify({'status': 'success', 'action': 'center'})


@app.route('/api/camera/status', methods=['GET'])
def camera_status():
    """Get current camera position"""
    return jsonify({
        'pan': servo_ctrl.pan_angle,
        'tilt': servo_ctrl.tilt_angle
    })


# ==================== Streaming Routes ====================

@app.route('/stream')
def video_stream():
    """MJPEG video stream endpoint"""
    return Response(
        camera_stream.stream_generator(),
        mimetype=MJPEG_CONTENT_TYPE
    )


@app.route('/api/camera/start-stream', methods=['POST'])
def start_stream():
    """Start camera streaming"""
    camera_stream.streaming = True
    return jsonify({'status': 'success', 'streaming': True})


@app.route('/api/camera/stop-stream', methods=['POST'])
def stop_stream():
    """Stop camera streaming"""
    camera_stream.stop_streaming()
    return jsonify({'status': 'success', 'streaming': False})


# ==================== Voice Control Routes ====================

@app.route('/api/voice/status', methods=['GET'])
def voice_status():
    """Report whether voice control is usable, and what it's doing."""
    return jsonify({
        'enabled': VOICE_ENABLED,
        'available': voice_agent.available,
        'busy': voice_agent.busy,
        'model': VOICE_MODEL if voice_agent.available else None,
        'speaker_available': get_speaker().available,
        'local_transcription': get_transcriber().loaded,
        'listening': get_listener().running,
        'wake_word': VOICE_WAKE_WORD,
        'max_speed': VOICE_MAX_SPEED,
        'max_move_seconds': VOICE_MAX_MOVE_SECONDS,
    })


@app.route('/api/voice/command', methods=['POST'])
def voice_command():
    """Run one spoken command, already transcribed to text.

    This is the main entry point: the browser's Web Speech API does the
    listening on the phone and POSTs the text here, so no microphone or
    speech software is needed on the Pi itself.
    """
    data = _get_json_body()
    text = data.get('text', '')
    if not isinstance(text, str) or not text.strip():
        raise ValueError("'text' must be a non-empty string")

    return _run_voice_command(text.strip(), speak=data.get('speak', True) is not False)


@app.route('/api/voice/audio', methods=['POST'])
def voice_audio():
    """Run a spoken command from an uploaded audio clip.

    For the untethered path: a USB microphone on the Pi, or a browser that
    can't do speech recognition itself. Needs faster-whisper installed.
    """
    upload = request.files.get('audio')
    if upload is None:
        return jsonify({
            'status': 'error',
            'message': "No audio uploaded. POST a file under the 'audio' field.",
        }), 400

    suffix = Path(upload.filename or 'clip.wav').suffix or '.wav'
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            upload.save(tmp)
        transcript = get_transcriber().transcribe(tmp_path)
    except TranscriberUnavailable as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 501
    except Exception as exc:
        logger.exception("Transcription failed")
        return jsonify({'status': 'error', 'message': f'Transcription failed: {exc}'}), 500
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                logger.debug("Could not remove temp audio %s", tmp_path, exc_info=True)

    if not transcript:
        return jsonify({
            'status': 'error',
            'message': "I couldn't make out any speech in that clip.",
            'transcript': '',
        }), 400

    return _run_voice_command(transcript, speak=True)


def _run_voice_command(text: str, speak: bool):
    """Shared path for text and audio commands."""
    try:
        result = voice_agent.handle_command(text)
    except VoiceAgentUnavailable as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 503
    except RuntimeError as exc:
        # Already running a command - the caller should wait, not retry blindly.
        return jsonify({'status': 'error', 'message': str(exc)}), 409
    except Exception as exc:
        logger.exception("Voice command failed")
        # A failure mid-drive must not leave the car moving.
        motor_ctrl.stop()
        steering_ctrl.center()
        return jsonify({'status': 'error', 'message': f'Voice command failed: {exc}'}), 500

    spoken = False
    if speak and result['reply']:
        spoken = get_speaker().say(result['reply'])

    return jsonify({
        'status': 'success',
        'transcript': text,
        'spoken_on_pi': spoken,
        **result,
    })


@app.route('/api/voice/stop', methods=['POST'])
def voice_stop():
    """Emergency stop: cut motion and speech now, without asking the model.

    Deliberately does not go through the agent's turn loop - this has to work
    while a command is mid-drive and the model is mid-thought, so it only
    touches the abort flag and the hardware.
    """
    voice_agent.emergency_stop()
    get_speaker().silence()
    motor_ctrl.stop()
    steering_ctrl.center()
    return jsonify({'status': 'success', 'action': 'emergency_stop'})


@app.route('/api/voice/listener', methods=['GET'])
def voice_listener_status():
    """Whether the car is listening through its own microphone."""
    listener = get_listener()
    return jsonify({
        'configured': VOICE_LISTENER_ENABLED,
        'wake_word': VOICE_WAKE_WORD,
        **listener.status,
    })


@app.route('/api/voice/listener/start', methods=['POST'])
def voice_listener_start():
    """Start listening through the on-board microphone."""
    if not VOICE_ENABLED:
        return jsonify({
            'status': 'error',
            'message': 'Voice control is not configured. Set ANTHROPIC_API_KEY.',
        }), 503
    try:
        get_listener().start()
    except ListenerUnavailable as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 501
    except Exception as exc:
        logger.exception("Could not start the listener")
        return jsonify({'status': 'error', 'message': str(exc)}), 500
    return jsonify({'status': 'success', **get_listener().status})


@app.route('/api/voice/listener/stop', methods=['POST'])
def voice_listener_stop():
    """Stop listening and release the microphone."""
    get_listener().stop()
    return jsonify({'status': 'success', **get_listener().status})


@app.route('/api/voice/reset', methods=['POST'])
def voice_reset():
    """Forget the conversation so far and start fresh."""
    voice_agent.reset()
    return jsonify({'status': 'success', 'action': 'conversation_reset'})


@app.route('/api/voice/transcript', methods=['GET'])
def voice_transcript():
    """The conversation so far, for rebuilding the log after a page reload."""
    return jsonify({'transcript': voice_agent.get_transcript()})


# ==================== Health Checks ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'motors_initialized': motor_ctrl.initialized,
        'servos_initialized': servo_ctrl.initialized,
        'steering_initialized': steering_ctrl.initialized,
        'camera_initialized': camera_stream.initialized,
        'voice_enabled': VOICE_ENABLED,
        'voice_available': voice_agent.available,
        'voice_busy': voice_agent.busy,
    })


@app.route('/')
def index():
    """Serve main page"""
    from flask import render_template
    return render_template('index.html')


@app.route('/steering-calibration')
def steering_calibration_page():
    """Serve steering calibration page."""
    from flask import render_template
    return render_template('steering_calibration.html')


# ==================== Error Handling ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'status': 'error', 'message': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    try:
        logger.info("Starting production server (waitress) on %s:%s", FLASK_HOST, FLASK_PORT)
        # Flask's built-in dev server isn't meant for production use (no
        # concurrency/robustness guarantees, and it's single-threaded by
        # default - which would block motor/API requests while the MJPEG
        # stream endpoint is held open). waitress is a production-grade
        # WSGI server; a modest thread pool lets a camera stream and API
        # calls be served at the same time without needing a multi-process
        # server, which would fight over the same I2C/GPIO hardware.
        from waitress import serve
        serve(app, host=FLASK_HOST, port=FLASK_PORT, threads=8)
    finally:
        # Cleanup on exit
        get_listener().stop()
        motor_ctrl.cleanup()
        servo_ctrl.cleanup()
        steering_ctrl.cleanup()
        camera_stream.cleanup()
