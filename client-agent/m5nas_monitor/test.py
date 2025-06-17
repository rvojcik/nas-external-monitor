"""
Test utilities for M5Stack NAS Monitor
"""

import argparse
import sys
import logging
from .config import Config
from .daemon import NASMonitorDaemon


def main():
    """Test entry point"""
    parser = argparse.ArgumentParser(description="M5Stack NAS Monitor Test Tool")
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--port', '-p', help='Serial port for M5Stack device')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = Config(args.config)
    
    # Override config with command line arguments
    if args.port:
        config.config.set('serial', 'port', args.port)
    
    # Create and test daemon
    daemon = NASMonitorDaemon(config)
    success = daemon.test_system()
    
    print("\n" + "="*50)
    if success:
        print("✓ All tests passed!")
        print("\nYou can now run the daemon:")
        print(f"  m5nas-monitor --port {config.serial_port} --foreground")
    else:
        print("✗ Some tests failed!")
        print("\nPlease check the error messages above and:")
        print("1. Verify M5Stack device is connected to the correct port")
        print("2. Check that you have permission to access the serial port")
        print("3. Install missing system tools (sensors, smartctl, zfs)")
        print("4. Run with --debug for more detailed output")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())