#!/bin/bash
# Stop and disable the boot-time PiCar-X service.

set -euo pipefail

SERVICE_NAME="${1:-picar-startup}"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs sudo/root to manage systemd services."
    echo "Run: sudo ./stop_boot_service.sh [service-name]"
    exit 1
fi

if ! systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    echo "Service ${SERVICE_NAME}.service was not found."
    echo "Tip: try 'picar' if you installed via Ansible."
    exit 1
fi

systemctl stop "${SERVICE_NAME}"
systemctl disable "${SERVICE_NAME}"

echo "Stopped and disabled: ${SERVICE_NAME}.service"
echo "Status:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
