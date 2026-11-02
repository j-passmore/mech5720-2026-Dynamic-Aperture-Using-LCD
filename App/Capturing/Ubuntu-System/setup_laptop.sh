#!/usr/bin/env bash
# The root half of the laptop setup: gphoto2 for the 60D and serial access for the Uno.
# The Python venv (.venv) and arduino-cli with the Uno core and panel libraries need no root.
# Log out and back in afterwards so the dialout group takes effect.
set -euo pipefail

sudo apt update
sudo apt install -y gphoto2

# GNOME's camera monitor mounts the 60D as a drive when it reconnects and gphoto2 then cannot
# claim it. Any file dialog, camview's Browse included, starts the monitor again, so mask it.
# Undo with: systemctl --user unmask gvfs-gphoto2-volume-monitor.service
systemctl --user mask gvfs-gphoto2-volume-monitor.service

# serial port access for /dev/ttyACM0
sudo usermod -aG dialout "$USER"

# ModemManager probes a new /dev/ttyACM device for a few seconds and breaks the first connection.
# brltty claims the CH340 bridge on clone Unos (/dev/ttyUSB0). Neither is needed here.
sudo apt remove -y modemmanager brltty

echo "Done. Log out and back in, then check with: groups | grep dialout"
