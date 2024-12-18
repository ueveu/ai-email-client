"""
Service for monitoring network connectivity.
"""

import socket
import requests
import time
from typing import List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from utils.logger import logger

class NetworkService(QObject):
    """Service for monitoring network connectivity."""
    
    # Signals
    connection_changed = pyqtSignal(bool)  # Emits True when connected, False when disconnected
    speed_updated = pyqtSignal(dict)  # Emits speed test results
    
    def __init__(self):
        """Initialize the network service."""
        super().__init__()
        
        # List of reliable hosts to check connectivity
        self.check_hosts = [
            ('8.8.8.8', 53),  # Google DNS
            ('1.1.1.1', 53),  # Cloudflare DNS
            ('208.67.222.222', 53)  # OpenDNS
        ]
        
        # List of reliable URLs to check internet connectivity
        self.check_urls = [
            'https://www.google.com',
            'https://www.cloudflare.com',
            'https://www.microsoft.com'
        ]
        
        # Network status
        self.is_online = False
        self.is_offline_mode = False
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._check_connection)
    
    def start_monitoring(self, interval: int = 30000):
        """
        Start network monitoring.
        
        Args:
            interval: Check interval in milliseconds (default: 30s)
        """
        # Initial check
        self._check_connection()
        
        # Start periodic checks
        self.monitor_timer.start(interval)
    
    def stop_monitoring(self):
        """Stop network monitoring."""
        self.monitor_timer.stop()
    
    def set_offline_mode(self, enabled: bool):
        """
        Set offline mode.
        
        Args:
            enabled: Whether to enable offline mode
        """
        self.is_offline_mode = enabled
        if enabled:
            self.is_online = False
            self.connection_changed.emit(False)
        else:
            # Check current status
            self._check_connection()
    
    def _check_connection(self):
        """Check connection and emit signal if status changed."""
        if self.is_offline_mode:
            return
        
        is_connected = self.check_connectivity()
        if is_connected != self.is_online:
            self.is_online = is_connected
            self.connection_changed.emit(is_connected)
            
            # Log status change
            status = "connected" if is_connected else "disconnected"
            logger.info(f"Network status changed: {status}")
    
    def check_connectivity(self, timeout: float = 3.0) -> bool:
        """
        Check if there is network connectivity.
        
        Args:
            timeout (float): Timeout in seconds for each check
            
        Returns:
            bool: True if network is available, False otherwise
        """
        # First try socket connection to DNS servers
        if self._check_socket_connectivity(timeout):
            return True
        
        # If socket check fails, try HTTP requests
        return self._check_http_connectivity(timeout)
    
    def _check_socket_connectivity(self, timeout: float) -> bool:
        """
        Check connectivity using socket connections.
        
        Args:
            timeout (float): Timeout in seconds
            
        Returns:
            bool: True if connection successful
        """
        for host, port in self.check_hosts:
            try:
                socket.create_connection((host, port), timeout=timeout)
                return True
            except OSError as e:
                logger.debug(f"Socket connection failed to {host}:{port} - {str(e)}")
        return False
    
    def _check_http_connectivity(self, timeout: float) -> bool:
        """
        Check connectivity using HTTP requests.
        
        Args:
            timeout (float): Timeout in seconds
            
        Returns:
            bool: True if connection successful
        """
        for url in self.check_urls:
            try:
                response = requests.head(url, timeout=timeout)
                if response.status_code == 200:
                    return True
            except requests.RequestException as e:
                logger.debug(f"HTTP connection failed to {url} - {str(e)}")
        return False
    
    def get_connection_speed(self, timeout: float = 5.0) -> dict:
        """
        Test connection speed.
        
        Args:
            timeout (float): Timeout in seconds
            
        Returns:
            dict: Connection speed information
        """
        if not self.check_connectivity(timeout):
            return {
                'status': 'offline',
                'latency': None,
                'download_speed': None
            }
        
        # Test latency
        latency = self._test_latency()
        
        # Test download speed
        download_speed = self._test_download_speed()
        
        results = {
            'status': 'online',
            'latency': latency,
            'download_speed': download_speed
        }
        
        # Emit speed update
        self.speed_updated.emit(results)
        
        return results
    
    def _test_latency(self, samples: int = 3) -> float:
        """
        Test connection latency.
        
        Args:
            samples (int): Number of samples to test
            
        Returns:
            float: Average latency in milliseconds
        """
        total_time = 0
        successful_samples = 0
        
        for _ in range(samples):
            try:
                start_time = time.time()
                requests.head('https://www.google.com', timeout=2)
                end_time = time.time()
                
                total_time += (end_time - start_time) * 1000  # Convert to ms
                successful_samples += 1
            except:
                continue
        
        if successful_samples == 0:
            return None
        
        return total_time / successful_samples
    
    def _test_download_speed(self, file_size: int = 1024 * 1024) -> float:
        """
        Test download speed using a small file.
        
        Args:
            file_size (int): Size of file to download in bytes
            
        Returns:
            float: Download speed in Mbps
        """
        try:
            # Download a small file from a reliable CDN
            url = f'https://speed.cloudflare.com/__down?bytes={file_size}'
            
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                duration = end_time - start_time
                speed_bps = (len(response.content) * 8) / duration
                return speed_bps / 1_000_000  # Convert to Mbps
        except:
            pass
        
        return None 