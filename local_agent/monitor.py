"""
System monitoring module using psutil
"""
import psutil
import logging
from datetime import datetime
from typing import List, Tuple
import sys
import os

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import SystemMetrics
from shared.config import MONITOR_INTERVAL

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system resources in real-time"""

    def __init__(self, interval: int = MONITOR_INTERVAL):
        self.interval = interval
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = 100

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        metrics = SystemMetrics()
        
        # RAM metrics
        ram = psutil.virtual_memory()
        metrics.ram_percent = ram.percent
        metrics.ram_used_mb = ram.used / (1024 * 1024)
        metrics.ram_available_mb = ram.available / (1024 * 1024)
        
        # CPU metrics
        metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        metrics.disk_percent = disk.percent
        
        # Process count
        metrics.process_count = len(psutil.pids())
        
        # Top processes by memory
        metrics.top_processes = self._get_top_processes(n=10)
        
        return metrics

    def _get_top_processes(self, n: int = 10) -> List[Tuple[str, int, float]]:
        """Get top N processes by memory usage"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
                    processes.append((proc.info['name'], proc.info['pid'], memory_mb))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory and return top N
            processes.sort(key=lambda x: x[2], reverse=True)
            return processes[:n]
        except Exception as e:
            logger.error(f"Failed to get top processes: {e}")
            return []

    def record_metrics(self, metrics: SystemMetrics) -> None:
        """Store metrics in history"""
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

    def get_metrics_history(self, last_n: int = 10) -> List[SystemMetrics]:
        """Get last N recorded metrics"""
        return self.metrics_history[-last_n:]

    def get_average_metrics(self, last_n: int = 10) -> SystemMetrics:
        """Get average metrics over last N recordings"""
        if not self.metrics_history:
            return self.get_current_metrics()
        
        history = self.metrics_history[-last_n:]
        avg = SystemMetrics()
        avg.ram_percent = sum(m.ram_percent for m in history) / len(history)
        avg.cpu_percent = sum(m.cpu_percent for m in history) / len(history)
        avg.disk_percent = sum(m.disk_percent for m in history) / len(history)
        
        return avg

    def is_low_memory(self, threshold: float = 20.0) -> bool:
        """Check if available memory is below threshold (in MB)"""
        metrics = self.get_current_metrics()
        return metrics.ram_available_mb < threshold

    def is_high_memory_usage(self, threshold: int = 80) -> bool:
        """Check if RAM usage is above threshold (%)"""
        metrics = self.get_current_metrics()
        return metrics.ram_percent > threshold

    def is_high_cpu_usage(self, threshold: int = 80) -> bool:
        """Check if CPU usage is above threshold (%)"""
        metrics = self.get_current_metrics()
        return metrics.cpu_percent > threshold
