# Raspberry Pi OS Setup Guide

Complete guide for setting up Raspberry Pi OS for PiCar-X project.

## Prerequisites

- Raspberry Pi 4B (recommended: 4GB or 8GB RAM)
- MicroSD card (32GB or larger, Class 10 recommended)
- microSD card reader
- USB-C power supply (5V/3A minimum)
- Ethernet cable OR WiFi access
- HDMI cable and monitor (for initial setup)
- USB keyboard and mouse

## Step 1: Download Raspberry Pi OS

### Option A: Using Raspberry Pi Imager (Easiest)

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Install on your computer (Windows, Mac, or Linux)
3. Insert microSD card into card reader
4. Open Raspberry Pi Imager
5. Click "Choose OS" → Select "Raspberry Pi OS (32-bit)" or "Raspberry Pi OS (64-bit)"
   - **Recommended**: 64-bit for better performance with PiCar-X
6. Click "Choose Storage" → Select your microSD card
7. Click "Settings" (gear icon) for advanced options:
   - Set hostname: `picar`
   - Enable SSH with password authentication
   - Set username/password: `pi` / `raspberry`
   - Configure WiFi (optional but recommended)
   - Set locale and timezone
8. Click "Write" and wait for completion

### Option B: Manual Download and Write

1. Download [Raspberry Pi OS image](https://www.raspberrypi.com/software/operating-systems/)
   - Choose "Raspberry Pi OS (64-bit)" for better performance
2. Extract the `.img` file from the zip archive
3. Write to microSD card:

**Windows**:
```powershell
# Using Balena Etcher (GUI - recommended)
# Download from https://www.balena.io/etcher/
# Open and select image, drive, and write

# Or using command line:
# Use Win32DiskImager or similar tool
```

**Linux/Mac**:
```bash
# Identify SD card device
diskutil list  # macOS
lsblk          # Linux

# Unmount if needed
diskutil unmountDisk /dev/diskX  # macOS
sudo umount /dev/sdX*            # Linux

# Write image (⚠️ This will erase the SD card!)
sudo dd if=raspberry-pi-os-image.img of=/dev/rdiskX bs=4m  # macOS
sudo dd if=raspberry-pi-os-image.img of=/dev/sdX bs=4M     # Linux

# Verify write completed
sudo diskutil eject /dev/diskX  # macOS
sudo eject /dev/sdX             # Linux
```

## Step 2: Initial Boot

1. **Insert microSD card** into Raspberry Pi
2. **Connect power** via USB-C
3. **Connect monitor** via HDMI
4. **Connect keyboard and mouse** via USB ports
5. **First boot takes 1-2 minutes**

You'll see:
- Raspberry Pi OS boot screen
- Desktop environment loads
- First-time setup wizard (if enabled)

## Step 3: Enable Required Interfaces

Open Terminal and run:

```bash
sudo raspi-config
```

Navigate through the menu:

### 3a. Enable I2C (For Servos)
```
3 Interface Options
   → I2C
   → Yes (Enable)
```

### 3b. Enable Camera
```
3 Interface Options
   → Camera
   → Yes (Enable)
```

### 3c. Enable SSH (Optional but recommended)
```
3 Interface Options
   → SSH
   → Yes (Enable)
```

### 3d. Expand Filesystem
```
6 Advanced Options
   → Expand Filesystem
   → (Automatically expands SD card usage)
```

### 3e. Set GPU Memory (Optional for better camera performance)
```
6 Advanced Options
   → GPU Memory
   → Set to 256MB or higher
```

After each change, select **Finish** and reboot when prompted:
```bash
sudo reboot
```

## Step 4: Update System

Open Terminal and run:

```bash
# Update package lists
sudo apt-get update

# Upgrade all packages
sudo apt-get upgrade -y

# Install additional tools
sudo apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    i2c-tools \
    python3-dev \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libcamera-tools
```

This may take 10-15 minutes. Go grab a coffee! ☕

## Step 5: Set Static IP Address (Optional but recommended)

Static IP makes it easier to access your PiCar-X consistently.

### For WiFi:

Edit netplan configuration:
```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:
```bash
# WiFi interface
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 1.1.1.1
```

Save (Ctrl+X, Y, Enter) and reboot:
```bash
sudo reboot
```

### For Ethernet:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:
```bash
# Ethernet interface
interface eth0
static ip_address=192.168.1.101/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 1.1.1.1
```

Save and reboot:
```bash
sudo reboot
```

After reboot, find your IP:
```bash
hostname -I
```

## Step 6: Setup SSH Access (Optional)

Connect from another computer without monitor/keyboard.

### From Linux/Mac:
```bash
# Find Pi IP first
ping picar.local

# Or use:
nmap -sn 192.168.1.0/24 | grep -i raspberry

# SSH into Pi
ssh pi@192.168.1.100
# Password: raspberry
```

### From Windows:

Use PuTTY or Windows built-in SSH:
```powershell
ssh pi@192.168.1.100
```

### Security tip - Change default password:
```bash
passwd
```

## Step 7: Verify Hardware Connections

### Check I2C Servo Driver
```bash
i2cdetect -y 1
```

Look for PCA9685 at address 0x40:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
```

### Check Camera
```bash
libcamera-hello --list-cameras
```

Expected output:
```
Available cameras
0 : imx219 [3280x2464] (/base/soc/i2c0mux/i2c@1,45000/imx219@10)
```

### Check GPIO
```bash
# List GPIO info
gpioinfo

# Check if pins are accessible
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
```

## Step 8: Install uv (Python Package Manager)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Verify installation
uv --version
```

## Step 9: Clone PiCar-X Repository

```bash
# Create projects directory
mkdir -p ~/projects

# Clone repository
cd ~/projects
git clone <your-repo-url> picar-x
cd picar-x

# Sync dependencies
uv sync --python 3.9
```

## Step 10: Configure GPIO Pins (If needed)

Edit the GPIO pin configuration to match your PiCar-X setup:

```bash
nano config/config.py
```

Verify or adjust:
```python
# Motor pins (BCM numbering - based on your wiring)
MOTOR_LEFT_FORWARD = 17
MOTOR_LEFT_BACKWARD = 18
MOTOR_RIGHT_FORWARD = 27
MOTOR_RIGHT_BACKWARD = 22

# Servo channels (PCA9685 - usually correct as-is)
SERVO_PAN_CHANNEL = 0
SERVO_TILT_CHANNEL = 1

# Camera settings
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
```

## Step 11: Test the System

```bash
# Start the server
cd ~/projects/picar-x
uv run python backend/app.py
```

You should see:
```
Motor controller initialized successfully
Servo controller initialized successfully
Camera initialized successfully
Starting Flask server on 0.0.0.0:5000
 * Running on http://0.0.0.0:5000
```

### Access from Another Computer:

Open browser and navigate to:
```
http://<pi-ip>:5000
```

Example:
```
http://192.168.1.100:5000
```

## Step 12: Setup Auto-Start (Optional)

Make PiCar-X start automatically on boot:

```bash
sudo nano /etc/systemd/system/picar.service
```

Paste:
```ini
[Unit]
Description=PiCar-X Control Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/projects/picar-x
ExecStart=/home/pi/.cargo/bin/uv run python backend/app.py
Environment="PATH=/home/pi/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable picar.service
sudo systemctl start picar.service
```

Check status:
```bash
sudo systemctl status picar.service

# View logs
sudo journalctl -u picar.service -f
```

## Troubleshooting

### raspi-config not found
```bash
sudo apt-get install raspi-config
sudo raspi-config
```

### Camera not detected
```bash
# Full camera diagnostics
libcamera-hello --verbose

# Check for libcamera issues
dpkg -l | grep libcamera

# Reinstall if needed
sudo apt-get install --reinstall libcamera0 libcamera-apps
```

### I2C device not found
```bash
# Check I2C module loaded
lsmod | grep i2c

# Load I2C modules if needed
sudo modprobe i2c_dev
sudo modprobe i2c_bcm2835

# Verify PCA9685 connections (power, ground, SDA, SCL)
```

### GPIO permission issues
```bash
# Add user to GPIO groups
sudo usermod -aG gpio pi
sudo usermod -aG i2c pi

# Log out and back in for changes to take effect
exit
```

### Low performance/Camera lag
```bash
# Check CPU temperature
vcgencmd measure_temp

# Check available memory
free -h

# Check disk space
df -h

# If CPU hot (>80°C), consider heatsink
```

## Performance Optimization

### 1. Disable unnecessary services
```bash
# Disable Bluetooth (if not using)
sudo systemctl disable bluetooth.service

# Disable avahi-daemon (if not using mDNS)
sudo systemctl disable avahi-daemon

# Disable CUPS printing
sudo systemctl disable cups
```

### 2. Overclock GPU (Optional, for camera)
```bash
sudo nano /boot/config.txt
```

Add:
```
gpu_mem=256
```

### 3. Use SSD for faster I/O
If using USB boot:
```bash
# Set boot order to USB first
sudo nano /boot/firmware/config.txt
```

Add:
```
boot_order=0xf12
```

## Next Steps

1. ✅ Clone PiCar-X repository
2. ✅ Run setup script
3. ✅ Access web interface at `http://<pi-ip>:5000`
4. ✅ Test controls and camera stream
5. 🚀 Start controlling your PiCar-X!

## Useful Commands

```bash
# System info
uname -a
cat /etc/os-release
vcgencmd measure_clock arm
vcgencmd measure_temp

# Network
hostname -I
ifconfig
ping 8.8.8.8

# Storage
df -h
du -sh *

# Processes
top
ps aux | grep python

# Logs
journalctl -xe
dmesg | tail -20
```

## Additional Resources

- [Raspberry Pi Official Documentation](https://www.raspberrypi.com/documentation/)
- [Raspberry Pi OS Setup](https://www.raspberrypi.com/documentation/computers/getting-started.html)
- [GPIO Documentation](https://www.raspberrypi.com/documentation/computers/os.html#gpio-and-the-gpioctl-tool)
- [Camera Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)

---

**Your Raspberry Pi is now ready for PiCar-X!** 🚀
