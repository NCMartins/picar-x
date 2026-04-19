# Setup & Installation Guide

## Quick Start

### Prerequisites
- Raspberry Pi 4B with Raspberry Pi OS (32-bit or 64-bit)
- PiCar-X kit from Sunfounder
- Camera module (Pi Camera V2 or V3)
- Internet connection for dependency installation
- USB keyboard/mouse or SSH access

### Step 1: Enable Interfaces

```bash
sudo raspi-config
```

Navigate to:
1. Interface Options → I2C → Yes (Enable)
2. Interface Options → Camera → Yes (Enable)
3. Interface Options → SSH → Yes (Enable) [Optional, for remote access]
4. Finish and reboot

### Step 2: Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 3: Install Dependencies

```bash
# Install system packages
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libcamera-tools \
    python3-libcamera \
    python3-kms++

# For I2C communication
sudo apt-get install -y i2c-tools python3-smbus
```

### Step 4: Clone Repository

```bash
cd ~
git clone <your-repo-url>
cd picar-x
```

### Step 5: Setup Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 6: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
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

### Option 1: Direct Execution

```bash
cd ~/picar-x
source venv/bin/activate
cd backend
python app.py
```

Expected output:
```
Motor controller initialized successfully
Servo controller initialized successfully
Camera initialized successfully
Starting Flask server on 0.0.0.0:5000
```

### Option 2: Run as Service (Autostart)

Create systemd service:

```bash
sudo nano /etc/systemd/system/picar.service
```

Add the following:

```ini
[Unit]
Description=PiCar-X Control Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/picar-x/backend
ExecStart=/home/pi/picar-x/venv/bin/python app.py
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

### Test Motors

```python
python3
>>> from picar.motors import get_motor_controller
>>> motor = get_motor_controller()
>>> motor.forward(speed=50)
>>> import time; time.sleep(2)
>>> motor.stop()
>>> exit()
```

### Test Servos

```python
python3
>>> from picar.servos import get_servo_controller
>>> servo = get_servo_controller()
>>> servo.set_pan(45)
>>> servo.center()
>>> exit()
```

### Test Camera

```python
python3
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
