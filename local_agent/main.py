"""
Main local agent orchestrator
Fixes applied:
  BUG 4 - process_sample_task() removed from run_once() loop.
           One-shot startup demo controlled by _sample_task_sent flag.
  BUG 2 - Agent now POSTs psutil metrics to cloud backend (/metrics)
           so the Streamlit dashboard can display *laptop* stats, not cloud server stats.
"""
import logging
import sys
import os
import time
import requests
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor import SystemMonitor
from optimizer import SystemOptimizer
from router import TaskRouter
from shared.models import Task, SystemMetrics
from shared.config import TaskType, ExecutionLocation, MONITOR_INTERVAL
from shared.client import VLLMClient, CloudClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cloud backend URL — override via env var
CLOUD_BACKEND_URL = os.environ.get("CLOUD_BASE_URL", "http://localhost:8000")


class LightningBoostAgent:
    """Main local agent for LightningBoost"""

    def __init__(self):
        self.monitor      = SystemMonitor(interval=MONITOR_INTERVAL)
        self.vllm_client  = VLLMClient()
        self.cloud_client = CloudClient()
        self.optimizer    = SystemOptimizer(self.vllm_client)
        self.router       = TaskRouter(self.vllm_client)
        self.running_tasks: dict = {}

        # BUG 4 FIX: flag so demo task fires exactly once
        self._sample_task_sent = False

    def start(self):
        logger.info("🚀 LightningBoost Agent Starting...")
        cloud_healthy = self.cloud_client.get_health()
        vllm_healthy  = self.vllm_client.health_check()
        logger.info(f"Cloud Backend: {'✅ Connected' if cloud_healthy else '⚠️ Offline'}")
        logger.info(f"vLLM Endpoint: {'✅ Connected' if vllm_healthy else '⚠️ Offline'}")
        if not vllm_healthy:
            logger.warning("⚠️ vLLM not available - using local processing only")
        logger.info("Starting main monitoring loop...")

    def process_metrics(self):
        """Collect metrics and get recommendations."""
        metrics = self.monitor.get_current_metrics()
        self.monitor.record_metrics(metrics)
        logger.debug(
            f"📊 Metrics — RAM: {metrics.ram_percent:.1f}% | "
            f"CPU: {metrics.cpu_percent:.1f}% | "
            f"Free: {metrics.ram_available_mb:.0f} MB"
        )
        recommendations = self.optimizer.get_ai_recommendations(metrics)
        return metrics, recommendations

    def push_metrics_to_cloud(self, metrics: SystemMetrics):
        """
        BUG 2 FIX: POST laptop psutil data to cloud backend.
        Dashboard reads /metrics from cloud — never runs psutil itself.
        """
        payload = {
            "ram_percent":    metrics.ram_percent,
            "ram_used_mb":    metrics.ram_used_mb,
            "ram_free_mb":    metrics.ram_available_mb,
            "cpu_percent":    metrics.cpu_percent,
            "disk_percent":   metrics.disk_percent,
            "process_count":  metrics.process_count,
            "top_processes":  [
                {"name": name, "pid": pid, "memory_mb": mem}
                for name, pid, mem in (metrics.top_processes or [])[:5]
            ],
        }
        try:
            requests.post(
                f"{CLOUD_BACKEND_URL}/metrics",
                json=payload,
                timeout=3,
            )
        except Exception as e:
            logger.debug(f"Metrics push failed (cloud offline?): {e}")

    def process_sample_task(self) -> Optional[Task]:
        """Create and route a demo task. Called ONCE on startup only."""
        metrics = self.monitor.get_current_metrics()
        task = self.router.create_task(
            task_type=TaskType.TEXT_GENERATION,
            description="Generate a short poem about AI optimization",
            input_data={"prompt": "Write a haiku about AI helping computers"},
        )
        routing_decision = self.router.route_task(task, metrics)
        task.execution_location = routing_decision.location
        logger.info(
            f"📋 Demo task {task.id[:8]}: {routing_decision.location.value} "
            f"(confidence: {routing_decision.confidence:.1%}) — {routing_decision.reasoning}"
        )
        return task

    def submit_task_to_cloud(self, task: Task) -> bool:
        try:
            result = self.cloud_client.submit_task(task.to_dict())
            logger.info(f"☁️  Task {task.id[:8]} → cloud: {result.get('status')}")
            self.running_tasks[task.id] = task
            return True
        except Exception as e:
            logger.error(f"Failed to submit task to cloud: {e}")
            return False

    def check_task_progress(self, task_id: str) -> Optional[dict]:
        result = self.cloud_client.get_task_result(task_id)
        if result:
            logger.debug(f"Task {task_id[:8]} status: {result.get('status')}")
        return result

    def run_once(self):
        """
        One monitoring iteration.
        BUG 4 FIX: process_sample_task() is NOT called here in the loop.
        It fires once via _send_startup_demo_task() on first iteration.
        """
        try:
            metrics, recommendations = self.process_metrics()

            status_emoji = self._get_status_emoji(metrics)
            logger.info(
                f"{status_emoji} RAM {metrics.ram_percent:.0f}% | CPU {metrics.cpu_percent:.0f}%"
            )

            # BUG 2 FIX: push to cloud every tick
            self.push_metrics_to_cloud(metrics)

            # BUG 4 FIX: only send demo task once
            if not self._sample_task_sent:
                task = self.process_sample_task()
                if task and task.execution_location == ExecutionLocation.CLOUD:
                    self.submit_task_to_cloud(task)
                self._sample_task_sent = True

            # Check in-flight cloud tasks
            for task_id in list(self.running_tasks.keys()):
                task_result = self.check_task_progress(task_id)
                if task_result and task_result.get("status") in ("completed", "failed"):
                    del self.running_tasks[task_id]

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    def _get_status_emoji(self, metrics: SystemMetrics) -> str:
        if metrics.ram_percent > 80:
            return "🔴"
        elif metrics.ram_percent > 60:
            return "🟡"
        return "🟢"

    def run_continuous(self, interval: int = MONITOR_INTERVAL):
        self.start()
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.shutdown()

    def shutdown(self):
        logger.info("Closing connections...")
        self.cloud_client.close()
        logger.info("✅ Agent stopped")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend",  default=CLOUD_BACKEND_URL,
                        help="Cloud backend URL (e.g. http://YOUR_AMD_IP:8000)")
    parser.add_argument("--interval", type=int, default=MONITOR_INTERVAL,
                        help="Polling interval in seconds")
    args = parser.parse_args()

    CLOUD_BACKEND_URL = args.backend  # override global for push_metrics_to_cloud

    agent = LightningBoostAgent()
    agent.run_continuous(interval=args.interval)