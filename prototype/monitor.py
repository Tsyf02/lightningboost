"""
LightningBoost · local_agent/monitor.py  (MERGED PERFECT)
──────────────────────────────────────────────────────────
Merges the best of both versions:
  ✅ CJ's:    Clean SystemMetrics dataclass, disk tracking, process count
  ✅ Tsyf's:  Background thread + thread-safe snapshot → no blocking on psutil

WHY THREADING MATTERS:
  CJ's original called psutil.cpu_percent(interval=0.1) on every request.
  This blocks for 100ms each call. In a live Streamlit dashboard that auto-
  refreshes every 3s, this causes visible stuttering and inaccurate readings.
  The background thread polls at a fixed interval and any caller just reads
  the latest snapshot instantly — zero blocking.
"""

import psutil
import logging
import threading
import time
from datetime import datetime
from typing import List, Tuple, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.models import SystemMetrics
from shared.config import MONITOR_INTERVAL, RAM_THRESHOLD_HIGH, RAM_THRESHOLD_MEDIUM

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Real-time system resource monitor.

    Runs a background daemon thread that polls psutil every MONITOR_INTERVAL
    seconds. All public methods read from a thread-safe snapshot — never
    blocking the caller on a psutil call.

    Usage:
        monitor = SystemMonitor()
        monitor.start()                     # begin background polling
        snap = monitor.get_current_metrics()  # always instant
        monitor.stop()                      # graceful shutdown
    """

    def __init__(self, interval: int = MONITOR_INTERVAL):
        self.interval   = interval
        self._lock      = threading.Lock()
        self._snapshot: Optional[SystemMetrics] = None
        self._history:  List[SystemMetrics] = []
        self._max_history = 100
        self._running   = False
        self._thread:   Optional[threading.Thread] = None
        # Baseline for I/O delta calculations
        self._prev_net  = psutil.net_io_counters()
        self._prev_disk = psutil.disk_io_counters()
        self._prev_time = time.time()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Start background polling. Safe to call multiple times."""
        if self._running:
            return
        self._running = True
        # Take one immediate snapshot so callers don't get None on first read
        self._snapshot = self._collect()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="lb-monitor")
        self._thread.start()
        logger.info("SystemMonitor started (interval=%ds)", self.interval)

    def stop(self):
        """Gracefully stop the background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("SystemMonitor stopped")

    # ── Public API (all instant — reads from snapshot) ────────────────────────

    def get_current_metrics(self) -> SystemMetrics:
        """Return the latest system metrics snapshot. Never blocks."""
        with self._lock:
            if self._snapshot is None:
                # First call before thread starts — do a synchronous collect
                self._snapshot = self._collect()
            return self._snapshot

    def record_metrics(self, metrics: SystemMetrics) -> None:
        """Append metrics to history (called automatically by background thread)."""
        with self._lock:
            self._history.append(metrics)
            if len(self._history) > self._max_history:
                self._history.pop(0)

    def get_metrics_history(self, last_n: int = 10) -> List[SystemMetrics]:
        """Return the last N recorded metrics snapshots."""
        with self._lock:
            return list(self._history[-last_n:])

    def get_average_metrics(self, last_n: int = 10) -> SystemMetrics:
        """Compute average RAM/CPU/disk over last N recordings."""
        with self._lock:
            history = self._history[-last_n:]
        if not history:
            return self.get_current_metrics()
        avg = SystemMetrics()
        avg.ram_percent  = sum(m.ram_percent  for m in history) / len(history)
        avg.cpu_percent  = sum(m.cpu_percent  for m in history) / len(history)
        avg.disk_percent = sum(m.disk_percent for m in history) / len(history)
        return avg

    def is_high_memory_usage(self, threshold: int = RAM_THRESHOLD_HIGH) -> bool:
        return self.get_current_metrics().ram_percent > threshold

    def is_medium_memory_usage(self, threshold: int = RAM_THRESHOLD_MEDIUM) -> bool:
        return self.get_current_metrics().ram_percent > threshold

    def is_high_cpu_usage(self, threshold: int = 80) -> bool:
        return self.get_current_metrics().cpu_percent > threshold

    def should_offload(self) -> bool:
        """True when the system is under enough pressure to route tasks to cloud."""
        m = self.get_current_metrics()
        return m.ram_percent > RAM_THRESHOLD_HIGH or m.cpu_percent > 80

    # ── Background thread ─────────────────────────────────────────────────────

    def _loop(self):
        """Background daemon: collect → store → sleep → repeat."""
        while self._running:
            try:
                snap = self._collect()
                with self._lock:
                    self._snapshot = snap
                    self._history.append(snap)
                    if len(self._history) > self._max_history:
                        self._history.pop(0)
                logger.debug(
                    "Monitor: RAM=%.1f%% CPU=%.1f%% Disk=%.1f%%",
                    snap.ram_percent, snap.cpu_percent, snap.disk_percent
                )
            except Exception as exc:
                logger.error("Monitor poll error: %s", exc)
            time.sleep(self.interval)

    # ── Data collection ───────────────────────────────────────────────────────

    def _collect(self) -> SystemMetrics:
        """
        Synchronous psutil collection. Only called from the background thread
        (or once synchronously at startup). Never call from request handlers.
        """
        metrics = SystemMetrics()

        # ── RAM ───────────────────────────────────────────────────────────────
        vm = psutil.virtual_memory()
        metrics.ram_percent      = vm.percent
        metrics.ram_used_mb      = vm.used      / (1024 * 1024)
        metrics.ram_available_mb = vm.available  / (1024 * 1024)

        # ── CPU — use interval=None so it reads the rolling average, no blocking
        metrics.cpu_percent = psutil.cpu_percent(interval=None)

        # ── Disk ──────────────────────────────────────────────────────────────
        try:
            disk = psutil.disk_usage('/')
            metrics.disk_percent = disk.percent
        except Exception:
            metrics.disk_percent = 0.0

        # ── Process list ──────────────────────────────────────────────────────
        metrics.process_count = len(psutil.pids())
        metrics.top_processes = self._top_processes(n=10)

        # ── I/O deltas ────────────────────────────────────────────────────────
        now = time.time()
        elapsed = max(now - self._prev_time, 0.001)
        try:
            curr_net  = psutil.net_io_counters()
            curr_disk = psutil.disk_io_counters()
            metrics.net_sent_mb_s  = round((curr_net.bytes_sent  - self._prev_net.bytes_sent)  / elapsed / 1e6, 2)
            metrics.net_recv_mb_s  = round((curr_net.bytes_recv  - self._prev_net.bytes_recv)  / elapsed / 1e6, 2)
            metrics.disk_read_mb_s = round((curr_disk.read_bytes  - self._prev_disk.read_bytes) / elapsed / 1e6, 2)
            metrics.disk_write_mb_s= round((curr_disk.write_bytes - self._prev_disk.write_bytes)/ elapsed / 1e6, 2)
            self._prev_net  = curr_net
            self._prev_disk = curr_disk
        except Exception:
            pass
        self._prev_time = now

        # ── Battery (laptops) ─────────────────────────────────────────────────
        try:
            bat = psutil.sensors_battery()
            if bat:
                metrics.battery_percent = round(bat.percent, 1)
                metrics.battery_plugged = bat.power_plugged
        except Exception:
            pass

        return metrics

    @staticmethod
    def _top_processes(n: int = 10) -> List[Tuple[str, int, float]]:
        """Return top N processes by RSS memory. Returns (name, pid, memory_mb)."""
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                mb = p.info['memory_info'].rss / (1024 * 1024)
                procs.append((p.info['name'], p.info['pid'], round(mb, 2)))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x[2], reverse=True)
        return procs[:n]
