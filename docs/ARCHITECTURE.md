# Architecture Guide

## System Overview

PiCar-X is designed with a **modular, layered architecture** that separates concerns and enables easy testing and maintenance.

```
┌─────────────────────────────────────────────┐
│         Web Browser (Frontend)              │
│  HTML/CSS/JavaScript - Responsive UI        │
└──────────────────┬──────────────────────────┘
                   │ HTTP/JSON
┌──────────────────▼──────────────────────────┐
│      Flask REST API (Backend)               │
│  /api/motors, /api/camera, /stream          │
└──────────────────┬──────────────────────────┘
                   │ Python
┌──────────────────▼──────────────────────────┐
│    Hardware Abstraction Layer               │
│  ├─ MotorController                         │
│  ├─ ServoController                         │
│  └─ CameraStream                            │
└──────────────────┬──────────────────────────┘
                   │ GPIO/I2C
┌──────────────────▼──────────────────────────┐
│      Raspberry Pi Hardware                  │
│  ├─ GPIO Pins (Motors)                      │
│  ├─ I2C Bus (Servos)                        │
│  └─ Camera Module                           │
└─────────────────────────────────────────────┘
```

## Component Architecture

### 1. **Frontend** (`frontend/`)

**Purpose**: User interface for controlling the PiCar-X

**Structure**:
- `templates/index.html` - Main UI template
- `static/style.css` - Responsive styling
- `static/control.js` - Event handling and API calls

**Features**:
- Real-time camera stream viewing
- Directional movement controls
- Speed adjustment slider
- Camera pan/tilt controls
- Motor status display
- Keyboard support

### 2. **Backend API** (`backend/app.py`)

**Purpose**: RESTful API server connecting frontend to hardware

**Endpoints**:
```
Motors:
  POST   /api/motors/forward
  POST   /api/motors/backward
  POST   /api/motors/stop
  POST   /api/motors/set-speed
  GET    /api/motors/status

Camera:
  POST   /api/camera/pan
  POST   /api/camera/tilt
  POST   /api/camera/position
  POST   /api/camera/center
  GET    /api/camera/status
  GET    /stream

System:
  GET    /api/health
```

### 3. **Hardware Abstraction** (`picar/`)

Each hardware component is abstracted into its own module:

#### **MotorController** (`picar/motors/`)

Controls DC motors for movement

```python
motor = get_motor_controller()
motor.forward(speed=80)       # Move forward at 80% speed
motor.set_speed(50, 75)       # Left: 50%, Right: 75%
motor.backward(speed=60)      # Move backward at 60% speed
motor.stop()                  # Stop all motors
```

**GPIO Configuration**:
- Left forward: GPIO 17 (PWM)
- Left backward: GPIO 18 (PWM)
- Right forward: GPIO 27 (PWM)
- Right backward: GPIO 22 (PWM)

#### **ServoController** (`picar/servos/`)

Controls servo motors for camera pan/tilt

```python
servo = get_servo_controller()
servo.set_pan(45)             # Pan 45° right
servo.set_tilt(-30)           # Tilt 30° down
servo.set_position(45, -30)   # Pan and tilt together
servo.center()                # Center to (0, 0)
```

**I2C Configuration**:
- Driver: PCA9685 (16-channel PWM)
- Channel 0: Pan servo
- Channel 1: Tilt servo
- Range: -90° to +90°

#### **CameraStream** (`picar/camera/`)

Handles video streaming and capture

```python
camera = get_camera_stream()
frame = camera.get_frame()           # Get single JPEG frame
stream = camera.stream_generator()   # Get MJPEG stream generator
camera.stop_streaming()              # Stop streaming
```

**Features**:
- MJPEG streaming format
- Configurable resolution (default: 640x480)
- Configurable framerate (default: 30 FPS)
- Quality control (0-100)

### 4. **Configuration** (`config/config.py`)

Centralized configuration for all hardware and software settings

```python
# Motor Configuration
MOTOR_LEFT_FORWARD = 17
PWM_FREQUENCY = 1000

# Servo Configuration
SERVO_PAN_CHANNEL = 0
SERVO_MIN_ANGLE = -90

# Camera Configuration
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30

# Flask Configuration
FLASK_PORT = 5000
```

## Design Patterns

### **Singleton Pattern**

Each hardware controller is a singleton:
```python
# Always returns the same instance
motor1 = get_motor_controller()
motor2 = get_motor_controller()
assert motor1 is motor2  # True
```

### **Hardware Abstraction**

Controllers work in two modes:
1. **Hardware Mode**: Real GPIO/I2C communication
2. **Simulation Mode**: Logs commands without hardware

```python
# Automatically detects hardware availability
motor = MotorController()
# Works on Raspberry Pi with GPIO
# Falls back gracefully on other systems
```

### **Thread Safety**

All hardware access is protected with locks:
```python
motor.lock.acquire()
# Perform motor operation
motor.lock.release()
```

## Data Flow

### Movement Control Flow

```
User clicks "Forward"
    ↓
JavaScript sends POST /api/motors/forward
    ↓
Flask route handler receives request
    ↓
get_motor_controller() returns singleton
    ↓
motor.forward(speed) calls set_speed()
    ↓
Thread lock acquired
    ↓
Speed validated and clamped
    ↓
PWM duty cycles applied to GPIO pins
    ↓
Motors receive PWM signal
    ↓
Vehicle moves forward
    ↓
JavaScript polls /api/motors/status
    ↓
UI updates motor speed display
```

### Camera Stream Flow

```
User loads webpage
    ↓
Browser requests GET /stream
    ↓
Flask initiates streaming response
    ↓
camera.stream_generator() starts loop
    ↓
get_frame() captures JPEG from camera
    ↓
Frame wrapped in MJPEG boundary
    ↓
Frame sent to browser
    ↓
Browser displays frame
    ↓
Loop repeats at configured FPS
```

## Modularity Benefits

### ✅ **Testability**
- Each module can be tested independently
- Simulation mode allows testing without hardware
- Mock objects can replace hardware controllers

### ✅ **Reusability**
- Motors module can be used in other projects
- Servo controller is generic for any PCA9685 device
- Camera module works with any picamera2-compatible device

### ✅ **Maintainability**
- Clear separation of concerns
- Single responsibility per module
- Easy to locate and fix bugs

### ✅ **Extensibility**
- Add new hardware: create new module in `picar/`
- Add new API routes: extend `backend/app.py`
- Customize UI: modify `frontend/` files

### ✅ **Scalability**
- Thread-safe design for concurrent requests
- Can handle multiple simultaneous commands
- Performance can be tuned per component

## Adding New Features

### Example: Add Lights Control

1. **Create Hardware Module**
```python
# picar/lights/light_controller.py
class LightController:
    def __init__(self):
        self.brightness = 0
    
    def set_brightness(self, level):
        # Control GPIO for lights
        pass
```

2. **Add to Backend**
```python
# backend/app.py
@app.route('/api/lights/set', methods=['POST'])
def set_lights():
    brightness = request.json.get('brightness')
    light_ctrl.set_brightness(brightness)
    return jsonify({'status': 'success'})
```

3. **Update Frontend**
```html
<!-- frontend/templates/index.html -->
<input type="range" id="brightness" oninput="setLights(this.value)">

<script>
function setLights(value) {
    fetch('/api/lights/set', {
        method: 'POST',
        body: JSON.stringify({'brightness': value})
    });
}
</script>
```

## Performance Considerations

### Motor Control
- PWM frequency: 1000 Hz for smooth control
- Speed values: 0-100% with linear scaling
- Thread-safe updates for responsive UI

### Camera Streaming
- Resolution: 640x480 default (adjustable)
- Framerate: 30 FPS default
- Quality: 80/100 for bandwidth efficiency
- MJPEG format for browser compatibility

### Network
- RESTful API for simplicity
- Future: WebSocket for lower latency
- Runs on local network (no cloud required)

## Security Note

This is a **local network only** system:
- No authentication (runs on trusted local network)
- No encryption (local network assumed secure)
- Future versions should add security features for internet exposure

---

**Architecture designed for clarity, modularity, and ease of extension**
