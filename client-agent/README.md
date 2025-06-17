# M5Stack NAS Monitor - Client Agent

Python daemon application that collects system information and sends it to the M5Stack NAS Monitor device via serial port.

## Features

- **Temperature Monitoring**: Collects CPU and HDD temperatures using `sensors` and `smartctl`
- **Network Information**: Gathers MAC addresses and IP addresses (IPv4/IPv6)
- **ZFS Storage Monitoring**: Monitors ZFS pool status, capacity, and usage
- **Serial Communication**: Sends data to M5Stack device every 30 seconds
- **Daemon Operation**: Runs as a system service with proper logging
- **Error Handling**: Robust error recovery and reconnection logic

## Requirements

### System Dependencies
```bash
# Install required system tools
sudo apt update
sudo apt install -y lm-sensors smartmontools zfsutils-linux

# Initialize sensors (run once)
sudo sensors-detect --auto
```

### Python Dependencies
- Python 3.8+
- pyserial
- psutil
- netifaces

## Installation

### Quick Install
```bash
# Clone or download the project
cd client-agent

# Install the package
pip install -e .

# Or install from PyPI (when published)
pip install m5stack-nas-monitor
```

### Development Install
```bash
# Install with development dependencies
pip install -e ".[dev]"
```

## Configuration

### 1. Find M5Stack Serial Port
```bash
# List available serial ports
ls /dev/ttyUSB* /dev/ttyACM*

# Test connection (replace with your port)
m5nas-test --port /dev/ttyUSB0
```

### 2. Configure the Service
```bash
# Edit configuration
sudo nano /etc/m5nas-monitor.conf
```

Example configuration:
```ini
[serial]
port = /dev/ttyUSB0
baudrate = 115200
timeout = 5

[monitoring]
update_interval = 30
temperature_sensors = coretemp-isa-0000,acpi-0
hdd_devices = /dev/sda,/dev/sdb,/dev/sdc,/dev/sdd,/dev/sde

[network]
primary_interface = eth0

[zfs]
pools = tank,backup,cache

[logging]
level = INFO
file = /var/log/m5nas-monitor.log
```

## Usage

### Command Line
```bash
# Test connection and data collection
m5nas-test --port /dev/ttyUSB0

# Run daemon in foreground (for testing)
m5nas-monitor --port /dev/ttyUSB0 --foreground

# Run as daemon
m5nas-monitor --port /dev/ttyUSB0 --daemon
```

### System Service

#### Install Service
```bash
# Copy service file
sudo cp systemd/m5nas-monitor.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable m5nas-monitor
sudo systemctl start m5nas-monitor

# Check status
sudo systemctl status m5nas-monitor
```

#### Monitor Service
```bash
# View logs
sudo journalctl -u m5nas-monitor -f

# Restart service
sudo systemctl restart m5nas-monitor

# Stop service
sudo systemctl stop m5nas-monitor
```

## Data Collection

### Temperature Data
- **CPU Temperature**: From `sensors` command (coretemp)
- **HDD Temperatures**: From `smartctl` for up to 5 drives
- **Fallback**: Uses psutil if hardware sensors unavailable

### Network Information
- **MAC Address**: Primary network interface
- **IPv4 Address**: Current assigned IP
- **IPv6 Address**: Current assigned IPv6 (if available)

### ZFS Storage
- **Pool Names**: All configured ZFS pools
- **Capacity**: Total pool size
- **Usage**: Used space percentage
- **Health**: Pool state (ONLINE, DEGRADED, FAULTED, etc.)

## Serial Protocol

The daemon sends data using these commands:

```bash
# Temperature and basic storage
UPDATE:45.2,38.1,42.5,39.8,41.2,43.6,Healthy

# Network information  
NETWORK:aa:bb:cc:dd:ee:ff,192.168.1.100,2001:db8::1

# Storage pools (sent after POOL:RESET)
POOL:RESET
POOL:tank,2TB,65%,ONLINE
POOL:backup,1TB,80%,DEGRADED
```

## Troubleshooting

### Permission Issues
```bash
# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER

# Logout and login again, or use:
newgrp dialout
```

### Serial Port Problems
```bash
# Check if port is available
ls -la /dev/ttyUSB*

# Test with screen
screen /dev/ttyUSB0 115200

# Check for conflicting processes
sudo lsof /dev/ttyUSB0
```

### Missing System Tools
```bash
# Install missing tools
sudo apt install lm-sensors smartmontools zfsutils-linux

# Test sensors
sensors

# Test smartctl
sudo smartctl -A /dev/sda

# Test ZFS
zpool list
```

### Debug Mode
```bash
# Run with debug logging
m5nas-monitor --port /dev/ttyUSB0 --foreground --debug

# Test individual components
python -c "from m5nas_monitor.collectors import TemperatureCollector; print(TemperatureCollector().collect())"
```

## Development

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Type checking
mypy m5nas_monitor/

# Code formatting
black m5nas_monitor/
```

### Project Structure
```
client-agent/
├── m5nas_monitor/          # Main package
│   ├── __init__.py
│   ├── daemon.py           # Main daemon
│   ├── collectors/         # Data collectors
│   ├── serial_client.py    # Serial communication
│   └── config.py           # Configuration
├── config/                 # Configuration files
├── systemd/               # Service files
├── tests/                 # Unit tests
├── setup.py
└── README.md
```

## License

MIT License - see LICENSE file for details.