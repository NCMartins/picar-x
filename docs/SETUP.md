# Setup & Installation Guide

## 🚀 Deployment Options

### Option 1: Automated Deployment (Recommended)

For the fastest and most reliable setup, use the **Ansible playbook**:

1. Setup Raspberry Pi OS: [RASPI_OS_SETUP.md](RASPI_OS_SETUP.md)
2. Deploy automatically: [ansible/README.md](../ansible/README.md)

```bash
# On your control machine (not the Pi)
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```

This handles everything automatically: system configuration, dependency installation, hardware setup, and service deployment.

### Option 2: Manual Installation (Advanced)

Follow the step-by-step manual installation below if you prefer hands-on control or need custom configuration.

## ⚠️ Prerequisites

- **Raspberry Pi 4B** with 4GB+ RAM
- **MicroSD card** 32GB+ (Class 10)
- **PiCar-X kit** from Sunfounder
- **Camera module** (Pi Camera V2 or V3)
- **Internet connection** for dependency installation
- **USB-C power supply** (5V/3A minimum)

## Quick Start

### Step 1: Setup Raspberry Pi OS

**For complete step-by-step instructions**, see **[RASPI_OS_SETUP.md](RASPI_OS_SETUP.md)**

This includes:
- Downloading Raspberry Pi OS
- Writing to microSD card
- Initial boot configuration
- Enabling I2C and Camera
- Network setup
- SSH configuration
- Hardware verification

**Quick reference**:
```bash
# 1. Download Raspberry Pi Imager
https://www.raspberrypi.com/software/

# 2. Write OS to microSD card
# 3. Boot Raspberry Pi
# 4. Enable interfaces
sudo raspi-config
# → Interface Options → I2C → Yes
# → Interface Options → Camera → Yes
# → Finish & Reboot

# 5. Update system
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install Required Packages

### Step 3: Install System Dependencies

```bash
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    i2c-tools \
    python3-dev \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libcamera-tools
```

### Step 4: Install uv (Fast Python Package Manager)

uv is a blazing-fast Python package installer written in Rust:

```bash
# Install uv
curl -LsS5: Clone Repository

```bash
# Create projects directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone <your-repo-url> picar-x
cd picar-x
```

### Step 6
**Why uv?**
- ⚡ 10-100x faster than pip
- 🔒 Dependency resolution with conflict detection
- 📦 Automatic virtual environment management
- 🐍 Works with any Python version

### Step 4: Clone Repository

```bash
cd ~
git clone <your-repo-url>
cd picar-x
```

### Step 5: Sync Dependencies with uv

```bash
# Sync all dependencies (creates .venv automatically)
uv sync --python 3.9

# Verify insConfigure Hardware Pins (If Needed)

Verify GPIO pin assignments match your setup:

```bash
nano ~/projects/picar-x/config/config.py
```

Check these values:
```python
# Motor pins (BCM numbering)
MOTOR_LEFT_FORWARD = 17
MOTOR_LEF9_BACKWARD = 18
MOTOR_RIGHT_FORWARD = 27
MOTOR_RIGHT_BACKWARD = 22

# Servo channels (PCA9685)
SERVO_PAN_CHANNEL = 0
SERVO_TILT_CHANNEL = 1
```

Adjust if your wiring is different.

### Step 8: tallation
uv pip list
```

### Step 7: Verify Camera

```bash
libcamera-hello --list-cameras
```

You should see output like:
```
Available cameras
0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1,45000/imx219@10)
```

### Step 8: Verify I2C Servo Driver

```bash
i2cdetect -y 1
```

Look for PCA9685 (usually at address 0x40):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
```

## Pin Configuration

### GPIO Motor Pins (BCM numbering)

Verify connections in `config/config.py`:

| Motor | Forward | Backward |
|-------|---------|----------|
| Left  | GPIO 17 | GPIO 18  |
| Right | GPIO 27 | GPIO 22  |

### I2C Servo Driver

Default PCA9685 address: `0x40` (verify with `i2cdetect`)

| Function | Channel |
|----------|---------|
| Pan      | 0       |
| Tilt     | 1       |

## Starting the Server

### Option 1: Quick Start with uv

```bash
# Sync dependencies (one-time setup)
uv sync --python 3.9

# Run server
uv run python backend/app.py
```

### Option 2: Using Launch Scripts

```bash
# Linux/Raspberry Pi
chmod +x start.sh
./start.sh

# Windows
start.bat
```

Expected output:
```
Motor controller initialized successfully
Servo controller initialized successfully
Camera initialized successfully
Starting Flask server on 0.0.0.0:5000
```

### Option 3: Run as Service (Autostart)

Create systemd service:

```bash
sudo nano /etc/systemd/system/picar.service
```

Add the following (adjust path to your installation):

```ini
[Unit]
Description=PiCar-X Control Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/picar-x
ExecStart=/home/pi/.cargo/bin/uv run python backend/app.py
Environment="PATH=/home/pi/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable picar.service
sudo systemctl start picar.service
sudo systemctl status picar.service
```

View logs:
```bash
sudo journalctl -u picar.service -f
```

## Accessing the Web Interface

### On Raspberry Pi

```bash
# Find IP address
hostname -I

# Example output: 192.168.1.100
```

### From Another Computer

Open browser and navigate to:
```
http://<raspberry-pi-ip>:5000
```

Example:
```
http://192.168.1.100:5000
```

## Firewall Configuration

If you need to access from outside the local network (not recommended for security):

```bash
# Open Flask port
sudo ufw allow 5000/tcp
sudo ufw allow 5000/udp
```

## Testing the System

### Test with uv

```bash
# Run Python commands with uv
uv run python3 <<'EOF'
from picar.motors import get_motor_controller
motor = get_motor_controller()
motor.forward(speed=50)
import time; time.sleep(2)
motor.stop()
EOF
```

Or create interactive Python session:

```bash
uv run python3
>>> from picar.motors import get_motor_controller
>>> motor = get_motor_controller()
>>> motor.forward(speed=50)
>>> import time; time.sleep(2)
>>> motor.stop()
>>> exit()
```

### Test Servos

```bash
uv run python3
>>> from picar.servos import get_servo_controller
>>> servo = get_servo_controller()
>>> servo.set_pan(45)
>>> servo.center()
>>> exit()
```

### Test Camera

```bash
uv run python3
>>> from picar.camera import get_camera_stream
>>> camera = get_camera_stream()
>>> frame = camera.get_frame()
>>> print(len(frame), "bytes")
>>> exit()
```

### Test API

```bash
# Check health
curl http://localhost:5000/api/health

# Move forward
curl -X POST http://localhost:5000/api/motors/forward \
  -H "Content-Type: application/json" \
  -d '{"speed": 75}'

# Get motor status
curl http://localhost:5000/api/motors/status
```

## Troubleshooting

### Camera Not Working

**Issue**: "Camera not available" error

**Solutions**:
```bash
# Verify camera is enabled
sudo raspi-config
# → Interfacing Options → Camera → Yes

# Check camera detection
libcamera-hello --list-cameras

# Check for conflicts
lsmod | grep v4l2
```

### I2C Servo Issues

**Issue**: "No address found on I2C bus 1"

**Solutions**:
```bash
# Check I2C detection
sudo i2cdetect -y 1

# Check I2C is enabled
ls /dev/i2c-*

# Verify connections on servo driver

# Test communication
i2ctransfer -y 1 w2@0x40 0x00 0x00
```

### GPIO Permission Denied

**Issue**: "RuntimeError: No access to /dev/mem"

**Solutions**:
```bash
# Add user to GPIO group
sudo usermod -aG gpio pi
sudo usermod -aG i2c pi

# Log out and back in for changes to take effect
exit
```

### Motor Not Moving

**Issue**: Motors don't respond to commands

**Debug**:
```bash
# Check GPIO export
ls /sys/class/gpio/

# Verify motor connections
# Test with multimeter for voltage
```

**Solutions**:
1. Check motor power supply voltage
2. Verify GPIO pin assignments in config.py
3. Test with simple GPIO script:
   ```python
   import RPi.GPIO as GPIO
   GPIO.setmode(GPIO.BCM)
   GPIO.setup(17, GPIO.OUT)
   GPIO.output(17, GPIO.HIGH)  # Should power motor
   ```

### Stream Latency Issues

**Issue**: Video stream is delayed or choppy

**Solutions**:
1. Reduce resolution in `config.py`:
   ```python
   CAMERA_RESOLUTION = (480, 360)  # Instead of 640x480
   ```

2. Lower framerate:
   ```python
   CAMERA_FRAMERATE = 15  # Instead of 30
   ```

3. Reduce quality:
   ```python
   STREAM_QUALITY = 60  # Instead of 80
   ```

4. Use 5GHz WiFi if available

## Optimization Tips

### Performance

- Run on 5GHz WiFi for lower latency
- Use static IP for consistent connectivity
- Keep Python virtual environment active

### Battery Life

- Reduce camera framerate when not needed
- Implement sleep modes for idle periods
- Optimize motor acceleration curves

### Reliability

- Monitor CPU temperature: `vcgencmd measure_temp`
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Regular backups: `sudo dd if=/dev/mmcblk0 of=backup.img`

---

**For additional help, check ARCHITECTURE.md and README.md**
