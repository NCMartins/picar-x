# PiCar-X Remote Control

A modular Python-based web interface for controlling the Sunfounder PiCar-X robot on Raspberry Pi 4B. Stream live video, control movement, and adjust camera position remotely.

## Project Notes

- This repository was vibecoded.
- The Ansible deployment path is included, but it has not been tested yet.

**Fast setup with [uv](https://astral.sh/blog/introducing-uv/) - a blazing-fast Python package manager**

## Features

✨ **Core Capabilities:**
- 🎥 Live MJPEG camera streaming
- 🎮 Real-time motor control (forward, backward, turn)
- 🛞 Dedicated steering calibration page with persistent center offset
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
│   ├── config.py              # Centralized configuration
│   └── steering_calibration.json  # Saved steering offset
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
│   │   ├── index.html
│   │   └── steering_calibration.html
│   └── static/
│       ├── style.css
│       ├── control.js
│       └── steering_calibration.js
├── requirements.txt
└── README.md
```

## Hardware Requirements

- **Raspberry Pi 4B** (4GB+ recommended)
- **Sunfounder PiCar-X** kit with **Robot Hat v4**
- **Camera module** (Pi Camera V2 or V3)
- **Stable power supply** (6.0V-8.4V XH2.54 3pin power input)

## Installation

### Option 1: Automated Deployment with Ansible

> ⚠️ This Ansible path is currently untested in this repository.

For automated deployment to a fresh Raspberry Pi:

1. **Setup Raspberry Pi OS**: Follow [RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)
2. **Deploy with Ansible**: See [ansible/README.md](ansible/README.md)

```bash
# On your control machine (not the Pi)
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```

This automatically:
- Configures system settings and networking
- Installs all dependencies including `robot-hat` library
- Deploys the PiCar-X application
- Sets up systemd service for auto-start
- Verifies hardware connectivity

### Option 2: Manual Installation

#### 1. Setup Raspberry Pi OS

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

### 4. Setup Virtual Environment and Install Dependencies

```bash
# Create virtual environment
uv venv

# Install Python dependencies (includes robot-hat)
uv pip install -r requirements.txt
```

### 5. Run the Server

```bash
# Activate virtual environment and run
source .venv/bin/activate
python backend/app.py
```

Or use the provided launcher script:
```bash
chmod +x start.sh
./start.sh  # Linux/macOS
```

```batch
start.bat   # Windows
```

## Configuration

The application uses `robot-hat` library for hardware control. No additional GPIO configuration is needed - the library handles all hardware abstraction.

Default pin assignments (robot-hat naming):
- **Motors**: M1 (left), M2 (right)
- **Servos**: P0 (pan), P1 (tilt)

To customize, edit `config/config.py`:

```python
# Motor pins (using robot-hat naming)
MOTOR_LEFT = "M1"  # Left motor
MOTOR_RIGHT = "M2"  # Right motor

# Servo pins (using robot-hat naming)
SERVO_PAN_PIN = "P0"  # Pan servo
SERVO_TILT_PIN = "P1"  # Tilt servo
```

## Usage

### Start the Server

```bash
# Setup virtual environment (one-time)
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Run server
source .venv/bin/activate
python backend/app.py
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

### Steering Calibration

Open the dedicated calibration page:

```
http://<raspberry-pi-ip>:5000/steering-calibration
```

Use this page to adjust steering center offset and save it permanently.

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

## Safety

The motors have a built-in dead-man's switch: if no forward/backward/speed
command refreshes them within `MOTOR_WATCHDOG_TIMEOUT` (1 second by default,
see `config/config.py`), they're automatically stopped. This protects against
a dropped connection, a crashed browser tab, or a locked phone leaving the
robot driving indefinitely - it does not require any changes to how the
frontend sends commands.

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

- `POST /api/camera/start-stream` - Start streaming

- `POST /api/camera/stop-stream` - Stop streaming

- `GET /stream` - MJPEG stream endpoint

### Steering

- `POST /api/steering/angle` - Set steering angle
  ```json
  { "angle": 25 }
  ```

- `POST /api/steering/center` - Center steering

- `GET /api/steering/status` - Get steering angle and current calibration offset

- `GET /api/steering/calibration` - Get steering calibration offset

- `POST /api/steering/calibration` - Save steering calibration offset
  ```json
  { "offset": -3 }
  ```

- `POST /api/steering/calibration/reset` - Reset calibration offset to 0

### System

- `GET /api/health` - Health check and system status

## Development & Testing

### Run in Simulation Mode

The application automatically runs in simulation mode when hardware is not available or not properly configured. You'll see warnings like:

```
Warning: RPi.GPIO not available - running in simulation mode
Warning: Adafruit PCA9685 not available - running in simulation mode
Warning: picamera2 not available - running in simulation mode
```

In simulation mode:
- Motor controls will log commands instead of moving hardware
- Camera stream will show placeholder frames
- All web interface features remain functional for testing

```bash
# Works on any system without Raspberry Pi hardware
source .venv/bin/activate
python backend/app.py
```

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
# Check if camera is enabled and detected
vcgencmd get_camera

# For Raspberry Pi OS Bookworm with libcamera:
rpicam-still --list-cameras
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
