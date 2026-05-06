"""
LightningBoost Configuration & Constants
"""
import os
from enum import Enum

# Cloud Backend Settings
CLOUD_HOST = os.getenv("CLOUD_HOST", "localhost")
CLOUD_PORT = int(os.getenv("CLOUD_PORT", 8000))
CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", f"http://{CLOUD_HOST}:{CLOUD_PORT}")

# vLLM Settings
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
VLLM_MODEL = os.getenv("VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
VLLM_TIMEOUT = int(os.getenv("VLLM_TIMEOUT", 60))

# Local Agent Settings
RAM_THRESHOLD_HIGH = int(os.getenv("RAM_THRESHOLD_HIGH", 80))  # percentage
RAM_THRESHOLD_MEDIUM = int(os.getenv("RAM_THRESHOLD_MEDIUM", 60))
CPU_THRESHOLD_HIGH = int(os.getenv("CPU_THRESHOLD_HIGH", 80))

# Task Routing Settings
MIN_LOCAL_RAM_MB = int(os.getenv("MIN_LOCAL_RAM_MB", 500))
LOCAL_TASK_TIMEOUT = int(os.getenv("LOCAL_TASK_TIMEOUT", 30))  # seconds
CLOUD_TASK_TIMEOUT = int(os.getenv("CLOUD_TASK_TIMEOUT", 120))

# Frontend Settings
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "0.0.0.0")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", 8501))

# Monitoring Interval
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 2))  # seconds


class TaskType(Enum):
    """Task type classification"""
    TEXT_GENERATION = "text_generation"
    IMAGE_CLASSIFICATION = "image_classification"
    EMBEDDING = "embedding"
    LIGHTWEIGHT = "lightweight"


class ExecutionLocation(Enum):
    """Where to execute the task"""
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED_CLOUD = "queued_cloud"
