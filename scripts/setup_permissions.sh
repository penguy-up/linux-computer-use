#!/usr/bin/env bash
set -e

# Setup permissions for /dev/uinput on Deepin OS
# This enables direct hardware absolute mouse and pointer simulation.

echo "=== Configuring /dev/uinput permissions for user $(whoami) ==="

RULE_PATH="/etc/udev/rules.d/99-uinput.rules"

echo "Creating udev rule: $RULE_PATH"
sudo bash -c "cat << 'EOF' > $RULE_PATH
KERNEL==\"uinput\", GROUP=\"input\", MODE=\"0660\"
EOF"

echo "Adding user $USER to group input..."
sudo usermod -aG input "$USER"

echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Setting permissions on /dev/uinput for current session..."
sudo chmod 660 /dev/uinput
sudo chgrp input /dev/uinput

echo "=== Permission setup complete! ==="
echo "Note: Log out and log back in for group membership to permanently take effect in all shells."
