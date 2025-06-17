"""
Tests for data collectors
"""

import pytest
from unittest.mock import patch, MagicMock
from m5nas_monitor.collectors import TemperatureCollector, NetworkCollector, StorageCollector


class TestTemperatureCollector:
    
    def test_collect_returns_dict(self):
        collector = TemperatureCollector()
        result = collector.collect()
        
        assert isinstance(result, dict)
        assert 'system' in result
        assert all(f'hdd{i}' in result for i in range(1, 6))
    
    @patch('subprocess.run')
    def test_get_sensors_temperature(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="coretemp-isa-0000\nCore 0: +45.0°C\n"
        )
        
        collector = TemperatureCollector()
        temp = collector._get_sensors_temperature()
        
        assert temp == 45.0
    
    @patch('psutil.sensors_temperatures')
    def test_get_psutil_temperature(self, mock_sensors):
        mock_sensor = MagicMock()
        mock_sensor.current = 42.5
        mock_sensor.label = 'Core 0'
        
        mock_sensors.return_value = {'coretemp': [mock_sensor]}
        
        collector = TemperatureCollector()
        temp = collector._get_psutil_temperature()
        
        assert temp == 42.5


class TestNetworkCollector:
    
    def test_collect_returns_dict(self):
        collector = NetworkCollector()
        result = collector.collect()
        
        assert isinstance(result, dict)
        assert 'mac' in result
        assert 'ipv4' in result
        assert 'ipv6' in result
    
    @patch('netifaces.interfaces')
    @patch('netifaces.ifaddresses')
    def test_get_mac_address(self, mock_ifaddresses, mock_interfaces):
        mock_interfaces.return_value = ['eth0']
        mock_ifaddresses.return_value = {
            17: [{'addr': 'aa:bb:cc:dd:ee:ff'}]  # AF_LINK = 17
        }
        
        collector = NetworkCollector()
        mac = collector._get_mac_address('eth0')
        
        assert mac == 'AA:BB:CC:DD:EE:FF'


class TestStorageCollector:
    
    def test_collect_returns_list(self):
        collector = StorageCollector()
        result = collector.collect()
        
        assert isinstance(result, list)
    
    @patch('subprocess.run')
    def test_discover_pools(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="tank\nbackup\n"
        )
        
        collector = StorageCollector()
        pools = collector._discover_pools()
        
        assert pools == ['tank', 'backup']
    
    @patch('subprocess.run')
    def test_get_pool_info(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="tank\t2T\t1.5T\t500G\t75%\tONLINE\n"
        )
        
        collector = StorageCollector()
        info = collector._get_pool_info('tank')
        
        assert info is not None
        assert info['name'] == 'tank'
        assert info['capacity'] == '2T'
        assert info['usage'] == '75%'
        assert info['state'] == 'Healthy'