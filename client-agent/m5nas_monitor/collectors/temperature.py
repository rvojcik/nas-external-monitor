"""
Temperature data collector using sensors and smartctl
"""

import subprocess
import re
import logging
import psutil
from typing import Dict, List, Optional
from pathlib import Path


class TemperatureCollector:
    """Collects temperature data from CPU and HDD sensors"""
    
    def __init__(self, sensor_names: List[str] = None, hdd_devices: List[str] = None):
        self.sensor_names = sensor_names or ['coretemp-isa-0000']
        self.hdd_devices = hdd_devices or ['/dev/sda', '/dev/sdb', '/dev/sdc', '/dev/sdd', '/dev/sde']
        self.logger = logging.getLogger(__name__)
        
    def collect(self) -> Dict[str, float]:
        """Collect all temperature data"""
        temps = {}
        
        # Get CPU temperature
        temps['system'] = self._get_cpu_temperature()
        
        # Get HDD temperatures
        hdd_temps = self._get_hdd_temperatures()
        for i, temp in enumerate(hdd_temps[:5], 1):
            temps[f'hdd{i}'] = temp
        
        # Ensure we have all 5 HDD entries
        for i in range(1, 6):
            if f'hdd{i}' not in temps:
                temps[f'hdd{i}'] = 0.0
        
        self.logger.debug(f"Collected temperatures: {temps}")
        return temps
    
    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature from sensors"""
        try:
            # Try hardware sensors first
            temp = self._get_sensors_temperature()
            if temp > 0:
                return temp
                
            # Fallback to psutil
            temp = self._get_psutil_temperature()
            if temp > 0:
                return temp
                
            # Fallback to thermal zone
            temp = self._get_thermal_zone_temperature()
            if temp > 0:
                return temp
                
            self.logger.warning("No CPU temperature source available")
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to get CPU temperature: {e}")
            return 0.0
    
    def _get_sensors_temperature(self) -> float:
        """Get temperature from sensors command"""
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return 0.0
                
            output = result.stdout
            
            # Look for temperature from specified sensors
            for sensor_name in self.sensor_names:
                sensor_section = False
                for line in output.split('\n'):
                    line = line.strip()
                    
                    # Check if we're in the right sensor section
                    if sensor_name in line:
                        sensor_section = True
                        continue
                        
                    # Look for temperature in the sensor section
                    if sensor_section and ('Core' in line or 'temp' in line.lower()):
                        # Extract temperature (format: "Core 0: +45.0°C")
                        match = re.search(r'[+-]?(\d+\.?\d*)\s*°?C', line)
                        if match:
                            temp = float(match.group(1))
                            self.logger.debug(f"Found CPU temperature: {temp}°C from {sensor_name}")
                            return temp
                    
                    # Reset if we hit another sensor
                    elif line.endswith(':') and sensor_section:
                        sensor_section = False
            
            # Try generic temperature search
            for line in output.split('\n'):
                if 'Core' in line and '°C' in line:
                    match = re.search(r'[+-]?(\d+\.?\d*)\s*°?C', line)
                    if match:
                        temp = float(match.group(1))
                        self.logger.debug(f"Found generic CPU temperature: {temp}°C")
                        return temp
            
            return 0.0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return 0.0
        except Exception as e:
            self.logger.warning(f"Error parsing sensors output: {e}")
            return 0.0
    
    def _get_psutil_temperature(self) -> float:
        """Get temperature from psutil"""
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return 0.0
                
            # Look for coretemp first
            if 'coretemp' in temps:
                for sensor in temps['coretemp']:
                    if 'core' in sensor.label.lower() or 'package' in sensor.label.lower():
                        return sensor.current
                return temps['coretemp'][0].current
            
            # Try other temperature sensors
            for sensor_name, sensors in temps.items():
                if sensors and 'cpu' in sensor_name.lower():
                    return sensors[0].current
            
            # Use first available sensor
            for sensor_name, sensors in temps.items():
                if sensors:
                    return sensors[0].current
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Error getting psutil temperature: {e}")
            return 0.0
    
    def _get_thermal_zone_temperature(self) -> float:
        """Get temperature from thermal zone files"""
        try:
            thermal_zones = list(Path('/sys/class/thermal').glob('thermal_zone*'))
            
            for zone_path in thermal_zones:
                try:
                    # Check if this is a CPU thermal zone
                    type_file = zone_path / 'type'
                    if type_file.exists():
                        zone_type = type_file.read_text().strip().lower()
                        if 'cpu' in zone_type or 'x86_pkg_temp' in zone_type:
                            temp_file = zone_path / 'temp'
                            if temp_file.exists():
                                temp_millidegrees = int(temp_file.read_text().strip())
                                temp_celsius = temp_millidegrees / 1000.0
                                if 0 < temp_celsius < 150:  # Sanity check
                                    return temp_celsius
                except Exception:
                    continue
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Error reading thermal zone: {e}")
            return 0.0
    
    def _get_hdd_temperatures(self) -> List[float]:
        """Get HDD temperatures using smartctl"""
        temperatures = []
        
        for device in self.hdd_devices:
            temp = self._get_single_hdd_temperature(device)
            if temp > 0:
                temperatures.append(temp)
            else:
                # Still add 0 to maintain device order
                temperatures.append(0.0)
        
        return temperatures
    
    def _get_single_hdd_temperature(self, device: str) -> float:
        """Get temperature for a single HDD"""
        try:
            # Check if device exists
            if not Path(device).exists():
                return 0.0
            
            # Run smartctl to get temperature
            result = subprocess.run([
                'sudo', 'smartctl', '-A', device
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                # Try without sudo
                result = subprocess.run([
                    'smartctl', '-A', device
                ], capture_output=True, text=True, timeout=15)
                
                if result.returncode != 0:
                    return 0.0
            
            output = result.stdout
            
            # Look for temperature attributes
            temp_patterns = [
                r'194\s+Temperature_Celsius\s+[^0-9]*(\d+)',  # Attribute 194
                r'190\s+Airflow_Temperature_Cel\s+[^0-9]*(\d+)',  # Attribute 190
                r'Temperature:\s+(\d+)\s+Celsius',  # Direct temperature
                r'Current Drive Temperature:\s+(\d+)\s+C',  # NVMe drives
            ]
            
            for pattern in temp_patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    temp = float(match.group(1))
                    if 0 < temp < 100:  # Sanity check
                        self.logger.debug(f"HDD {device} temperature: {temp}°C")
                        return temp
            
            return 0.0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return 0.0
        except Exception as e:
            self.logger.warning(f"Error getting temperature for {device}: {e}")
            return 0.0
    
    def get_storage_health(self) -> str:
        """Get overall storage health status"""
        try:
            # Check if any drive has SMART errors
            for device in self.hdd_devices:
                if not Path(device).exists():
                    continue
                    
                try:
                    result = subprocess.run([
                        'sudo', 'smartctl', '-H', device
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        output = result.stdout.lower()
                        if 'failed' in output or 'error' in output:
                            self.logger.warning(f"SMART health check failed for {device}")
                            return "Problem"
                            
                except Exception:
                    continue
            
            return "Healthy"
            
        except Exception as e:
            self.logger.error(f"Error checking storage health: {e}")
            return "Unknown"