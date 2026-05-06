"""
Main local agent orchestrator
Monitors system and manages task routing
"""
import logging
import sys
import os
import asyncio
import time
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitor import SystemMonitor
from optimizer import SystemOptimizer
from router import TaskRouter
from shared.models import Task, SystemMetrics
from shared.config import TaskType, ExecutionLocation, MONITOR_INTERVAL
from shared.client import VLLMClient, CloudClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LightningBoostAgent:
    """Main local agent for LightningBoost"""

    def __init__(self):
        self.monitor = SystemMonitor(interval=MONITOR_INTERVAL)
        self.vllm_client = VLLMClient()
        self.cloud_client = CloudClient()
        self.optimizer = SystemOptimizer(self.vllm_client)
        self.router = TaskRouter(self.vllm_client)
        self.running_tasks = {}

    def start(self):
        """Start the monitoring agent"""
        logger.info("🚀 LightningBoost Agent Starting...")
        
        # Check cloud and vLLM connectivity
        cloud_healthy = self.cloud_client.get_health()
        vllm_healthy = self.vllm_client.health_check()
        
        logger.info(f"Cloud Backend: {'✅ Connected' if cloud_healthy else '⚠️ Offline'}")
        logger.info(f"vLLM Endpoint: {'✅ Connected' if vllm_healthy else '⚠️ Offline'}")
        
        if not vllm_healthy:
            logger.warning("⚠️ vLLM not available - using local processing only")
        
        logger.info("Starting main monitoring loop...")

    def process_metrics(self):
        """Process current system metrics"""
        metrics = self.monitor.get_current_metrics()
        self.monitor.record_metrics(metrics)
        
        logger.debug(
            f"📊 Metrics - RAM: {metrics.ram_percent:.1f}% | "
            f"CPU: {metrics.cpu_percent:.1f}% | "
            f"Available: {metrics.ram_available_mb:.0f}MB"
        )
        
        # Get optimization recommendations
        recommendations = self.optimizer.get_ai_recommendations(metrics)
        
        return metrics, recommendations

    def process_sample_task(self) -> Optional[Task]:
        """Process a sample task (for testing)"""
        metrics = self.monitor.get_current_metrics()
        
        # Create a sample text generation task
        task = self.router.create_task(
            task_type=TaskType.TEXT_GENERATION,
            description="Generate a short poem about AI optimization",
            input_data={"prompt": "Write a haiku about AI helping computers"}
        )
        
        # Route the task
        routing_decision = self.router.route_task(task, metrics)
        task.execution_location = routing_decision.location
        
        logger.info(
            f"📋 Task {task.id[:8]}: {routing_decision.location.value} "
            f"(confidence: {routing_decision.confidence:.1%}) - {routing_decision.reasoning}"
        )
        
        return task

    def submit_task_to_cloud(self, task: Task) -> bool:
        """Submit task to cloud backend"""
        try:
            result = self.cloud_client.submit_task(task.to_dict())
            logger.info(f"☁️ Task {task.id[:8]} submitted to cloud: {result.get('status')}")
            self.running_tasks[task.id] = task
            return True
        except Exception as e:
            logger.error(f"Failed to submit task to cloud: {e}")
            return False

    def check_task_progress(self, task_id: str) -> Optional[dict]:
        """Check progress of a cloud task"""
        result = self.cloud_client.get_task_result(task_id)
        if result:
            logger.debug(f"Task {task_id[:8]} status: {result.get('status')}")
        return result

    def run_once(self):
        """Run one iteration of the monitoring loop"""
        try:
            # Process metrics and get recommendations
            metrics, recommendations = self.process_metrics()
            
            # Log system status
            status_emoji = self._get_status_emoji(metrics)
            logger.info(f"{status_emoji} System Status: RAM {metrics.ram_percent:.0f}% | CPU {metrics.cpu_percent:.0f}%")
            
            # Process a sample task for demo
            task = self.process_sample_task()
            
            # Route and handle task
            if task.execution_location == ExecutionLocation.CLOUD:
                self.submit_task_to_cloud(task)
            
            # Check on running tasks
            for task_id in list(self.running_tasks.keys()):
                task_result = self.check_task_progress(task_id)
                if task_result and task_result.get('status') in ['completed', 'failed']:
                    del self.running_tasks[task_id]
        
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

    def _get_status_emoji(self, metrics: SystemMetrics) -> str:
        """Get emoji representing system health"""
        if metrics.ram_percent > 80:
            return "🔴"  # Red - critical
        elif metrics.ram_percent > 60:
            return "🟡"  # Yellow - warning
        else:
            return "🟢"  # Green - healthy

    def run_continuous(self, interval: int = MONITOR_INTERVAL):
        """Run continuous monitoring loop"""
        self.start()
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.shutdown()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Closing connections...")
        self.cloud_client.close()
        logger.info("✅ Agent stopped")


if __name__ == "__main__":
    agent = LightningBoostAgent()
    
    # For testing: run a few iterations
    for _ in range(3):
        agent.run_once()
        time.sleep(2)
    
    logger.info("Demo run completed. Use run_continuous() for continuous monitoring.")
