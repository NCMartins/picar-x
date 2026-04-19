#!/bin/bash
# PiCar-X Quick Start Script for Raspberry Pi

set -e

echo "==========================================="
echo "PiCar-X Setup & Launch Script"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}Project directory: $PROJECT_DIR${NC}"

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first:"
    echo "  sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$PROJECT_DIR/venv"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$PROJECT_DIR/venv/bin/activate"

# Install requirements
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --upgrade pip setuptools wheel
    pip install -r "$PROJECT_DIR/requirements.txt"
fi

# Navigate to backend and start server
echo -e "${GREEN}Starting PiCar-X server...${NC}"
echo -e "${BLUE}Access the web interface at: http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo ""

cd "$PROJECT_DIR/backend"
python app.py
