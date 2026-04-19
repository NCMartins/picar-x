# 📚 Documentation Index

Complete documentation for PiCar-X project setup, development, and deployment.

## 🚀 Getting Started

### For First-Time Setup (Start Here!)

1. **[QUICKSTART.md](QUICKSTART.md)** - 5-minute overview
   - Quick project structure overview
   - Installation quick reference
   - Key features list

2. **[docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)** - Complete Raspberry Pi Setup ⭐ **START HERE FOR RASPI**
   - Download and install Raspberry Pi OS
   - Initial boot configuration
   - Enable I2C and Camera interfaces
   - Network setup and SSH access
   - Hardware verification
   - Auto-start service setup
   - ~45 minutes total time

3. **[ansible/README.md](ansible/README.md)** - Automated Deployment ⭐ **RECOMMENDED FOR DEPLOYMENT**
   - Ansible playbook for automated setup
   - Complete system configuration
   - Hardware verification and testing
   - Service deployment and management
   - ~15 minutes total time (after OS setup)

4. **[docs/SETUP.md](docs/SETUP.md)** - Manual PiCar-X Installation
   - System dependencies
   - uv installation and usage
   - Code repository setup
   - Configuration and testing
   - Troubleshooting tips

## 📖 Main Documentation

### [README.md](README.md)
The main project documentation with:
- Feature overview
- Project structure
- Installation steps
- Usage instructions
- API endpoints reference
- Development guide
- Customization options
- Troubleshooting guide

### [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
Deep dive into project architecture:
- System design overview
- Component architecture
- Design patterns used
- Data flow diagrams
- Modularity benefits
- Adding new features guide
- Performance considerations

### [docs/SETUP.md](docs/SETUP.md)
Installation and troubleshooting:
- Prerequisites
- Step-by-step installation
- System dependency installation
- uv package manager guide
- Hardware pin configuration
- Running and testing
- Service auto-start
- Common issues and fixes

## 🤖 Development Documentation

### [AGENT_INSTRUCTIONS.md](AGENT_INSTRUCTIONS.md)
Instructions for GitHub Copilot and other AI assistants:
- Project context
- Architecture overview
- Key file locations
- Development guidelines
- Common tasks with examples
- Useful commands
- Future enhancement ideas

## 📋 Quick Reference Tables

### Documentation by Use Case

| Goal | Documentation |
|------|-----------------|
| Get started quickly | [QUICKSTART.md](QUICKSTART.md) |
| Setup Raspberry Pi OS | [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md) |
| Automated deployment | [ansible/README.md](ansible/README.md) |
| Manual installation | [docs/SETUP.md](docs/SETUP.md) |
| Understand architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| API reference | [README.md](README.md#api-endpoints) |
| Troubleshoot issues | [docs/SETUP.md](docs/SETUP.md#troubleshooting) |
| Customize project | [README.md](README.md#customization) |
| Develop new features | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#adding-new-features) |

### Documentation by Role

| Role | Start Here |
|------|-----------|
| **User (want to use it)** | [QUICKSTART.md](QUICKSTART.md) → [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md) → [ansible/README.md](ansible/README.md) |
| **Developer (fixing/extending)** | [AGENT_INSTRUCTIONS.md](AGENT_INSTRUCTIONS.md) → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **System Admin (deployment)** | [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md) → [ansible/README.md](ansible/README.md) |
| **Maintainer (overall project)** | [README.md](README.md) → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |

## 🔍 Key Sections

### Installation Timeline
1. **5 min**: Read [QUICKSTART.md](QUICKSTART.md)
2. **30-45 min**: Follow [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)
3. **10 min**: Complete [docs/SETUP.md](docs/SETUP.md) steps
4. **5 min**: Test system
5. **Total**: ~1 hour first-time setup

### Common Tasks Quick Links
- [Setup Raspberry Pi OS](docs/RASPI_OS_SETUP.md)
- [Install PiCar-X](docs/SETUP.md)
- [Configure GPIO pins](docs/RASPI_OS_SETUP.md#step-10-configure-gpio-pins-if-needed)
- [Enable auto-start](docs/RASPI_OS_SETUP.md#step-12-setup-auto-start-optional)
- [Access remotely via SSH](docs/RASPI_OS_SETUP.md#step-6-setup-ssh-access-optional)
- [Verify hardware](docs/RASPI_OS_SETUP.md#step-7-verify-hardware-connections)
- [Fix common issues](docs/SETUP.md#troubleshooting)

## 📝 File Organization

```
picar-x/
├── README.md                    ← Start here for overview
├── QUICKSTART.md                ← 5-minute quick reference
├── AGENT_INSTRUCTIONS.md        ← For AI/Copilot
├── docs/
│   ├── RASPI_OS_SETUP.md       ← Complete Raspberry Pi setup ⭐
│   ├── SETUP.md                ← PiCar-X installation
│   ├── ARCHITECTURE.md         ← Technical deep dive
│   └── INDEX.md                ← This file
├── config/
├── picar/
├── backend/
├── frontend/
└── pyproject.toml
```

## 🎓 Learning Path

### Beginner (Want to use it)
1. [QUICKSTART.md](QUICKSTART.md) - Understand what it does
2. [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md) - Setup Raspberry Pi
3. [docs/SETUP.md](docs/SETUP.md) - Install and run
4. [README.md](README.md#usage) - Learn basic usage

### Intermediate (Want to customize)
1. Complete beginner path
2. [README.md](README.md#customization) - Customization options
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Understand structure
4. [config/config.py](../config/config.py) - Modify settings

### Advanced (Want to extend)
1. Complete intermediate path
2. [AGENT_INSTRUCTIONS.md](AGENT_INSTRUCTIONS.md) - Development context
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#adding-new-features) - Add features
4. [Source code](../picar) - Read implementation

## 🔗 External Resources

### Raspberry Pi
- [Official Documentation](https://www.raspberrypi.com/documentation/)
- [GPIO Guide](https://www.raspberrypi.com/documentation/computers/os.html#gpio-and-the-gpioctl-tool)
- [Camera Guide](https://www.raspberrypi.com/documentation/computers/camera_software.html)

### Tools & Libraries
- [uv Documentation](https://docs.astral.sh/uv/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [RPi.GPIO Documentation](https://sourceforge.net/p/raspberry-gpio-python/wiki/Home/)
- [Adafruit PCA9685 Library](https://github.com/adafruit/Adafruit_Python_PCA9685)

### PiCar-X Specific
- [Sunfounder PiCar-X Official Guide](https://github.com/sunfounder)
- [Camera Module Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [I2C Servo Driver (PCA9685)](https://cdn-shop.adafruit.com/datasheets/PCA9685.pdf)

## 🆘 Quick Troubleshooting

**Can't access web interface?**
→ See [docs/SETUP.md#troubleshooting](docs/SETUP.md#troubleshooting)

**Camera not working?**
→ See [docs/RASPI_OS_SETUP.md#troubleshooting](docs/RASPI_OS_SETUP.md#troubleshooting)

**Motor not moving?**
→ See [docs/SETUP.md#motor-not-moving](docs/SETUP.md#motor-not-moving)

**I2C servo issues?**
→ See [docs/RASPI_OS_SETUP.md#i2c-device-not-found](docs/RASPI_OS_SETUP.md#i2c-device-not-found)

## 📞 Support Resources

1. **Check documentation** - Most issues covered in docs
2. **Review troubleshooting sections** - [SETUP.md](docs/SETUP.md#troubleshooting) and [RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md#troubleshooting)
3. **Search existing issues** - Check GitHub issues (if using GitHub)
4. **Read error messages carefully** - Often contain clues to the problem
5. **Test individual components** - See [docs/SETUP.md#testing-the-system](docs/SETUP.md#testing-the-system)

## 📊 Documentation Statistics

| Document | Purpose | Read Time |
|----------|---------|-----------|
| README.md | Project overview & API | 15 min |
| QUICKSTART.md | Quick reference | 5 min |
| docs/RASPI_OS_SETUP.md | Raspberry Pi setup | 45 min |
| docs/SETUP.md | Installation & troubleshooting | 20 min |
| docs/ARCHITECTURE.md | Technical deep dive | 20 min |
| AGENT_INSTRUCTIONS.md | AI assistant context | 10 min |

---

**👉 First time? Start with [QUICKSTART.md](QUICKSTART.md) then [docs/RASPI_OS_SETUP.md](docs/RASPI_OS_SETUP.md)**

**Happy coding!** 🚀
