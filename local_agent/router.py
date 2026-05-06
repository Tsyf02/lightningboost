"""
Intelligent task routing agent
Routes tasks between local and cloud execution
"""
import logging
import sys
import os
from typing import Tuple
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Task, RoutingDecision, SystemMetrics
from shared.config import (
    TaskType, ExecutionLocation, TaskStatus,
    RAM_THRESHOLD_HIGH, RAM_THRESHOLD_MEDIUM,
    MIN_LOCAL_RAM_MB
)
from shared.prompts import get_routing_decision_prompt
from shared.client import VLLMClient

logger = logging.getLogger(__name__)


class TaskRouter:
    """Routes tasks between local and cloud execution"""

    def __init__(self, vllm_client: VLLMClient = None):
        self.vllm_client = vllm_client or VLLMClient()

    def create_task(self, task_type: TaskType, description: str, input_data: dict) -> Task:
        """Create a new task"""
        return Task(
            id=str(uuid.uuid4()),
            task_type=task_type,
            description=description,
            input_data=input_data,
            status=TaskStatus.PENDING
        )

    def route_task(self, task: Task, metrics: SystemMetrics) -> RoutingDecision:
        """Decide whether to route task to local or cloud"""
        
        # Rule-based initial decision
        location, confidence, reasoning = self._rule_based_routing(task, metrics)
        
        # Try to refine with AI if available
        if self.vllm_client.health_check():
            location, confidence, reasoning = self._ai_enhanced_routing(
                task, metrics, location, confidence, reasoning
            )
        
        return RoutingDecision(
            task_id=task.id,
            location=location,
            confidence=confidence,
            reasoning=reasoning
        )

    def _rule_based_routing(self, task: Task, metrics: SystemMetrics) -> Tuple[ExecutionLocation, float, str]:
        """Rule-based routing logic"""
        
        # Memory check - if critically low, must use cloud
        if metrics.ram_available_mb < MIN_LOCAL_RAM_MB:
            return ExecutionLocation.CLOUD, 0.95, "Critical memory shortage - routing to cloud"
        
        # RAM usage check
        if metrics.ram_percent > RAM_THRESHOLD_HIGH:
            return ExecutionLocation.CLOUD, 0.9, "High system memory usage - routing to cloud"
        
        # Task type-specific routing
        if task.task_type == TaskType.TEXT_GENERATION:
            if metrics.ram_percent > RAM_THRESHOLD_MEDIUM or metrics.cpu_percent > 70:
                return ExecutionLocation.CLOUD, 0.85, "Resource constraints - cloud better suited"
            return ExecutionLocation.LOCAL, 0.7, "Sufficient local resources available"
        
        elif task.task_type == TaskType.IMAGE_CLASSIFICATION:
            # Better on cloud if available
            if metrics.ram_available_mb > MIN_LOCAL_RAM_MB * 2:
                return ExecutionLocation.LOCAL, 0.6, "Image classification can run locally"
            return ExecutionLocation.CLOUD, 0.9, "Route to cloud GPU for image processing"
        
        elif task.task_type == TaskType.EMBEDDING:
            if metrics.ram_available_mb < MIN_LOCAL_RAM_MB * 1.5:
                return ExecutionLocation.CLOUD, 0.85, "Embeddings routing to cloud"
            return ExecutionLocation.LOCAL, 0.7, "Embeddings can process locally"
        
        elif task.task_type == TaskType.LIGHTWEIGHT:
            return ExecutionLocation.LOCAL, 0.95, "Lightweight task - run locally"
        
        # Default: local if resources available
        if metrics.ram_available_mb > MIN_LOCAL_RAM_MB:
            return ExecutionLocation.LOCAL, 0.5, "Default to local with available resources"
        
        return ExecutionLocation.CLOUD, 0.7, "Insufficient local resources"

    def _ai_enhanced_routing(self, task: Task, metrics: SystemMetrics, 
                            initial_location: ExecutionLocation, 
                            initial_confidence: float, 
                            initial_reasoning: str) -> Tuple[ExecutionLocation, float, str]:
        """Refine routing decision with AI analysis"""
        try:
            prompt = get_routing_decision_prompt(
                task.description,
                metrics.ram_percent,
                metrics.cpu_percent,
                metrics.ram_available_mb
            )
            
            response = self.vllm_client.generate(
                prompt=prompt,
                model="meta-llama/Llama-3.1-8B-Instruct",
                max_tokens=100
            )
            
            if response:
                decision_text = response.upper()
                if "LOCAL" in decision_text:
                    return ExecutionLocation.LOCAL, 0.8, f"AI Router: {response[:100]}"
                elif "CLOUD" in decision_text:
                    return ExecutionLocation.CLOUD, 0.8, f"AI Router: {response[:100]}"
        
        except Exception as e:
            logger.debug(f"AI routing failed, using rule-based: {e}")
        
        # Return initial decision if AI fails
        return initial_location, initial_confidence, initial_reasoning

    def should_offload_to_cloud(self, metrics: SystemMetrics) -> bool:
        """Check if tasks should be offloaded due to system pressure"""
        return (metrics.ram_percent > RAM_THRESHOLD_HIGH or 
                metrics.ram_available_mb < MIN_LOCAL_RAM_MB)

    def update_task_status(self, task: Task, status: TaskStatus, 
                          result: dict = None, error: str = None) -> Task:
        """Update task status"""
        task.status = status
        
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now()
        elif status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            task.result = result
        elif status == TaskStatus.FAILED:
            task.completed_at = datetime.now()
            task.error = error
        
        return task
