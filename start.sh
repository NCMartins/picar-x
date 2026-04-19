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
NC='\033[0m' # No Color

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}Project directory: $PROJECT_DIR${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Sync dependencies using uv
echo -e "${YELLOW}Syncing dependencies with uv...${NC}"
uv sync --python 3.9

# Navigate to backend and start server
echo -e "${GREEN}Starting PiCar-X server...${NC}"
echo -e "${BLUE}Access the web interface at: http://$(hostname -I | awk '{print $1}'):5000${NC}"
echo ""

cd "$PROJECT_DIR/backend"
uv run python app.py
