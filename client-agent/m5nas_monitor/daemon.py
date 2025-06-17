"""
Main daemon for M5Stack NAS Monitor
"""

import time
import logging
import signal
import sys
import os
import argparse
from threading import Event
from typing import Dict, Any

from .config import Config
from .serial_client import SerialClient
from .collectors import TemperatureCollector, NetworkCollector, StorageCollector


class NASMonitorDaemon:
    """Main daemon for NAS monitoring"""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = Event()
        self.running.set()
        
        # Initialize logger
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize collectors
        self.temp_collector = TemperatureCollector(
            sensor_names=config.temperature_sensors,
            hdd_devices=config.hdd_devices
        )
        
        self.network_collector = NetworkCollector(
            primary_interface=config.primary_interface,
            fallback_interfaces=config.fallback_interfaces
        )
        
        self.storage_collector = StorageCollector(
            storage_types=config.storage_types,
            zfs_pools=config.zfs_pools,
            zfs_auto_discover=config.zfs_auto_discover,
            mdadm_arrays=config.mdadm_arrays,
            mdadm_auto_discover=config.mdadm_auto_discover,
            mdadm_mount_points=config.mdadm_mount_points,
            enabled=config.storage_enabled,
            health_enabled=config.storage_health_enabled
        )
        
        # Initialize serial client
        self.serial_client = SerialClient(
            port=config.serial_port,
            baudrate=config.serial_baudrate,
            timeout=config.serial_timeout
        )
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("NAS Monitor Daemon initialized")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.log_level, logging.INFO)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Add file handler if log file specified
        if self.config.log_file:
            try:
                os.makedirs(os.path.dirname(self.config.log_file), exist_ok=True)
                file_handler = logging.FileHandler(self.config.log_file)
                file_handler.setFormatter(logging.Formatter(log_format))
                logging.getLogger().addHandler(file_handler)
            except Exception as e:
                logging.warning(f"Failed to setup file logging: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running.clear()
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all monitoring data"""
        data = {}
        
        try:
            # Collect temperature data
            self.logger.debug("Collecting temperature data...")
            temperatures = self.temp_collector.collect()
            storage_state = self.temp_collector.get_storage_health()
            
            data['temperatures'] = temperatures
            data['storage_state'] = storage_state
            
            # Collect network data
            self.logger.debug("Collecting network data...")
            network = self.network_collector.collect()
            data['network'] = network
            
            # Collect storage data (ZFS, MDADM, etc.)
            self.logger.debug("Collecting storage data...")
            storage_volumes = self.storage_collector.collect()
            data['pools'] = storage_volumes
            
            # Override storage state with storage health if available
            if self.storage_collector.enabled and self.storage_collector.health_enabled:
                storage_state = self.storage_collector.get_overall_storage_state()
                if storage_state != "Unknown":
                    data['storage_state'] = storage_state
            
            self.logger.debug(f"Data collection complete: {len(temperatures)} temps, "
                            f"{len(storage_volumes)} storage volumes, network: {bool(network['mac'])}")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error collecting data: {e}")
            return {}
    
    def send_data_to_device(self, data: Dict[str, Any]) -> bool:
        """Send collected data to M5Stack device"""
        try:
            success = self.serial_client.send_complete_update(data)
            if success:
                self.logger.info("Data sent to M5Stack device successfully")
            else:
                self.logger.warning("Failed to send data to M5Stack device")
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending data to device: {e}")
            return False
    
    def run_once(self) -> bool:
        """Run one monitoring cycle"""
        try:
            # Collect data
            data = self.collect_all_data()
            if not data:
                self.logger.warning("No data collected")
                return False
            
            # Send to device
            return self.send_data_to_device(data)
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            return False
    
    def run(self):
        """Main daemon loop"""
        self.logger.info("Starting NAS Monitor Daemon")
        self.logger.info(f"Update interval: {self.config.update_interval} seconds")
        self.logger.info(f"Serial port: {self.config.serial_port}")
        
        # Test initial connection
        if not self.serial_client.test_connection():
            self.logger.error("Failed to establish initial connection to M5Stack device")
            self.logger.error("Please check serial port and device connection")
            return False
        
        self.logger.info("M5Stack device connection verified")
        
        # Main monitoring loop
        cycle_count = 0
        last_update_time = 0
        
        while self.running.is_set():
            try:
                current_time = time.time()
                
                # Check if enough time has passed since last update
                time_since_last = current_time - last_update_time
                if time_since_last < self.config.update_interval:
                    sleep_time = self.config.update_interval - time_since_last
                    self.logger.debug(f"Waiting {sleep_time:.1f}s before next update")
                    self.running.wait(timeout=sleep_time)
                    continue
                
                cycle_count += 1
                self.logger.debug(f"Starting monitoring cycle {cycle_count} (interval: {self.config.update_interval}s)")
                
                start_time = time.time()
                success = self.run_once()
                last_update_time = start_time
                
                elapsed = time.time() - start_time
                self.logger.info(f"Cycle {cycle_count} completed in {elapsed:.2f}s, success: {success}")
                
                # Brief pause to prevent tight loop
                self.running.wait(timeout=0.1)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                # Sleep a bit before retrying
                self.running.wait(timeout=5)
        
        self.logger.info("Shutting down NAS Monitor Daemon")
        self.serial_client.disconnect()
        return True
    
    def test_system(self) -> bool:
        """Test system components and data collection"""
        self.logger.info("Testing system components...")
        
        success = True
        
        # Test serial connection
        self.logger.info("Testing serial connection...")
        if self.serial_client.test_connection():
            self.logger.info("✓ Serial connection: OK")
        else:
            self.logger.error("✗ Serial connection: FAILED")
            success = False
        
        # Test temperature collection
        self.logger.info("Testing temperature collection...")
        try:
            temps = self.temp_collector.collect()
            if any(temp > 0 for temp in temps.values()):
                self.logger.info(f"✓ Temperature collection: OK - {temps}")
            else:
                self.logger.warning(f"⚠ Temperature collection: No sensors found - {temps}")
        except Exception as e:
            self.logger.error(f"✗ Temperature collection: FAILED - {e}")
            success = False
        
        # Test network collection
        self.logger.info("Testing network collection...")
        try:
            network = self.network_collector.collect()
            if network['mac']:
                self.logger.info(f"✓ Network collection: OK - {network}")
            else:
                self.logger.warning(f"⚠ Network collection: No active interface - {network}")
        except Exception as e:
            self.logger.error(f"✗ Network collection: FAILED - {e}")
            success = False
        
        # Test storage collection
        self.logger.info("Testing storage collection...")
        try:
            if self.storage_collector.enabled:
                storage_volumes = self.storage_collector.collect()
                if storage_volumes:
                    self.logger.info(f"✓ Storage collection: OK - {len(storage_volumes)} volumes found")
                    for volume in storage_volumes:
                        vol_type = volume.get('type', 'Unknown')
                        self.logger.info(f"  {vol_type}: {volume['name']} - {volume['capacity']} ({volume['usage']}) - {volume['state']}")
                else:
                    self.logger.warning("⚠ Storage collection: No storage volumes found")
                
                # Test storage health
                health = self.storage_collector.get_overall_storage_state()
                self.logger.info(f"  Overall storage health: {health}")
                
                # Test individual storage types
                if 'zfs' in self.storage_collector.storage_types and self.storage_collector.is_zfs_available():
                    self.logger.info("  ✓ ZFS support: Available")
                elif 'zfs' in self.storage_collector.storage_types:
                    self.logger.warning("  ⚠ ZFS support: Not available")
                
                if 'mdadm' in self.storage_collector.storage_types and hasattr(self.storage_collector, 'mdadm_collector'):
                    if self.storage_collector.mdadm_collector.is_mdadm_available():
                        self.logger.info("  ✓ MDADM support: Available")
                    else:
                        self.logger.warning("  ⚠ MDADM support: Not available")
            else:
                self.logger.info("⚠ Storage collection: Disabled in configuration")
        except Exception as e:
            self.logger.error(f"✗ Storage collection: FAILED - {e}")
        
        return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="M5Stack NAS Monitor Daemon")
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--port', '-p', help='Serial port for M5Stack device')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run as daemon')
    parser.add_argument('--foreground', '-f', action='store_true', help='Run in foreground')
    parser.add_argument('--test', '-t', action='store_true', help='Test system and exit')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--generate-config', help='Generate sample config file')
    
    args = parser.parse_args()
    
    # Generate sample config if requested
    if args.generate_config:
        config = Config()
        config.save_sample_config(args.generate_config)
        print(f"Sample configuration saved to: {args.generate_config}")
        return 0
    
    # Load configuration
    config = Config(args.config)
    
    # Override config with command line arguments
    if args.port:
        config.config.set('serial', 'port', args.port)
    
    if args.debug:
        config.config.set('logging', 'level', 'DEBUG')
    
    # Create daemon
    daemon = NASMonitorDaemon(config)
    
    # Test mode
    if args.test:
        success = daemon.test_system()
        return 0 if success else 1
    
    # Run daemon
    if args.daemon and not args.foreground:
        # TODO: Implement proper daemonization
        print("Daemon mode not yet implemented. Use --foreground for now.")
        return 1
    
    try:
        success = daemon.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())