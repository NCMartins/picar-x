# 🚗 PiCar-X Project - Quick Start Guide

Your private PiCar-X remote control project has been initialized! Here's what you got:

## ✅ What's Been Created

### 📁 Project Structure
```
picar-x/
├── config/                 # Hardware configuration
│   └── config.py          # All settings in one place
├── picar/                 # Hardware abstraction modules
│   ├── motors/            # DC motor control
│   ├── servos/            # Servo pan/tilt control
│   └── camera/            # Camera streaming
├── backend/               # Flask REST API
│   ├── app.py            # Main server (REST endpoints)
│   └── utils.py          # Helper functions
├── frontend/              # Web interface
│   ├── templates/        # HTML
│   └── static/           # CSS & JavaScript
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md    # Design & patterns
│   └── SETUP.md          # Installation guide
├── AGENT_INSTRUCTIONS.md  # Copilot instructions
├── README.md             # Full documentation
├── requirements.txt      # Python dependencies
├── start.sh             # Linux/Raspberry Pi launcher
└── start.bat            # Windows launcher
```

## 🚀 Quick Start (Raspberry Pi)

### 1. **Complete Raspberry Pi OS Setup**

See **[docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)** for:
- Downloading and flashing Raspberry Pi OS
- Initial boot configuration
- Enabling I2C and Camera interfaces
- Network and SSH setup
- Hardware verification

**Quick steps**:
```bash
# 1. Download Raspberry Pi Imager
#    https://www.raspberrypi.com/software/
# 2. Flash microSD card with Raspberry Pi OS (64-bit)
# 3. Boot Raspberry Pi and enable interfaces via raspi-config
# 4. Update system
sudo apt-get update && sudo apt-get upgrade -y
```

### 2. Clone & Setup PiCar-X
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
mkdir -p ~/projects
cd ~/projects
git clone <your-repo-url> picar-x
cd picar-x

# Sync dependencies
uv sync --python 3.9
```

### 3. Run the Server
```bash
# Start server
uv run python backend/app.py

# Or use launcher script
chmod +x start.sh
./start.sh
```

### 4. Access Web Interface
```
http://<your-pi-ip>:5000
```

Example: `http://192.168.1.100:5000`

## 🎮 Features

### Motor Control
- ⬆️ Forward / ⬇️ Backward
- ⬅️ Turn Left / ➡️ Turn Right  
- Speed slider (0-100%)
- Individual motor speed control
- Keyboard support (WASD + Space)

### Camera Control
- 📹 Live MJPEG stream
- Pan: ⬅️ / ➡️
- Tilt: ⬆️ / ⬇️
- Center camera
- Numeric keypad support (2,4,6,8,5)

### System
- Real-time motor status
- Camera position display
- FPS counter
- Connection health check
- Comprehensive error handling

## 🏗️ Architecture Highlights

### Modular Design ✓
- Each component is independent
- Easy to test without hardware
- Simple to extend and customize

### Hardware Abstraction ✓
- Works with or without actual hardware
- Automatic fallback to simulation mode
- Thread-safe operations

### REST API ✓
```
POST   /api/motors/forward
POST   /api/motors/backward
POST   /api/motors/set-speed
POST   /api/camera/pan
POST   /api/camera/tilt
GET    /stream
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Full project overview & API docs |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design & patterns |
| [SETUP.md](docs/SETUP.md) | Installation & troubleshooting |
| [AGENT_INSTRUCTIONS.md](AGENT_INSTRUCTIONS.md) | Copilot context |

## 🔧 Customization

### Change Motor Pins
Edit `config/config.py`:
```python
MOTOR_LEFT_FORWARD = 17
MOTOR_LEFT_BACKWARD = 18
MOTOR_RIGHT_FORWARD = 27
MOTOR_RIGHT_BACKWARD = 22
```

### Adjust Camera
Edit `config/config.py`:
```python
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
STREAM_QUALITY = 80
```

### Modify Speed Limits
Edit `config/config.py`:
```python
MAX_SPEED = 100  # 0-100%
```

## 🧪 Testing Without Hardware

Everything works in simulation mode:
```bash
# On any computer (no Raspberry Pi needed)
uv sync --python 3.9
uv run python backend/app.py
```

Then navigate to `http://localhost:5000` - all controls respond but don't require hardware.

## 📡 Deployment

### Development
```bash
python backend/app.py
```

### Production (Auto-Start on Boot)
```bash
# Create systemd service (see SETUP.md)
sudo nano /etc/systemd/system/picar.service
```

### Monitor Logs
```bash
sudo journalctl -u picar.service -f
```

## 🐛 Troubleshooting

### Motor not moving?
1. Check GPIO pins are correct in `config.py`
2. Verify power supply to motors
3. Check motor connections
4. See detailed guide in `docs/SETUP.md`

### Camera not streaming?
```bash
# Verify camera
libcamera-hello --list-cameras

# Check resolution compatibility
libcamera-jpeg -o test.jpg
```

### I2C servo issues?
```bash
# Check I2C bus
i2cdetect -y 1

# Should show 0x40 (PCA9685)
```

## 🔐 Security Note

This system is designed for **local network only**:
- No authentication enabled
- No encryption (local network assumed secure)
- Future versions can add security features

For internet exposure, add:
- API key authentication
- HTTPS/TLS
- Rate limiting
- Input validation

## 📦 Dependencies

```
flask==2.3.0          # Web framework
flask-cors==4.0.0     # CORS support
picamera2==0.3.9      # Camera module
adafruit-pca9685==1.4.1  # Servo driver
RPi.GPIO==0.7.0       # GPIO control
```

## 🎯 Next Steps

1. **Immediate**: Copy to Raspberry Pi and test locally
2. **Soon**: Customize pin configuration for your setup
3. **Later**: Extend with new features (lights, sensors, etc.)
4. **Future**: Add autonomous navigation, cloud integration, etc.

## 📝 Git Workflow

```bash
# Push to private repo (setup remote first)
git remote add origin https://github.com/your-username/picar-x.git
git branch -M main
git push -u origin main

# Regular commits
git add .
git commit -m "description"
git push
```

## 📦 Dependency Management with uv

### Why uv over pip/venv?

| Feature | pip/venv | uv |
|---------|----------|-----|
| Speed | ⚠️ Slow | ⚡ 10-100x faster |
| Installation | Manual steps | Single command |
| Lock files | No | ✓ Yes (uv.lock) |
| Conflict detection | Basic | ✓ Advanced |
| Virtual environment | Manual | ✓ Automatic (.venv) |

### Common uv Commands

```bash
# Sync dependencies (install/update)
uv sync --python 3.9

# Add a new dependency
uv add flask-restful

# Update a dependency
uv update flask

# Run commands in virtual environment
uv run python app.py
uv run python -m pytest

# Install dev dependencies
uv sync --all-extras

# View installed packages
uv pip list
```

### Configuration

Settings are in `pyproject.toml`:
```toml
[project]
dependencies = [
    "flask==2.3.0",
    # ...
]

[project.optional-dependencies]
dev = ["pytest==7.4.0", "black==23.7.0"]
```

## 💡 Pro Tips

- Use 5GHz WiFi for lower latency
- Monitor CPU temp: `vcgencmd measure_temp`
- Backup SD card: `sudo dd if=/dev/mmcblk0 of=backup.img`
- Keep system updated: `sudo apt update && sudo apt upgrade`

## 🤝 Need Help?

1. Check **SETUP.md** for installation issues
2. Review **ARCHITECTURE.md** for design questions
3. See **README.md** for API documentation
4. Read **AGENT_INSTRUCTIONS.md** for development context

---

**Your modular, production-ready PiCar-X control system is ready to go!** 🚀

Happy coding! 🎉
