# PiCar-X Remote Control

A modular Python-based web interface for controlling the Sunfounder PiCar-X robot on Raspberry Pi 4B. Stream live video, control movement, and adjust camera position remotely.

**Fast setup with [uv](https://astral.sh/blog/introducing-uv/) - a blazing-fast Python package manager**

## Features

✨ **Core Capabilities:**
- 🎥 Live MJPEG camera streaming
- 🎮 Real-time motor control (forward, backward, turn)
- 📸 Pan/tilt camera servo control
- 🌐 Web-based interface accessible from any browser
- ⌨️ Keyboard control support (Arrow keys/WASD)
- 📊 Real-time status monitoring

✔️ **Architecture:**
- Modular Python design with clean separation of concerns
- Hardware abstraction layer for easy testing
- RESTful API backend
- Responsive web frontend
- Simulation mode for development without hardware

## Project Structure

```
picar/
├── config/
│   └── config.py              # Centralized configuration
├── picar/
│   ├── motors/
│   │   ├── motor_controller.py
│   │   └── __init__.py
│   ├── servos/
│   │   ├── servo_controller.py
│   │   └── __init__.py
│   ├── camera/
│   │   ├── camera_stream.py
│   │   └── __init__.py
│   └── __init__.py
├── backend/
│   ├── app.py                 # Flask application
│   └── utils.py               # Backend utilities
├── frontend/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── control.js
├── requirements.txt
└── README.md
```

## Hardware Requirements

- **Raspberry Pi 4B** (4GB+ recommended)
- **Sunfounder PiCar-X** kit
- **Camera module** (Pi Camera V2 or V3)
- **I2C servo driver** (PCA9685 - included in kit)
- **DC motors** (for movement)
- **Servo motors** (for camera control)
- **Stable power supply** (5V for Pi, appropriate voltage for motors)

## Installation

### 1. Setup Raspberry Pi OS

**Complete step-by-step guide**: See [RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)

Quick summary:
```bash
# Download Raspberry Pi OS using Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Enable required interfaces:
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → Camera → Enable
# → Finish & Reboot

# Update system
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install uv (Fast Python Package Manager)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH if needed
export PATH="$HOME/.cargo/bin:$PATH"
```

### 3. Clone Repository

```bash
git clone <your-repo-url> picar-x
cd picar-x
```

### 4. Sync Dependencies with uv

```bash
# Sync all dependencies (creates virtual environment automatically)
uv sync --python 3.9
```

### 5. Run the Server

```bash
# Linux/macOS
uv run python backend/app.py

# Windows
uv run python backend\app.py
```

Or use the provided launcher scripts:
```bash
chmod +x start.sh
./start.sh  # Linux/macOS
```

```batch
start.bat   # Windows
```

### 5. Configure Hardware

Edit `config/config.py` to match your GPIO pin assignments:

```python
# Motor pins (BCM numbering)
MOTOR_LEFT_FORWARD = 17
MOTOR_LEFT_BACKWARD = 18
MOTOR_RIGHT_FORWARD = 27
MOTOR_RIGHT_BACKWARD = 22

# Servo channels
SERVO_PAN_CHANNEL = 0
SERVO_TILT_CHANNEL = 1
```

## Usage

### Start the Server with uv

```bash
# Sync dependencies (one-time)
uv sync --python 3.9

# Run server
uv run python backend/app.py
```

Or use the launcher script:
```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

### Access Web Interface

Open browser and navigate to:
```
http://<raspberry-pi-ip>:5000
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| ↑ / W | Move Forward |
| ↓ / S | Move Backward |
| ← / A | Turn Left |
| → / D | Turn Right |
| Space | Stop |
| 4 / ← | Pan Left |
| 6 / → | Pan Right |
| 8 / ↑ | Tilt Up |
| 2 / ↓ | Tilt Down |
| 5 | Center Camera |

## API Endpoints

### Motors

- `POST /api/motors/forward` - Move forward
  ```json
  { "speed": 100 }
  ```

- `POST /api/motors/backward` - Move backward
  ```json
  { "speed": 100 }
  ```

- `POST /api/motors/stop` - Stop all motors

- `POST /api/motors/set-speed` - Set individual motor speeds
  ```json
  { "left_speed": 50, "right_speed": 80 }
  ```

- `GET /api/motors/status` - Get current motor speeds

### Camera

- `POST /api/camera/pan` - Set pan angle
  ```json
  { "angle": 45 }
  ```

- `POST /api/camera/tilt` - Set tilt angle
  ```json
  { "angle": -30 }
  ```

- `POST /api/camera/position` - Set pan and tilt
  ```json
  { "pan": 45, "tilt": -30 }
  ```

- `POST /api/camera/center` - Center camera (0, 0)

- `GET /api/camera/status` - Get current camera position

- `GET /api/camera/start-stream` - Start streaming

- `POST /api/camera/stop-stream` - Stop streaming

- `GET /stream` - MJPEG stream endpoint

### System

- `GET /api/health` - Health check and system status

## Development & Testing

### Run in Simulation Mode

The application runs in simulation mode when hardware is not available:

```bash
# Works on any system without Raspberry Pi hardware
python app.py
```

- Motor controls will log commands instead of moving hardware
- Camera stream will show placeholder frames
- All web interface features remain functional

### Testing Individual Modules

```python
from picar.motors import get_motor_controller

motor = get_motor_controller()
motor.forward(speed=75)
motor.stop()
motor.cleanup()
```

## Customization

### Adjust Motor Speed

Edit `config/config.py`:
```python
MAX_SPEED = 100  # 0-100%
```

### Change Camera Resolution

```python
CAMERA_RESOLUTION = (1280, 720)  # Higher resolution
```

### Modify Servo Range

```python
SERVO_MIN_ANGLE = -90
SERVO_MAX_ANGLE = 90
```

## Troubleshooting

### Camera Not Appearing

```bash
# Check if camera is enabled
vcgencmd get_camera

# Check camera is connected
libcamera-hello --list-cameras
```

### I2C Servo Issues

```bash
# Check I2C devices
i2cdetect -y 1

# Install I2C tools if needed
sudo apt-get install i2c-tools
```

### GPIO Permission Denied

```bash
# Add user to GPIO group
sudo usermod -aG gpio $USER
# Log out and back in
```

## Performance Tips

1. **Network Optimization**: Use 5GHz WiFi for better latency
2. **Camera Quality**: Adjust `STREAM_QUALITY` in config for bandwidth
3. **Framerate**: Lower `CAMERA_FRAMERATE` if stream lags
4. **Resolution**: Reduce `CAMERA_RESOLUTION` for smoother streaming

## Future Enhancements

- 🤖 Autonomous navigation with object detection
- 📡 WebSocket support for lower latency
- 🗺️ Map visualization during movement
- 🎯 Path recording and playback
- 📱 Mobile app native support
- 🔒 Authentication and security features
- 🎛️ Advanced motor control (PID tuning)

## License

Private Repository

## Support & Documentation

Complete documentation available in `/docs`:

- **[docs/INDEX.md](docs/INDEX.md)** - Documentation index (start here!)
- **[docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)** - Complete Raspberry Pi OS setup guide ⭐
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture & design patterns
- **[docs/SETUP.md](docs/SETUP.md)** - Installation & troubleshooting
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference guide

---

**Built with Python + Flask + Modular Architecture**
