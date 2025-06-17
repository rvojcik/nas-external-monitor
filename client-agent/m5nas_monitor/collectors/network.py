"""
Network information collector
"""

import subprocess
import logging
import netifaces
import socket
from typing import Dict, List, Optional


class NetworkCollector:
    """Collects network interface information"""
    
    def __init__(self, primary_interface: str = 'eth0', fallback_interfaces: List[str] = None):
        self.primary_interface = primary_interface
        self.fallback_interfaces = fallback_interfaces or ['enp0s3', 'ens33', 'wlan0']
        self.logger = logging.getLogger(__name__)
    
    def collect(self) -> Dict[str, str]:
        """Collect network information"""
        try:
            interface = self._get_active_interface()
            if not interface:
                self.logger.warning("No active network interface found")
                return {
                    'mac': '',
                    'ipv4': '',
                    'ipv6': ''
                }
            
            mac = self._get_mac_address(interface)
            ipv4 = self._get_ipv4_address(interface)
            ipv6 = self._get_ipv6_address(interface)
            
            self.logger.debug(f"Network info - Interface: {interface}, MAC: {mac}, IPv4: {ipv4}, IPv6: {ipv6}")
            
            return {
                'mac': mac,
                'ipv4': ipv4,
                'ipv6': ipv6
            }
            
        except Exception as e:
            self.logger.error(f"Failed to collect network information: {e}")
            return {
                'mac': '',
                'ipv4': '',
                'ipv6': ''
            }
    
    def _get_active_interface(self) -> Optional[str]:
        """Find the active network interface"""
        try:
            # Try primary interface first
            if self._is_interface_active(self.primary_interface):
                return self.primary_interface
            
            # Try fallback interfaces
            for interface in self.fallback_interfaces:
                if self._is_interface_active(interface):
                    return interface
            
            # Get all interfaces and find first active one
            interfaces = netifaces.interfaces()
            for interface in interfaces:
                if interface != 'lo' and self._is_interface_active(interface):
                    return interface
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding active interface: {e}")
            return None
    
    def _is_interface_active(self, interface: str) -> bool:
        """Check if interface is active and has an IP address"""
        try:
            if interface not in netifaces.interfaces():
                return False
            
            addrs = netifaces.ifaddresses(interface)
            
            # Check if interface has IPv4 address
            if netifaces.AF_INET in addrs:
                ipv4_addrs = addrs[netifaces.AF_INET]
                for addr in ipv4_addrs:
                    if addr.get('addr') and addr['addr'] != '127.0.0.1':
                        return True
            
            return False
            
        except Exception:
            return False
    
    def _get_mac_address(self, interface: str) -> str:
        """Get MAC address for interface"""
        try:
            addrs = netifaces.ifaddresses(interface)
            
            if netifaces.AF_LINK in addrs:
                link_addrs = addrs[netifaces.AF_LINK]
                for addr in link_addrs:
                    mac = addr.get('addr', '')
                    if mac and ':' in mac:
                        return mac.upper()
            
            # Fallback: try reading from sys filesystem
            try:
                with open(f'/sys/class/net/{interface}/address', 'r') as f:
                    mac = f.read().strip()
                    return mac.upper()
            except Exception:
                pass
            
            return ''
            
        except Exception as e:
            self.logger.warning(f"Error getting MAC address for {interface}: {e}")
            return ''
    
    def _get_ipv4_address(self, interface: str) -> str:
        """Get IPv4 address for interface"""
        try:
            addrs = netifaces.ifaddresses(interface)
            
            if netifaces.AF_INET in addrs:
                ipv4_addrs = addrs[netifaces.AF_INET]
                for addr in ipv4_addrs:
                    ip = addr.get('addr', '')
                    if ip and ip != '127.0.0.1':
                        return ip
            
            return ''
            
        except Exception as e:
            self.logger.warning(f"Error getting IPv4 address for {interface}: {e}")
            return ''
    
    def _get_ipv6_address(self, interface: str) -> str:
        """Get IPv6 address for interface"""
        try:
            addrs = netifaces.ifaddresses(interface)
            
            if netifaces.AF_INET6 in addrs:
                ipv6_addrs = addrs[netifaces.AF_INET6]
                for addr in ipv6_addrs:
                    ip = addr.get('addr', '')
                    if ip and not ip.startswith('::1') and not ip.startswith('fe80'):
                        # Remove interface suffix if present (e.g., %eth0)
                        if '%' in ip:
                            ip = ip.split('%')[0]
                        return ip
            
            return ''
            
        except Exception as e:
            self.logger.warning(f"Error getting IPv6 address for {interface}: {e}")
            return ''
    
    def get_default_gateway(self) -> str:
        """Get default gateway IP"""
        try:
            gateways = netifaces.gateways()
            default = gateways.get('default')
            if default and netifaces.AF_INET in default:
                return default[netifaces.AF_INET][0]
            return ''
        except Exception as e:
            self.logger.warning(f"Error getting default gateway: {e}")
            return ''
    
    def test_connectivity(self, host: str = '8.8.8.8', port: int = 53, timeout: float = 3.0) -> bool:
        """Test network connectivity"""
        try:
            socket.setdefaulttimeout(timeout)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False