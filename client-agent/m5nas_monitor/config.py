"""
Configuration management for M5Stack NAS Monitor
"""

import configparser
import os
import logging
from typing import List, Dict, Any
from pathlib import Path


class Config:
    """Configuration manager for the NAS monitor daemon"""
    
    def __init__(self, config_file: str = None):
        self.config = configparser.ConfigParser()
        
        # Default configuration
        self.defaults = {
            'serial': {
                'port': '/dev/ttyUSB0',
                'baudrate': '115200',
                'timeout': '5'
            },
            'monitoring': {
                'update_interval': '30',
                'temperature_sensors': 'coretemp-isa-0000',
                'hdd_devices': '/dev/sda,/dev/sdb,/dev/sdc,/dev/sdd,/dev/sde',
                'max_hdds': '5'
            },
            'network': {
                'primary_interface': 'eth0',
                'fallback_interfaces': 'enp0s3,ens33,wlan0'
            },
            'storage': {
                'enabled': 'true',
                'storage_health_enabled': 'true',
                'storage_types': 'zfs,mdadm',
                'zfs_pools': '',
                'zfs_auto_discover': 'true',
                'mdadm_arrays': '',
                'mdadm_auto_discover': 'true',
                'mdadm_mount_points': '/mnt,/media,/home'
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/m5nas-monitor.log',
                'max_size': '10MB',
                'backup_count': '5'
            }
        }
        
        # Load configuration
        self._load_config(config_file)
        
    def _load_config(self, config_file: str = None):
        """Load configuration from file with fallback to defaults"""
        
        # Set defaults
        for section, options in self.defaults.items():
            self.config.add_section(section)
            for key, value in options.items():
                self.config.set(section, key, value)
        
        # Possible config file locations
        config_paths = [
            config_file,
            '/etc/m5nas-monitor.conf',
            '/usr/local/etc/m5nas-monitor.conf',
            os.path.expanduser('~/.m5nas-monitor.conf'),
            './m5nas-monitor.conf'
        ]
        
        # Try to load config file
        for path in config_paths:
            if path and os.path.exists(path):
                try:
                    self.config.read(path)
                    logging.info(f"Loaded configuration from: {path}")
                    return
                except Exception as e:
                    logging.warning(f"Failed to load config from {path}: {e}")
        
        logging.info("Using default configuration")
    
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """Get configuration value"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return self.config.getint(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get float configuration value"""
        try:
            return self.config.getfloat(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get boolean configuration value"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getlist(self, section: str, key: str, fallback: List[str] = None) -> List[str]:
        """Get list configuration value (comma-separated)"""
        if fallback is None:
            fallback = []
        
        try:
            value = self.config.get(section, key)
            if not value.strip():
                return fallback
            return [item.strip() for item in value.split(',') if item.strip()]
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    @property
    def serial_port(self) -> str:
        return self.get('serial', 'port', '/dev/ttyUSB0')
    
    @property
    def serial_baudrate(self) -> int:
        return self.getint('serial', 'baudrate', 115200)
    
    @property
    def serial_timeout(self) -> float:
        return self.getfloat('serial', 'timeout', 5.0)
    
    @property
    def update_interval(self) -> int:
        return self.getint('monitoring', 'update_interval', 30)
    
    @property
    def temperature_sensors(self) -> List[str]:
        return self.getlist('monitoring', 'temperature_sensors', ['coretemp-isa-0000'])
    
    @property
    def hdd_devices(self) -> List[str]:
        return self.getlist('monitoring', 'hdd_devices', 
                           ['/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/sdd', '/dev/sde'])
    
    @property
    def max_hdds(self) -> int:
        return self.getint('monitoring', 'max_hdds', 5)
    
    @property
    def primary_interface(self) -> str:
        return self.get('network', 'primary_interface', 'eth0')
    
    @property
    def fallback_interfaces(self) -> List[str]:
        return self.getlist('network', 'fallback_interfaces', ['enp0s3', 'ens33', 'wlan0'])
    
    @property
    def storage_enabled(self) -> bool:
        return self.getboolean('storage', 'enabled', True)
    
    @property
    def storage_health_enabled(self) -> bool:
        return self.getboolean('storage', 'storage_health_enabled', True)
    
    @property
    def storage_types(self) -> List[str]:
        return self.getlist('storage', 'storage_types', ['zfs'])
    
    @property
    def zfs_pools(self) -> List[str]:
        return self.getlist('storage', 'zfs_pools', [])
    
    @property
    def zfs_auto_discover(self) -> bool:
        return self.getboolean('storage', 'zfs_auto_discover', True)
    
    @property
    def mdadm_arrays(self) -> List[str]:
        return self.getlist('storage', 'mdadm_arrays', [])
    
    @property
    def mdadm_auto_discover(self) -> bool:
        return self.getboolean('storage', 'mdadm_auto_discover', True)
    
    @property
    def mdadm_mount_points(self) -> List[str]:
        return self.getlist('storage', 'mdadm_mount_points', ['/mnt', '/media', '/home'])
    
    @property
    def log_level(self) -> str:
        return self.get('logging', 'level', 'INFO').upper()
    
    @property
    def log_file(self) -> str:
        return self.get('logging', 'file', '/var/log/m5nas-monitor.log')
    
    def save_sample_config(self, path: str):
        """Save a sample configuration file"""
        sample_config = """# M5Stack NAS Monitor Configuration

[serial]
# Serial port for M5Stack device
port = /dev/ttyUSB0
baudrate = 115200
timeout = 5

[monitoring]
# Update interval in seconds
update_interval = 30

# Temperature sensors (from 'sensors' command)
temperature_sensors = coretemp-isa-0000,acpi-0

# HDD devices for temperature monitoring
hdd_devices = /dev/sda,/dev/sdb,/dev/sdc,/dev/sdd,/dev/sde

# Maximum number of HDDs to monitor
max_hdds = 5

[network]
# Primary network interface
primary_interface = eth0

# Fallback interfaces to try
fallback_interfaces = enp0s3,ens33,wlan0

[storage]
# Enable storage monitoring
enabled = true

# Enable storage health monitoring
storage_health_enabled = true

# Storage types to monitor: zfs, mdadm (comma-separated)
storage_types = zfs,mdadm

# ZFS pools to monitor (empty = auto-discover all pools)
zfs_pools = 

# Auto-discover ZFS pools
zfs_auto_discover = true

# MDADM arrays to monitor (empty = auto-discover, e.g. md0,md1,md127)
mdadm_arrays = 

# Auto-discover MDADM arrays
mdadm_auto_discover = true

# Mount points to search for MDADM array usage
mdadm_mount_points = /mnt,/media,/home

[logging]
# Log level: DEBUG, INFO, WARNING, ERROR
level = INFO

# Log file path
file = /var/log/m5nas-monitor.log

# Log rotation
max_size = 10MB
backup_count = 5
"""
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(sample_config)
            logging.info(f"Sample configuration saved to: {path}")
        except Exception as e:
            logging.error(f"Failed to save sample config: {e}")
            raise