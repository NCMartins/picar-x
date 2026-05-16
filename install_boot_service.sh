#!/bin/bash
# Install and enable a systemd service that runs the PiCar-X backend on boot.

set -euo pipefail

SERVICE_NAME="picar-startup"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
APP_ENTRY="$BACKEND_DIR/app.py"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
RUN_USER="${SUDO_USER:-${USER}}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs sudo/root to write systemd unit files."
    echo "Run: sudo ./install_boot_service.sh"
    exit 1
fi

if ! id "$RUN_USER" >/dev/null 2>&1; then
    echo "Could not resolve service user: $RUN_USER"
    echo "Run with sudo from your normal account, e.g.: sudo ./install_boot_service.sh"
    exit 1
fi

RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
if [[ -z "$RUN_HOME" || ! -d "$RUN_HOME" ]]; then
    echo "Could not resolve home directory for user: $RUN_USER"
    exit 1
fi

RUN_GROUP="$(id -gn "$RUN_USER")"

if [[ ! -f "$APP_ENTRY" ]]; then
    echo "Could not find backend app at: $APP_ENTRY"
    exit 1
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Virtual environment Python not found at: $VENV_PYTHON"
    echo "Create it first, for example:"
    echo "  uv venv && uv pip install -r requirements.txt"
    exit 1
fi

if ! "$VENV_PYTHON" -c "import flask, flask_cors" >/dev/null 2>&1; then
    echo "Required Python packages are missing in $VENV_PYTHON"
    echo "Install dependencies into that interpreter with:"
    echo "  uv pip install --python $VENV_PYTHON -r $PROJECT_DIR/requirements.txt"
    exit 1
fi

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=PiCar-X backend web service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON $APP_ENTRY
Environment=HOME=$RUN_HOME
Environment=PATH=$RUN_HOME/.cargo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl --no-pager --full status "$SERVICE_NAME" >/dev/null 2>&1 || true
systemd-analyze verify "$SERVICE_FILE" >/dev/null 2>&1 || {
    echo "Warning: systemd-analyze reported issues in $SERVICE_FILE"
}
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "Service installed and enabled: ${SERVICE_NAME}.service"
echo "Check status with: sudo systemctl status ${SERVICE_NAME}.service"
echo "View logs with: sudo journalctl -u ${SERVICE_NAME}.service -f"
