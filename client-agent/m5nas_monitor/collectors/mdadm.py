"""
MDADM RAID storage information collector
"""

import subprocess
import re
import logging
import shutil
import os
from typing import List, Dict, Optional
from pathlib import Path


class MdadmCollector:
    """Collects MDADM RAID array information"""
    
    def __init__(self, arrays: List[str] = None, auto_discover: bool = True, mount_points: List[str] = None):
        self.arrays = arrays or []
        self.auto_discover = auto_discover
        self.mount_points = mount_points or ['/mnt', '/media', '/home']
        self.logger = logging.getLogger(__name__)
    
    def collect(self) -> List[Dict[str, str]]:
        """Collect MDADM array information"""
        try:
            if not self.is_mdadm_available():
                self.logger.warning("MDADM not available on this system")
                return []
            
            if self.auto_discover or not self.arrays:
                arrays = self._discover_arrays()
            else:
                arrays = self.arrays
            
            array_info = []
            for array_name in arrays:
                info = self._get_array_info(array_name)
                if info:
                    array_info.append(info)
            
            self.logger.debug(f"Collected {len(array_info)} MDADM arrays")
            return array_info
            
        except Exception as e:
            self.logger.error(f"Failed to collect MDADM information: {e}")
            return []
    
    def _discover_arrays(self) -> List[str]:
        """Discover available MDADM arrays from /proc/mdstat"""
        try:
            if not os.path.exists('/proc/mdstat'):
                self.logger.warning("/proc/mdstat not found")
                return []
            
            with open('/proc/mdstat', 'r') as f:
                content = f.read()
            
            arrays = []
            # Look for lines like "md0 : active raid1 sdb1[1] sda1[0]"
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('Personalities') and not line.startswith('unused'):
                    # Check if line starts with md followed by number
                    match = re.match(r'^(md\d+)\s*:', line)
                    if match:
                        array_name = match.group(1)
                        arrays.append(array_name)
            
            self.logger.debug(f"Discovered MDADM arrays from /proc/mdstat: {arrays}")
            return arrays
            
        except Exception as e:
            self.logger.error(f"Error discovering MDADM arrays: {e}")
            return []
    
    def _get_array_info(self, array_name: str) -> Optional[Dict[str, str]]:
        """Get detailed information for a specific MDADM array"""
        try:
            # Get array state from /proc/mdstat
            state_info = self._get_array_state(array_name)
            if not state_info:
                return None
            
            # Get capacity and usage information
            capacity_info = self._get_array_capacity(array_name)
            
            # Combine information
            array_info = {
                'name': array_name,
                'type': 'MDADM',
                'raid_level': state_info.get('raid_level', 'unknown'),
                'state': self._map_state(state_info.get('state', 'unknown')),
                'capacity': capacity_info.get('capacity', 'unknown'),
                'usage': capacity_info.get('usage', '0%'),
                'raw_state': state_info.get('state', 'unknown'),
                'devices': state_info.get('devices', ''),
                'mount_point': capacity_info.get('mount_point', '')
            }
            
            self.logger.debug(f"Array {array_name}: {array_info}")
            return array_info
            
        except Exception as e:
            self.logger.error(f"Error getting array info for {array_name}: {e}")
            return None
    
    def _get_array_state(self, array_name: str) -> Optional[Dict[str, str]]:
        """Get array state from /proc/mdstat"""
        try:
            if not os.path.exists('/proc/mdstat'):
                return None
            
            with open('/proc/mdstat', 'r') as f:
                content = f.read()
            
            # Find the array section
            lines = content.split('\n')
            array_section = []
            in_array = False
            
            for line in lines:
                if line.startswith(array_name + ' :'):
                    in_array = True
                    array_section.append(line)
                elif in_array:
                    if line.strip() == '' or re.match(r'^md\d+\s*:', line):
                        break
                    array_section.append(line)
            
            if not array_section:
                return None
            
            # Parse array information
            info = {}
            
            # First line: "md0 : active raid1 sdb1[1] sda1[0]"
            first_line = array_section[0]
            parts = first_line.split()
            
            if len(parts) >= 3:
                info['state'] = parts[2]  # active/inactive
                if len(parts) >= 4:
                    info['raid_level'] = parts[3]  # raid0, raid1, etc.
                
                # Extract device list
                devices = []
                for part in parts[4:]:
                    # Remove [n] suffix and add to devices
                    device = re.sub(r'\[\d+\]', '', part)
                    if device:
                        devices.append(device)
                info['devices'] = ','.join(devices)
            
            # Look for additional state information in subsequent lines
            for line in array_section[1:]:
                line = line.strip()
                if 'recovery' in line.lower():
                    info['state'] = 'recovering'
                elif 'resync' in line.lower():
                    info['state'] = 'resyncing'
                elif 'degraded' in line.lower():
                    info['state'] = 'degraded'
                elif 'failed' in line.lower():
                    info['state'] = 'failed'
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error reading /proc/mdstat for {array_name}: {e}")
            return None
    
    def _get_array_capacity(self, array_name: str) -> Dict[str, str]:
        """Get array capacity and usage information"""
        info = {
            'capacity': 'unknown',
            'usage': '0%',
            'mount_point': ''
        }
        
        try:
            device_path = f'/dev/{array_name}'
            
            # Try to get filesystem information if mounted
            mount_info = self._get_mount_info(device_path)
            if mount_info:
                info.update(mount_info)
                return info
            
            # Try to get raw device size
            try:
                result = subprocess.run([
                    'lsblk', '-b', '-n', '-o', 'SIZE', device_path
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    size_bytes = int(result.stdout.strip())
                    info['capacity'] = self._format_size(size_bytes)
            except Exception:
                pass
            
            # Try blockdev as fallback
            if info['capacity'] == 'unknown':
                try:
                    result = subprocess.run([
                        'blockdev', '--getsize64', device_path
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        size_bytes = int(result.stdout.strip())
                        info['capacity'] = self._format_size(size_bytes)
                except Exception:
                    pass
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting capacity for {array_name}: {e}")
            return info
    
    def _get_mount_info(self, device_path: str) -> Optional[Dict[str, str]]:
        """Get mount information and usage for a device"""
        try:
            # Check if device is mounted
            result = subprocess.run([
                'findmnt', '-n', '-o', 'TARGET', device_path
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return None
            
            mount_point = result.stdout.strip()
            if not mount_point:
                return None
            
            # Get filesystem usage
            usage_info = shutil.disk_usage(mount_point)
            total = usage_info.total
            used = usage_info.used
            
            usage_percent = int((used / total) * 100) if total > 0 else 0
            
            return {
                'capacity': self._format_size(total),
                'usage': f'{usage_percent}%',
                'mount_point': mount_point,
                'used': self._format_size(used),
                'free': self._format_size(total - used)
            }
            
        except Exception as e:
            self.logger.debug(f"Could not get mount info for {device_path}: {e}")
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human readable format"""
        if size_bytes == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)}{units[unit_index]}"
        else:
            return f"{size:.1f}{units[unit_index]}"
    
    def _map_state(self, mdadm_state: str) -> str:
        """Map MDADM states to display-friendly states"""
        state_map = {
            'active': 'Healthy',
            'clean': 'Healthy',
            'degraded': 'Degraded',
            'recovering': 'Recovering',
            'resyncing': 'Resyncing',
            'failed': 'Failed',
            'inactive': 'Offline',
            'spare': 'Spare'
        }
        
        return state_map.get(mdadm_state.lower(), mdadm_state.title())
    
    def get_overall_health(self) -> str:
        """Get overall MDADM health state"""
        try:
            arrays = self.collect()
            
            if not arrays:
                return "Unknown"
            
            # Check if any array has problems
            for array in arrays:
                raw_state = array.get('raw_state', '').lower()
                if raw_state in ['degraded', 'failed', 'inactive', 'recovering', 'resyncing']:
                    return "Problem"
            
            return "Healthy"
            
        except Exception as e:
            self.logger.error(f"Error getting overall MDADM health: {e}")
            return "Unknown"
    
    def is_mdadm_available(self) -> bool:
        """Check if MDADM is available on the system"""
        try:
            # Check if /proc/mdstat exists
            if not os.path.exists('/proc/mdstat'):
                return False
            
            # Check if mdadm command is available
            result = subprocess.run([
                'which', 'mdadm'
            ], capture_output=True, text=True, timeout=5)
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def get_array_details(self, array_name: str) -> Optional[Dict[str, str]]:
        """Get detailed status for a specific array"""
        try:
            result = subprocess.run([
                'mdadm', '--detail', f'/dev/{array_name}'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                return {
                    'name': array_name,
                    'details': result.stdout
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting array details for {array_name}: {e}")
            return None