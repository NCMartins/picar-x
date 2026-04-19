#!/bin/bash
# PiCar-X Quick Start Script for Raspberry Pi using uv

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

# Sync dependencies using uv
echo -e "${YELLOW}Syncing dependencies with uv...${NC}"
if ! uv sync --python 3.9; then
    echo -e "${RED}Failed to sync dependencies. Please check your Python 3.9 installation.${NC}"
    exit 1
fi

# Navigate to backend and start server
echo -e "${GREEN}Starting PiCar-X server...${NC}"

# Get IP address for display
IP_ADDRESS=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname -i 2>/dev/null || echo "localhost")
echo -e "${BLUE}Access the web interface at: http://${IP_ADDRESS}:5000${NC}"
echo ""

cd "$PROJECT_DIR/backend"
if ! uv run python app.py; then
    echo -e "${RED}Failed to start the server. Please check the error messages above.${NC}"
    exit 1
fi
