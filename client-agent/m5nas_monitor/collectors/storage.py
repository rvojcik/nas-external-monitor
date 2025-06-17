"""
Multi-type storage information collector (ZFS + MDADM)
"""

import subprocess
import re
import logging
from typing import List, Dict, Optional
from .mdadm import MdadmCollector


class StorageCollector:
    """Collects storage information from multiple sources (ZFS, MDADM)"""
    
    def __init__(self, 
                 storage_types: List[str] = None,
                 zfs_pools: List[str] = None, 
                 zfs_auto_discover: bool = True,
                 mdadm_arrays: List[str] = None,
                 mdadm_auto_discover: bool = True,
                 mdadm_mount_points: List[str] = None,
                 enabled: bool = True,
                 health_enabled: bool = True):
        self.storage_types = storage_types or ['zfs']
        self.zfs_pools = zfs_pools or []
        self.zfs_auto_discover = zfs_auto_discover
        self.mdadm_arrays = mdadm_arrays or []
        self.mdadm_auto_discover = mdadm_auto_discover
        self.mdadm_mount_points = mdadm_mount_points or ['/mnt', '/media', '/home']
        self.enabled = enabled
        self.health_enabled = health_enabled
        self.logger = logging.getLogger(__name__)
        
        # Initialize MDADM collector if needed
        if 'mdadm' in self.storage_types:
            self.mdadm_collector = MdadmCollector(
                arrays=self.mdadm_arrays,
                auto_discover=self.mdadm_auto_discover,
                mount_points=self.mdadm_mount_points
            )
    
    def collect(self) -> List[Dict[str, str]]:
        """Collect storage information from all enabled sources"""
        if not self.enabled:
            self.logger.debug("Storage monitoring disabled")
            return []
        
        try:
            all_storage = []
            
            # Collect ZFS pools
            if 'zfs' in self.storage_types:
                zfs_storage = self._collect_zfs()
                all_storage.extend(zfs_storage)
            
            # Collect MDADM arrays
            if 'mdadm' in self.storage_types:
                mdadm_storage = self._collect_mdadm()
                all_storage.extend(mdadm_storage)
            
            self.logger.debug(f"Collected {len(all_storage)} storage volumes total")
            return all_storage
            
        except Exception as e:
            self.logger.error(f"Failed to collect storage information: {e}")
            return []
    
    def _collect_zfs(self) -> List[Dict[str, str]]:
        """Collect ZFS pool information"""
        try:
            if not self.is_zfs_available():
                self.logger.debug("ZFS not available, skipping ZFS collection")
                return []
            
            if self.zfs_auto_discover or not self.zfs_pools:
                pools = self._discover_zfs_pools()
            else:
                pools = self.zfs_pools
            
            pool_info = []
            for pool_name in pools:
                info = self._get_zfs_pool_info(pool_name)
                if info:
                    # Add type indicator
                    info['type'] = 'ZFS'
                    pool_info.append(info)
            
            self.logger.debug(f"Collected {len(pool_info)} ZFS pools")
            return pool_info
            
        except Exception as e:
            self.logger.error(f"Failed to collect ZFS information: {e}")
            return []
    
    def _collect_mdadm(self) -> List[Dict[str, str]]:
        """Collect MDADM array information"""
        try:
            if not hasattr(self, 'mdadm_collector'):
                return []
            
            arrays = self.mdadm_collector.collect()
            self.logger.debug(f"Collected {len(arrays)} MDADM arrays")
            return arrays
            
        except Exception as e:
            self.logger.error(f"Failed to collect MDADM information: {e}")
            return []
    
    def _discover_zfs_pools(self) -> List[str]:
        """Discover available ZFS pools"""
        try:
            result = subprocess.run([
                'zpool', 'list', '-H', '-o', 'name'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                pools = result.stdout.strip().split('\n')
                pools = [pool.strip() for pool in pools if pool.strip()]
                self.logger.debug(f"Discovered ZFS pools: {pools}")
                return pools
            else:
                self.logger.warning("Failed to list ZFS pools - zpool command failed")
                return []
                
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout while discovering ZFS pools")
            return []
        except FileNotFoundError:
            self.logger.warning("zpool command not found - ZFS not installed?")
            return []
        except Exception as e:
            self.logger.error(f"Error discovering ZFS pools: {e}")
            return []
    
    def _get_zfs_pool_info(self, pool_name: str) -> Optional[Dict[str, str]]:
        """Get detailed information for a specific pool"""
        try:
            # Get pool status and capacity
            result = subprocess.run([
                'zpool', 'list', '-H', '-o', 'name,size,alloc,free,cap,health', pool_name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                self.logger.warning(f"Failed to get info for pool {pool_name}")
                return None
            
            # Parse output: name size alloc free cap health
            parts = result.stdout.strip().split('\t')
            if len(parts) < 6:
                self.logger.warning(f"Unexpected zpool output format for {pool_name}")
                return None
            
            name = parts[0]
            size = parts[1]
            allocated = parts[2]
            free = parts[3]
            capacity_pct = parts[4]
            health = parts[5]
            
            # Clean up capacity percentage
            if capacity_pct.endswith('%'):
                usage = capacity_pct
            else:
                usage = f"{capacity_pct}%"
            
            # Map ZFS health states to display states
            state = self._map_health_state(health)
            
            pool_info = {
                'name': name,
                'capacity': size,
                'usage': usage,
                'state': state,
                'allocated': allocated,
                'free': free,
                'health': health
            }
            
            self.logger.debug(f"Pool {name}: {pool_info}")
            return pool_info
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while getting info for pool {pool_name}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting pool info for {pool_name}: {e}")
            return None
    
    def _map_health_state(self, zfs_health: str) -> str:
        """Map ZFS health states to display-friendly states"""
        health_map = {
            'ONLINE': 'Healthy',
            'DEGRADED': 'Degraded',
            'FAULTED': 'Failed',
            'OFFLINE': 'Offline',
            'REMOVED': 'Removed',
            'UNAVAIL': 'Unavailable',
            'SUSPENDED': 'Suspended'
        }
        
        return health_map.get(zfs_health.upper(), zfs_health)
    
    def get_overall_storage_state(self) -> str:
        """Get overall storage health state"""
        if not self.enabled or not self.health_enabled:
            self.logger.debug("Storage health monitoring disabled, returning Healthy")
            return "Healthy"
        
        try:
            storage_volumes = self.collect()
            
            if not storage_volumes:
                return "Unknown"
            
            # Check ZFS pools
            if 'zfs' in self.storage_types:
                for volume in storage_volumes:
                    if volume.get('type') == 'ZFS':
                        health = volume.get('health', '').upper()
                        if health in ['DEGRADED', 'FAULTED', 'OFFLINE', 'UNAVAIL', 'SUSPENDED']:
                            return "Problem"
            
            # Check MDADM arrays
            if 'mdadm' in self.storage_types:
                for volume in storage_volumes:
                    if volume.get('type') == 'MDADM':
                        raw_state = volume.get('raw_state', '').lower()
                        if raw_state in ['degraded', 'failed', 'inactive', 'recovering', 'resyncing']:
                            return "Problem"
            
            return "Healthy"
            
        except Exception as e:
            self.logger.error(f"Error getting overall storage state: {e}")
            return "Unknown"
    
    def get_pool_details(self, pool_name: str) -> Optional[Dict[str, str]]:
        """Get detailed status for a specific pool"""
        try:
            result = subprocess.run([
                'zpool', 'status', pool_name
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                return {
                    'name': pool_name,
                    'status': result.stdout
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting pool details for {pool_name}: {e}")
            return None
    
    def is_zfs_available(self) -> bool:
        """Check if ZFS is available on the system"""
        try:
            result = subprocess.run([
                'zpool', 'version'
            ], capture_output=True, text=True, timeout=5)
            
            return result.returncode == 0
            
        except FileNotFoundError:
            return False
        except Exception:
            return False