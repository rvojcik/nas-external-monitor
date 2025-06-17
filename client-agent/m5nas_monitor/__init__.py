"""
M5Stack NAS Monitor Client Agent

A Python daemon that collects system information and sends it to
M5Stack NAS Monitor device via serial port.
"""

__version__ = "1.0.0"
__author__ = "M5Stack NAS Monitor Team"
__email__ = "admin@example.com"

from .daemon import NASMonitorDaemon
from .serial_client import SerialClient
from .config import Config

__all__ = ["NASMonitorDaemon", "SerialClient", "Config"]