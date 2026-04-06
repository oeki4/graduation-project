#!/bin/bash

# Configuration
SERVICE_FILE="voice-assistant.service"
SYSTEMD_PATH="/etc/systemd/system/"
USER_NAME="pi" # Change if your username is different

echo "🔧 Installing Voice Assistant autostart..."

# Update path in the service file to use the current directory if it's correct
CURRENT_DIR=$(pwd)
# We assume this script is in scripts/raspberry-pi/ and the main app is in core/
PROJECT_ROOT=$(dirname $(dirname "$CURRENT_DIR"))
APP_DIR="$PROJECT_ROOT/core"
PYTHON_VENV="$APP_DIR/.venv/bin/python3"

# Update fields in the service template (creating a temporary version)
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$APP_DIR|g" "$SERVICE_FILE"
sed -i "s|ExecStart=.*|ExecStart=$PYTHON_VENV main.py|g" "$SERVICE_FILE"
sed -i "s|User=.*|User=$USER_NAME|g" "$SERVICE_FILE"

# Copy the file to systemd directory
echo "📝 Copying $SERVICE_FILE to $SYSTEMD_PATH..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"

# Reload systemd and enable/start the service
echo "🚀 Enabling and starting the service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_FILE"
sudo systemctl start "$SERVICE_FILE"

echo "✅ Done! You can check the status with: sudo systemctl status voice-assistant"
echo "🔍 View logs with: journalctl -u voice-assistant -f"
