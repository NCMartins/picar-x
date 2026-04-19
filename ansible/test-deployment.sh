#!/bin/bash
# PiCar-X Ansible Deployment Test Script
# Run this on a Linux/Mac system with Ansible installed

set -e

echo "🔍 Testing Ansible PiCar-X Deployment"
echo "====================================="

# Check if ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo "❌ Ansible not found. Install with: pip install ansible"
    exit 1
fi

echo "✅ Ansible found: $(ansible-playbook --version | head -1)"

# Check syntax
echo ""
echo "📝 Checking playbook syntax..."
if ansible-playbook --syntax-check playbook.yml; then
    echo "✅ Playbook syntax is valid"
else
    echo "❌ Playbook syntax error"
    exit 1
fi

# Check inventory
echo ""
echo "📋 Checking inventory..."
if ansible -i inventory.ini --list-hosts picar | grep -q "hosts"; then
    echo "✅ Inventory is valid"
else
    echo "❌ Inventory error"
    exit 1
fi

# Check requirements
echo ""
echo "📦 Checking requirements file..."
if [ -f "requirements.yml" ]; then
    echo "✅ Requirements file exists"
else
    echo "❌ Requirements file missing"
fi

echo ""
echo "🎉 All checks passed!"
echo ""
echo "To deploy PiCar-X:"
echo "1. Configure inventory.ini with your Raspberry Pi IP"
echo "2. Configure group_vars/picar.yml for your setup"
echo "3. Run: ansible-playbook -i inventory.ini playbook.yml"
echo ""
echo "For more details, see README.md"