"""
Flask API for PiCar-X web control
RESTful API for controlling motors, servos, and camera
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import sys
from pathlib import Path

# Add project to path
project_path = Path(__file__).parent.parent
sys.path.insert(0, str(project_path))

from config.config import FLASK_HOST, FLASK_PORT, MJPEG_CONTENT_TYPE
from picar import (
    get_motor_controller,
    get_servo_controller,
    get_steering_controller,
    get_camera_stream
)

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)

# Get controller instances
motor_ctrl = get_motor_controller()
servo_ctrl = get_servo_controller()
steering_ctrl = get_steering_controller()
camera_stream = get_camera_stream()


# ==================== Motor Routes ====================

@app.route('/api/motors/forward', methods=['POST'])
def motor_forward():
    """Move forward"""
    speed = request.json.get('speed', 100)
    motor_ctrl.forward(speed)
    return jsonify({'status': 'success', 'action': 'forward', 'speed': speed})


@app.route('/api/motors/backward', methods=['POST'])
def motor_backward():
    """Move backward"""
    speed = request.json.get('speed', 100)
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
    data = request.json
    left_speed = data.get('left_speed', 0)
    right_speed = data.get('right_speed', 0)
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
    angle = request.json.get('angle', 0)
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
    offset = request.json.get('offset', 0)
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
    angle = request.json.get('angle', 0)
    servo_ctrl.set_pan(angle)
    return jsonify({'status': 'success', 'pan': angle})


@app.route('/api/camera/tilt', methods=['POST'])
def set_tilt():
    """Set camera tilt angle"""
    angle = request.json.get('angle', 0)
    servo_ctrl.set_tilt(angle)
    return jsonify({'status': 'success', 'tilt': angle})


@app.route('/api/camera/position', methods=['POST'])
def set_camera_position():
    """Set both pan and tilt"""
    data = request.json
    pan = data.get('pan', 0)
    tilt = data.get('tilt', 0)
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


# ==================== Health Checks ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'motors_initialized': motor_ctrl.initialized,
        'servos_initialized': servo_ctrl.initialized,
        'steering_initialized': steering_ctrl.initialized,
        'camera_initialized': camera_stream.initialized
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
        print(f"Starting Flask server on {FLASK_HOST}:{FLASK_PORT}")
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
    finally:
        # Cleanup on exit
        motor_ctrl.cleanup()
        servo_ctrl.cleanup()
        steering_ctrl.cleanup()
        camera_stream.cleanup()
