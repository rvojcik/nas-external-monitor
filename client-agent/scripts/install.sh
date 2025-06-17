#!/bin/bash
set -e

echo "Installing M5Stack NAS Monitor Client Agent..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "This script should not be run as root. Please run as a regular user."
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv lm-sensors smartmontools zfsutils-linux

# Add user to dialout group for serial port access
echo "Adding user to dialout group..."
sudo usermod -a -G dialout $USER

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python package
echo "Installing Python package..."
pip install -e .

# Create configuration directory
echo "Setting up configuration..."
sudo mkdir -p /etc
sudo cp config/m5nas-monitor.conf /etc/

# Install systemd service
echo "Installing systemd service..."
sudo cp systemd/m5nas-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# Initialize sensors
echo "Initializing sensors..."
sudo sensors-detect --auto || echo "Warning: sensors-detect failed or not available"

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/m5nas-monitor.log
sudo chown $USER:$USER /var/log/m5nas-monitor.log

echo ""
echo "Installation completed!"
echo ""
echo "Next steps:"
echo "1. Connect your M5Stack device to a USB port"
echo "2. Find the serial port: ls /dev/ttyUSB* /dev/ttyACM*"
echo "3. Edit configuration: sudo nano /etc/m5nas-monitor.conf"
echo "4. Test the connection: m5nas-test --port /dev/ttyUSB0"
echo "5. Start the service: sudo systemctl enable --now m5nas-monitor"
echo ""
echo "You may need to log out and back in for group changes to take effect."