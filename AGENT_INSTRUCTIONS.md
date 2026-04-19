# GitHub Copilot Agent Instructions for PiCar-X Project

## Project Overview

**Name**: PiCar-X Remote Control System  
**Type**: Modular Python IoT Application  
**Platform**: Raspberry Pi 4B with Sunfounder PiCar-X  
**Purpose**: Web-based remote control interface for autonomous robot

## Project Context

This is a modular Python application for controlling a Sunfounder PiCar-X robot via a web browser. The project features:
- Real-time MJPEG camera streaming
- Remote motor control (forward, backward, turn)
- Pan/tilt camera servo control
- Responsive web UI with keyboard support
- RESTful API backend

## Architecture Overview

```
Frontend (HTML/CSS/JS) 
    ↓ (HTTP/JSON)
Flask REST API Backend 
    ↓ (Python)
Hardware Abstraction Layer
    ├─ MotorController (GPIO PWM)
    ├─ ServoController (I2C PCA9685)
    └─ CameraStream (picamera2)
    ↓ (GPIO/I2C)
Raspberry Pi Hardware
```

## Key Directories & Files

| Path | Purpose |
|------|---------|
| `config/config.py` | Centralized hardware configuration |
| `picar/motors/motor_controller.py` | DC motor control via GPIO PWM |
| `picar/servos/servo_controller.py` | Servo control via I2C PCA9685 |
| `picar/camera/camera_stream.py` | Camera streaming & JPEG capture |
| `backend/app.py` | Flask REST API server |
| `frontend/templates/index.html` | Web UI template |
| `frontend/static/control.js` | Client-side API calls & keyboard control |
| `frontend/static/style.css` | Responsive styling |
| `requirements.txt` | Python dependencies (for compatibility) |
| `pyproject.toml` | Modern Python project setup (primary) |
| `README.md` | Project documentation |
| `docs/RASPI_OS_SETUP.md` | **Complete Raspberry Pi OS setup guide** |
| `docs/ARCHITECTURE.md` | Architecture & design patterns |
| `docs/SETUP.md` | Installation & troubleshooting |
| `QUICKSTART.md` | Quick reference guide |

## Development Guidelines

### Code Style
- **Python**: Follow PEP 8 with 4-space indentation
- **JavaScript**: Use camelCase for functions, const/let for variables
- **Naming**: Use descriptive names (e.g., `get_motor_controller`, `moveForward()`)
- **Comments**: Document complex logic and hardware-specific code

### Module Organization
Each hardware component is a separate module:
- Import structure: `from picar.motors import get_motor_controller`
- Singleton pattern: Each controller maintains a single instance
- Error handling: Graceful fallback to simulation mode if hardware unavailable

### Adding Features
1. **Hardware feature**: Create/modify module in `picar/`
2. **API route**: Add endpoint in `backend/app.py`
3. **UI element**: Update `frontend/` files
4. **Config**: Add settings to `config/config.py`

### Testing
- Supports simulation mode on systems without hardware
- All controllers check hardware availability at initialization
- Use test scripts in project root for individual module testing

## Hardware Configuration

### GPIO Motor Pins (BCM numbering)
- Left forward: GPIO 17
- Left backward: GPIO 18
- Right forward: GPIO 27
- Right backward: GPIO 22

### I2C Servo Driver (PCA9685)
- Address: 0x40
- Channel 0: Pan servo
- Channel 1: Tilt servo

### Camera
- Resolution: 640x480 (configurable)
- Framerate: 30 FPS (configurable)
- Format: MJPEG stream

## API Endpoints Summary

**Motors**: `POST /api/motors/{forward|backward|stop}`  
**Motor Control**: `POST /api/motors/set-speed` (individual speeds)  
**Camera**: `POST /api/camera/{pan|tilt|position|center}`  
**Streaming**: `GET /stream` (MJPEG)  
**Health**: `GET /api/health`

## Common Tasks

## Common Tasks

### Task: Initial Raspberry Pi Setup
1. Follow **[docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)** completely
2. Verify interfaces enabled: I2C, Camera, GPIO
3. Update system packages
4. Test hardware connections

### Task: Deploy PiCar-X to Raspberry Pi
1. Clone repository on Raspberry Pi
2. Run `uv sync --python 3.9`
3. Verify GPIO pins in `config/config.py`
4. Test with `uv run python backend/app.py`
5. Setup auto-start service (optional)

### Task: Add Manual Control Slider
1. Update `frontend/static/control.js` - add slider input handler
2. Update `backend/app.py` - create corresponding API route
3. Update `frontend/templates/index.html` - add slider UI element
4. Test with browser & keyboard

### Task: Increase Motor Speed
Edit `config/config.py`:
```python
MAX_SPEED = 100  # Increase value
```

### Task: Change Camera Resolution
Edit `config/config.py`:
```python
CAMERA_RESOLUTION = (1280, 720)  # Higher resolution
```

### Task: Debug Hardware Issues
1. Check component initialization in controller class
2. Verify GPIO/I2C configuration matches physical setup
3. Use `curl` or Postman to test API endpoints
4. Check system logs: `sudo journalctl -u picar.service -f`

## Important Notes

- **Local Network Only**: No authentication by default (for local network use)
- **Simulation Mode**: Code works on any system without Raspberry Pi hardware
- **Thread Safety**: All hardware access uses locks to prevent conflicts
- **Performance**: Streaming quality is configurable for bandwidth optimization

## Useful Commands

```bash
# Check camera
libcamera-hello --list-cameras

# Check I2C devices
i2cdetect -y 1

# Check GPIO
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# Test API
curl http://localhost:5000/api/health

# Monitor service
sudo journalctl -u picar.service -f

# Check system temp
vcgencmd measure_temp
```

## File Locations (on Raspberry Pi)

```
~/ (home directory)
└── picar-x/
    ├── venv/                  # Python virtual environment
    ├── config/
    ├── picar/
    ├── backend/
    ├── frontend/
    ├── docs/
    ├── requirements.txt
    └── README.md
```

## Debugging Tips

1. **Check initialization**: Look for "initialized successfully" messages
2. **Enable logging**: Modify config.py `FLASK_DEBUG = True`
3. **Test modules independently**: Use Python REPL for component testing
4. **Browser console**: Open DevTools (F12) to see JavaScript errors
5. **API responses**: Use curl to test endpoints and see JSON responses

## Future Enhancement Ideas

- WebSocket support for lower latency
- Obstacle detection with computer vision
- Path recording and autonomous playback
- Multiple PiCar units coordination
- Native mobile app
- Cloud integration (with security considerations)

---

**This project is maintained as a private repository. Focus on modular, well-documented code that's easy to extend and test.**
