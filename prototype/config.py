"""
LightningBoost · shared/config.py  (MERGED PERFECT)
─────────────────────────────────────────────────────
Single source of truth for all configuration.
Combines CJ's config with Tsyf's AMD-specific settings and auth.
"""

import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# ── Cloud backend ─────────────────────────────────────────────────────────────
CLOUD_HOST     = os.getenv("CLOUD_HOST", "0.0.0.0")
CLOUD_PORT     = int(os.getenv("CLOUD_PORT", 8000))
CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", f"http://localhost:{CLOUD_PORT}")

# API key for cloud backend authentication (set a strong secret in .env)
CLOUD_API_KEY  = os.getenv("CLOUD_API_KEY", "")

# ── vLLM (AMD GPU inference) ──────────────────────────────────────────────────
VLLM_BASE_URL  = os.getenv("VLLM_BASE_URL",  "http://localhost:8001")
VLLM_MODEL     = os.getenv("VLLM_MODEL",     "meta-llama/Llama-3.1-8B-Instruct")
VLLM_TIMEOUT   = int(os.getenv("VLLM_TIMEOUT", 120))

# ── HuggingFace ───────────────────────────────────────────────────────────────
HF_API_TOKEN   = os.getenv("HF_API_TOKEN", "")

# ── Local agent thresholds ────────────────────────────────────────────────────
RAM_THRESHOLD_HIGH   = int(os.getenv("RAM_THRESHOLD_HIGH",   80))   # %  → offload
RAM_THRESHOLD_MEDIUM = int(os.getenv("RAM_THRESHOLD_MEDIUM", 60))   # %  → warn
CPU_THRESHOLD_HIGH   = int(os.getenv("CPU_THRESHOLD_HIGH",   80))   # %  → heavy
MIN_LOCAL_RAM_MB     = int(os.getenv("MIN_LOCAL_RAM_MB",     500))  # MB → must offload
LOCAL_TASK_TIMEOUT   = int(os.getenv("LOCAL_TASK_TIMEOUT",   30))   # s
CLOUD_TASK_TIMEOUT   = int(os.getenv("CLOUD_TASK_TIMEOUT",   120))  # s

# ── Monitor ───────────────────────────────────────────────────────────────────
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 2))   # seconds

# ── Frontend ──────────────────────────────────────────────────────────────────
FRONTEND_HOST            = os.getenv("FRONTEND_HOST", "0.0.0.0")
FRONTEND_PORT            = int(os.getenv("FRONTEND_PORT", 8501))
DASHBOARD_REFRESH_SECONDS= int(os.getenv("DASHBOARD_REFRESH_SECONDS", 3))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# ─── Enums ───────────────────────────────────────────────────────────────────

class TaskType(Enum):
    TEXT_GENERATION    = "text_generation"
    IMAGE_CLASSIFICATION = "image_classification"
    EMBEDDING          = "embedding"
    LIGHTWEIGHT        = "lightweight"


class ExecutionLocation(Enum):
    LOCAL  = "local"
    CLOUD  = "cloud"
    HYBRID = "hybrid"


class TaskStatus(Enum):
    PENDING      = "pending"
    RUNNING      = "running"
    COMPLETED    = "completed"
    FAILED       = "failed"
    QUEUED_CLOUD = "queued_cloud"
