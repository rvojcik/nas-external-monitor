"""
Serial communication client for M5Stack NAS Monitor
"""

import serial
import time
import logging
from typing import Optional, Dict, Any
from threading import Lock


class SerialClient:
    """Serial communication client for M5Stack device"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection: Optional[serial.Serial] = None
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """Establish serial connection"""
        try:
            with self.lock:
                if self.connection and self.connection.is_open:
                    return True
                
                self.logger.info(f"Connecting to M5Stack on {self.port} at {self.baudrate} baud")
                
                self.connection = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout
                )
                
                # Wait for M5Stack to initialize
                time.sleep(2)
                
                # Clear any pending data
                self.connection.reset_input_buffer()
                self.connection.reset_output_buffer()
                
                self.logger.info("Serial connection established")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to connect to serial port: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        try:
            with self.lock:
                if self.connection and self.connection.is_open:
                    self.connection.close()
                    self.logger.info("Serial connection closed")
        except Exception as e:
            self.logger.error(f"Error closing serial connection: {e}")
    
    def is_connected(self) -> bool:
        """Check if serial connection is active"""
        with self.lock:
            return self.connection is not None and self.connection.is_open
    
    def send_command(self, command: str) -> bool:
        """Send command to M5Stack device"""
        if not self.is_connected():
            if not self.connect():
                return False
        
        try:
            with self.lock:
                # Ensure command ends with newline
                if not command.endswith('\n'):
                    command += '\n'
                
                self.logger.debug(f"Sending command: {command.strip()}")
                self.connection.write(command.encode('utf-8'))
                self.connection.flush()
                
                # Brief delay to ensure command is processed
                time.sleep(0.1)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send command '{command.strip()}': {e}")
            # Try to reconnect on next attempt
            self.disconnect()
            return False
    
    def send_temperature_update(self, temps: Dict[str, float], storage_state: str) -> bool:
        """Send temperature update command"""
        try:
            # Format: UPDATE:sys_temp,hdd1,hdd2,hdd3,hdd4,hdd5,storage_state
            temp_values = [
                f"{temps.get('system', 0.0):.1f}",
                f"{temps.get('hdd1', 0.0):.1f}",
                f"{temps.get('hdd2', 0.0):.1f}",
                f"{temps.get('hdd3', 0.0):.1f}",
                f"{temps.get('hdd4', 0.0):.1f}",
                f"{temps.get('hdd5', 0.0):.1f}",
                storage_state
            ]
            
            command = f"UPDATE:{','.join(temp_values)}"
            return self.send_command(command)
            
        except Exception as e:
            self.logger.error(f"Failed to format temperature update: {e}")
            return False
    
    def send_network_update(self, mac: str, ipv4: str, ipv6: str) -> bool:
        """Send network information update"""
        try:
            # Format: NETWORK:mac_address,ipv4_address,ipv6_address
            command = f"NETWORK:{mac},{ipv4},{ipv6}"
            return self.send_command(command)
            
        except Exception as e:
            self.logger.error(f"Failed to format network update: {e}")
            return False
    
    def send_storage_reset(self) -> bool:
        """Send storage pool reset command"""
        return self.send_command("POOL:RESET")
    
    def send_storage_pool(self, name: str, capacity: str, usage: str, state: str) -> bool:
        """Send storage pool information"""
        try:
            # Format: POOL:name,capacity,usage,state
            command = f"POOL:{name},{capacity},{usage},{state}"
            return self.send_command(command)
            
        except Exception as e:
            self.logger.error(f"Failed to format pool update: {e}")
            return False
    
    def send_complete_update(self, data: Dict[str, Any]) -> bool:
        """Send complete data update to M5Stack"""
        success = True
        
        try:
            # 1. Send temperature update
            if 'temperatures' in data and 'storage_state' in data:
                if not self.send_temperature_update(data['temperatures'], data['storage_state']):
                    success = False
                    
            # Small delay between commands
            time.sleep(0.2)
            
            # 2. Send network update
            if 'network' in data:
                net = data['network']
                if not self.send_network_update(
                    net.get('mac', ''),
                    net.get('ipv4', ''),
                    net.get('ipv6', '')
                ):
                    success = False
                    
            # Small delay between commands
            time.sleep(0.2)
            
            # 3. Send storage pools
            if 'pools' in data and data['pools']:
                # Reset pools first
                if not self.send_storage_reset():
                    success = False
                    
                time.sleep(0.1)
                
                # Send each pool
                for pool in data['pools']:
                    if not self.send_storage_pool(
                        pool.get('name', ''),
                        pool.get('capacity', ''),
                        pool.get('usage', ''),
                        pool.get('state', '')
                    ):
                        success = False
                    time.sleep(0.1)
            
            if success:
                self.logger.info("Complete data update sent successfully")
            else:
                self.logger.warning("Some commands failed during update")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send complete update: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test the serial connection"""
        try:
            if not self.connect():
                return False
                
            # Send a simple test command
            test_data = {
                'temperatures': {
                    'system': 25.0,
                    'hdd1': 30.0,
                    'hdd2': 28.0,
                    'hdd3': 29.0,
                    'hdd4': 27.0,
                    'hdd5': 26.0
                },
                'storage_state': 'Healthy',
                'network': {
                    'mac': 'TEST:MAC:ADDR',
                    'ipv4': '192.168.1.100',
                    'ipv6': '2001:db8::1'
                },
                'pools': [
                    {
                        'name': 'test-pool',
                        'capacity': '1TB',
                        'usage': '50%',
                        'state': 'ONLINE'
                    }
                ]
            }
            
            return self.send_complete_update(test_data)
            
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()