#!/bin/bash
# PiCar-X Quick Start Script for Raspberry Pi using uv
# Skips Windows tests - designed exclusively for Linux/Raspberry Pi

set -e

echo "==========================================="
echo "PiCar-X Setup & Launch Script (uv)"
echo "==========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on Windows (skip Windows tests)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo -e "${YELLOW}Warning: This script is designed for Linux/Raspberry Pi.${NC}"
    echo -e "${YELLOW}For Windows development, use start.bat instead.${NC}"
    echo -e "${YELLOW}Skipping Windows compatibility tests...${NC}"
    exit 1
fi

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}Project directory: $PROJECT_DIR${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}uv installed successfully. Continuing...${NC}"
fi

# Create virtual environment with system site packages
echo -e "${YELLOW}Creating virtual environment with system site packages...${NC}"
rm -rf .venv
if ! python3 -m venv --system-site-packages .venv; then
    echo -e "${RED}Failed to create virtual environment.${NC}"
    exit 1
fi

# Install dependencies using uv
echo -e "${YELLOW}Installing dependencies with uv...${NC}"
if ! uv pip install -r requirements.txt; then
    echo -e "${RED}Failed to install dependencies. Please check your Python installation.${NC}"
    exit 1
fi

# Navigate to backend and start server
echo -e "${GREEN}Starting PiCar-X server...${NC}"

# Get IP address for display (Linux-specific)
IP_ADDRESS=$(hostname -I | awk '{print $1}')
if [[ -z "$IP_ADDRESS" ]]; then
    IP_ADDRESS="localhost"
fi
echo -e "${BLUE}Access the web interface at: http://${IP_ADDRESS}:5000${NC}"
echo ""

cd "$PROJECT_DIR/backend"
source "$PROJECT_DIR/.venv/bin/activate"
if ! python app.py; then
    echo -e "${RED}Failed to start the server. Please check the error messages above.${NC}"
    exit 1
fi
