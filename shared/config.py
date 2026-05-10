"""
LightningBoost · shared/config.py
─────────────────────────────────────────────────────────────
Thread-safe singleton configuration loading from environment.
Includes Pydantic SecretStr for safe credential handling.
"""

import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT_DIR      = Path(__file__).resolve().parent.parent
DOT_ENV_PATH  = ROOT_DIR / ".env"




if DOT_ENV_PATH.exists():
    print(f"Loading environment variables from {DOT_ENV_PATH}")
    load_dotenv(dotenv_path=DOT_ENV_PATH)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskType(Enum):
    TEXT_GENERATION      = "text_generation"
    IMAGE_CLASSIFICATION = "image_classification"
    EMBEDDING            = "embedding"
    LIGHTWEIGHT          = "lightweight"
    VIDEO_RENDER         = "video_render"
    CODE_EXECUTION       = "code_execution"

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

# ---------------------------------------------------------------------------
# Singleton metaclass
# ---------------------------------------------------------------------------

class SingletonMeta(type):
    """Thread-safe singleton metaclass."""
    _instances: dict = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings(metaclass=SingletonMeta):

    # ── Cloud Backend ────────────────────────────────────────────────────────
    CLOUD_HOST: str          = os.getenv("CLOUD_HOST", "0.0.0.0")
    CLOUD_PORT: int          = int(os.getenv("CLOUD_PORT", 8000))
    CLOUD_BASE_URL: str      = os.getenv("CLOUD_BASE_URL", f"http://localhost:{CLOUD_PORT}")
    CLOUD_API_KEY: SecretStr = SecretStr(os.getenv("CLOUD_API_KEY", ""))

    # ── AI Models & Endpoints (AMD Cloud) ────────────────────────────────────
    # Primary: Vision + Text (19GB, fast, Multimodal)
    VL_MODEL_URL: str        = os.getenv("VL_MODEL_URL", "http://localhost:8080")
    PRIMARY_MODEL: str       = os.getenv("PRIMARY_MODEL", "Qwen3-VL-32B-Instruct-GGUF")
    
    # Secondary: Pure Text (20GB, instant responses)
    TEXT_MODEL_URL: str      = os.getenv("TEXT_MODEL_URL", "http://localhost:8081")
    SECONDARY_MODEL: str     = os.getenv("SECONDARY_MODEL", "Qwen3.5-35B-A3B-GGUF")

    # Legacy vLLM bindings mapping to secondary
    VLLM_BASE_URL: str       = os.getenv("VLLM_BASE_URL", "http://localhost:8081")
    VLLM_MODEL: str          = os.getenv("VLLM_MODEL", "Qwen3.5-35B-A3B-GGUF")
    VLLM_TIMEOUT: int        = int(os.getenv("VLLM_TIMEOUT", 120))
    
    # ── HuggingFace ──────────────────────────────────────────────────────────
    HF_API_TOKEN: SecretStr  = SecretStr(os.getenv("HF_API_TOKEN", ""))

    # ── Agent Thresholds ─────────────────────────────────────────────────────
    RAM_THRESHOLD_HIGH: int   = int(os.getenv("RAM_THRESHOLD_HIGH", 80))
    RAM_THRESHOLD_MEDIUM: int = int(os.getenv("RAM_THRESHOLD_MEDIUM", 60))
    CPU_THRESHOLD_HIGH: int   = int(os.getenv("CPU_THRESHOLD_HIGH", 80))
    MIN_LOCAL_RAM_MB: int     = int(os.getenv("MIN_LOCAL_RAM_MB", 500))
    MONITOR_INTERVAL: int     = int(os.getenv("MONITOR_INTERVAL", 2))

    # ── Task Timeouts ────────────────────────────────────────────────────────
    LOCAL_TASK_TIMEOUT: int   = int(os.getenv("LOCAL_TASK_TIMEOUT", 30))
    CLOUD_TASK_TIMEOUT: int   = int(os.getenv("CLOUD_TASK_TIMEOUT", 120))

    # ── Frontend & Logging ───────────────────────────────────────────────────
    FRONTEND_HOST: str             = os.getenv("FRONTEND_HOST", "0.0.0.0")
    FRONTEND_PORT: int             = int(os.getenv("FRONTEND_PORT", 8501))
    DASHBOARD_REFRESH_SECONDS: int = int(os.getenv("DASHBOARD_REFRESH_SECONDS", 3))
    LOG_LEVEL: str                 = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Module-level Aliases (Maintains compatibility with legacy code imports)
# ---------------------------------------------------------------------------

settings = Settings()

CLOUD_HOST                = settings.CLOUD_HOST
CLOUD_PORT                = settings.CLOUD_PORT
CLOUD_BASE_URL            = settings.CLOUD_BASE_URL
CLOUD_API_KEY             = settings.CLOUD_API_KEY.get_secret_value()

VL_MODEL_URL              = settings.VL_MODEL_URL
PRIMARY_MODEL             = settings.PRIMARY_MODEL
TEXT_MODEL_URL            = settings.TEXT_MODEL_URL
SECONDARY_MODEL           = settings.SECONDARY_MODEL

VLLM_BASE_URL             = settings.VLLM_BASE_URL
VLLM_MODEL                = settings.VLLM_MODEL
VLLM_TIMEOUT              = settings.VLLM_TIMEOUT

HF_API_TOKEN              = settings.HF_API_TOKEN.get_secret_value()

RAM_THRESHOLD_HIGH        = settings.RAM_THRESHOLD_HIGH
RAM_THRESHOLD_MEDIUM      = settings.RAM_THRESHOLD_MEDIUM
CPU_THRESHOLD_HIGH        = settings.CPU_THRESHOLD_HIGH
MIN_LOCAL_RAM_MB          = settings.MIN_LOCAL_RAM_MB
MONITOR_INTERVAL          = settings.MONITOR_INTERVAL

LOCAL_TASK_TIMEOUT        = settings.LOCAL_TASK_TIMEOUT
CLOUD_TASK_TIMEOUT        = settings.CLOUD_TASK_TIMEOUT

FRONTEND_HOST             = settings.FRONTEND_HOST
FRONTEND_PORT             = settings.FRONTEND_PORT
DASHBOARD_REFRESH_SECONDS = settings.DASHBOARD_REFRESH_SECONDS
LOG_LEVEL                 = settings.LOG_LEVEL