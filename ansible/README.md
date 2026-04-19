# PiCar-X Ansible Deployment

This directory contains Ansible playbooks and roles for automated deployment of the PiCar-X remote control system to a Raspberry Pi.

## Prerequisites

1. **Control Machine Requirements:**
   - Ansible 2.9+ installed
   - SSH access to Raspberry Pi
   - SSH key pair configured for passwordless authentication

2. **Target Raspberry Pi:**
   - Fresh Raspberry Pi OS (64-bit) installation
   - SSH enabled
   - Network connectivity
   - Internet access for package installation

## Quick Start

1. **Configure Inventory:**
   ```bash
   # Edit ansible/inventory.ini with your Raspberry Pi details
   nano ansible/inventory.ini
   ```

2. **Configure Variables:**
   ```bash
   # Edit ansible/group_vars/picar.yml for your setup
   nano ansible/group_vars/picar.yml
   ```

3. **Deploy:**
   ```bash
   cd ansible
   ansible-playbook -i inventory.ini playbook.yml
   ```

## Configuration

### Inventory Configuration (`inventory.ini`)

```ini
[picar]
# Replace with your Raspberry Pi IP address
picar ansible_host=192.168.1.100 ansible_user=pi ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### Variables Configuration (`group_vars/picar.yml`)

Key variables to customize:

- **Repository Settings:**
  - `picar_repo_url`: Git repository URL
  - `picar_repo_branch`: Branch to deploy
  - `picar_install_path`: Installation directory

- **Network Settings:**
  - `picar_static_ip`: Static IP address
  - `picar_netmask`: Network mask
  - `picar_gateway`: Gateway IP
  - `picar_dns_servers`: DNS servers

- **Hardware Settings:**
  - Motor pin assignments
  - Servo channels
  - Camera resolution and framerate

## Deployment Process

The Ansible playbook performs the following tasks:

1. **System Setup:**
   - Updates packages and installs dependencies
   - Configures timezone and hostname
   - Sets up static IP networking
   - Enables I2C, Camera, and SSH interfaces

2. **PiCar-X Deployment:**
   - Clones the repository
   - Installs Python dependencies with uv
   - Configures hardware settings
   - Creates and enables systemd service
   - Verifies hardware availability

3. **Verification:**
   - Tests camera, I2C, and GPIO access
   - Confirms web service is running
   - Displays deployment summary

## Usage After Deployment

Once deployed, access your PiCar-X:

- **Web Interface:** `http://<RASPBERRY_PI_IP>:5000`
- **SSH Access:** `ssh pi@<RASPBERRY_PI_IP>`
- **Service Management:**
  ```bash
  sudo systemctl status picar
  sudo systemctl restart picar
  sudo journalctl -u picar -f
  ```

## Troubleshooting

### Common Issues

1. **SSH Connection Failed:**
   - Verify SSH key is configured
   - Check Raspberry Pi IP address
   - Ensure SSH is enabled on Raspberry Pi

2. **Hardware Not Detected:**
   - Camera: Run `libcamera-hello --list-cameras`
   - I2C: Run `i2cdetect -y 1`
   - GPIO: Check user is in `gpio` group

3. **Service Not Starting:**
   ```bash
   sudo journalctl -u picar -xe
   sudo systemctl status picar
   ```

### Manual Verification

After deployment, you can manually verify components:

```bash
# Check camera
libcamera-hello --list-cameras

# Check I2C devices
i2cdetect -y 1

# Test GPIO access
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"

# Check service status
sudo systemctl status picar

# View service logs
sudo journalctl -u picar -f

# Test web interface
curl http://localhost:5000/api/health
```

## Advanced Configuration

### Custom Hardware Wiring

If your PiCar-X has different pin assignments, update `group_vars/picar.yml`:

```yaml
picar_motor_left_forward: 17    # BCM pin number
picar_motor_left_backward: 18
picar_motor_right_forward: 27
picar_motor_right_backward: 22
picar_servo_pan_channel: 0     # PCA9685 channel
picar_servo_tilt_channel: 1
```

### Multiple Raspberry Pis

For multiple PiCar-X robots, add entries to `inventory.ini`:

```ini
[picar]
picar1 ansible_host=192.168.1.100 ansible_user=pi
picar2 ansible_host=192.168.1.101 ansible_user=pi
picar3 ansible_host=192.168.1.102 ansible_user=pi
```

### WiFi Configuration

For WiFi instead of Ethernet, modify the DHCP template in `roles/common/templates/dhcpcd.conf.j2`:

```bash
interface wlan0
static ip_address={{ picar_static_ip }}/{{ picar_netmask }}
static routers={{ picar_gateway }}
static domain_name_servers={{ picar_dns_servers | join(' ') }}
```

## Security Considerations

- Change default SSH keys
- Configure firewall rules if needed
- Use strong passwords
- Keep system updated
- Monitor service logs

## Development

To modify the Ansible deployment:

1. **Test Locally:**
   ```bash
   ansible-playbook --check -i inventory.ini playbook.yml
   ```

2. **Run Specific Roles:**
   ```bash
   ansible-playbook -i inventory.ini playbook.yml --tags common
   ansible-playbook -i inventory.ini playbook.yml --tags picar
   ```

3. **Debug Mode:**
   ```bash
   ansible-playbook -i inventory.ini playbook.yml -vvv
   ```

## Support

For issues with the PiCar-X system itself, see the main project documentation in `docs/`.

For Ansible deployment issues, check:
- Ansible documentation: https://docs.ansible.com/
- Raspberry Pi Ansible collection: https://github.com/raspberrypi/ansible-collection-raspberrypi