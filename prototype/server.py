"""
LightningBoost · cloud_backend/server.py  (MERGED PERFECT)
────────────────────────────────────────────────────────────
MERGES:
  ✅ CJ's:    FastAPI, BackgroundTasks, full task lifecycle, vLLM client
  ✅ Tsyf's:  API key authentication middleware, /metrics endpoint (live psutil),
              threaded SystemMonitor, severity classification

KEY ADDITIONS vs CJ's original:
  1. X-API-Key middleware — prevents anyone who finds the AMD cloud IP from
     consuming your $100 GPU credits
  2. GET /metrics — returns REAL live psutil data so the Streamlit dashboard
     doesn't need hardcoded values
  3. SystemMonitor runs as a background thread from startup
"""

from __future__ import annotations

import logging
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Task, SystemMetrics, RoutingDecision
from shared.config import (
    TaskStatus, ExecutionLocation, TaskType,
    CLOUD_HOST, CLOUD_PORT, VLLM_MODEL, CLOUD_API_KEY,
    RAM_THRESHOLD_HIGH, RAM_THRESHOLD_MEDIUM, CPU_THRESHOLD_HIGH,
)
from shared.client import VLLMClient

# Import the threaded monitor (merged from Tsyf's version)
# We run it here so the cloud backend can also serve /metrics
import psutil
from local_agent.monitor import SystemMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="LightningBoost Cloud Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ─── Global singletons ────────────────────────────────────────────────────────
vllm_client  = VLLMClient()
system_mon   = SystemMonitor()
tasks_db:    Dict[str, Task]           = {}
results_db:  Dict[str, Dict[str, Any]] = {}


# ─── Authentication ───────────────────────────────────────────────────────────

async def verify_api_key(request: Request):
    """
    Dependency: checks X-API-Key header.
    Skips check if CLOUD_API_KEY is not configured (dev mode).
    """
    if not CLOUD_API_KEY:
        return  # open in dev mode
    key = request.headers.get("X-API-Key", "")
    if key != CLOUD_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")


# ─── Startup / shutdown ───────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("🚀 LightningBoost backend starting…")
    system_mon.start()                    # ← threaded psutil monitor

    if vllm_client.health_check():
        models = vllm_client.list_models()
        logger.info("✅ vLLM ready — %d model(s)", len(models) if models else 0)
    else:
        logger.warning("⚠️  vLLM offline — rule-based routing only")


@app.on_event("shutdown")
async def shutdown():
    system_mon.stop()
    logger.info("Backend stopped")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status":         "healthy",
        "timestamp":      datetime.now().isoformat(),
        "vllm_available": vllm_client.health_check(),
    }


@app.get("/metrics", dependencies=[Depends(verify_api_key)])
async def metrics():
    """
    NEW (Tsyf's addition): Returns LIVE psutil data from the threaded monitor.
    The Streamlit dashboard calls this instead of hardcoding values.
    """
    m = system_mon.get_current_metrics()

    # Severity classification (from Tsyf's version)
    if m.ram_percent >= RAM_THRESHOLD_HIGH or m.cpu_percent >= CPU_THRESHOLD_HIGH:
        severity = "heavy"
    elif m.ram_percent >= RAM_THRESHOLD_MEDIUM:
        severity = "warning"
    else:
        severity = "ok"

    return {
        "timestamp":        datetime.now().isoformat(),
        "severity":         severity,
        "ram_percent":      m.ram_percent,
        "ram_used_mb":      m.ram_used_mb,
        "ram_available_mb": m.ram_available_mb,
        "cpu_percent":      m.cpu_percent,
        "disk_percent":     m.disk_percent,
        "process_count":    m.process_count,
        "top_processes":    m.top_processes,  # [(name, pid, mb), ...]
        "battery_percent":  getattr(m, "battery_percent", None),
        "battery_plugged":  getattr(m, "battery_plugged", None),
        "net_sent_mb_s":    getattr(m, "net_sent_mb_s", 0),
        "net_recv_mb_s":    getattr(m, "net_recv_mb_s", 0),
        "disk_read_mb_s":   getattr(m, "disk_read_mb_s", 0),
        "disk_write_mb_s":  getattr(m, "disk_write_mb_s", 0),
        "thresholds": {
            "ram_warning":  RAM_THRESHOLD_MEDIUM,
            "ram_offload":  RAM_THRESHOLD_HIGH,
            "cpu_heavy":    CPU_THRESHOLD_HIGH,
        },
    }


@app.post("/api/v1/tasks", dependencies=[Depends(verify_api_key)])
async def submit_task(task_data: dict, background_tasks: BackgroundTasks):
    """Submit a task for async processing (queued to background thread)."""
    try:
        task_id = task_data.get("id") or str(uuid.uuid4())
        task = Task(
            id=task_id,
            task_type=TaskType[task_data.get("task_type", "TEXT_GENERATION")],
            description=task_data.get("description", ""),
            input_data=task_data.get("input_data", {}),
            status=TaskStatus.QUEUED_CLOUD,
            execution_location=ExecutionLocation.CLOUD,
        )
        tasks_db[task.id] = task
        background_tasks.add_task(_process_task, task.id)
        logger.info("📥 Task %s queued: %s", task.id[:8], task.description)
        return {"task_id": task.id, "status": task.status.value, "message": "Queued"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tasks/{task_id}", dependencies=[Depends(verify_api_key)])
async def get_task(task_id: str):
    """Poll for task status + result."""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    resp = task.to_dict()
    if task.id in results_db:
        resp["result"] = results_db[task.id]
    return resp


@app.get("/api/v1/tasks", dependencies=[Depends(verify_api_key)])
async def list_tasks(status: Optional[str] = None):
    """List all tasks (last 20), optionally filtered by status."""
    tasks = list(tasks_db.values())
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    return {"total": len(tasks), "tasks": [t.to_dict() for t in tasks[-20:]]}


@app.post("/api/v1/tasks/{task_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_task(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED_CLOUD]:
        raise HTTPException(status_code=400, detail="Cannot cancel running/completed task")
    task.status = TaskStatus.FAILED
    task.error  = "Cancelled by user"
    return {"status": "cancelled"}


@app.post("/api/v1/inference", dependencies=[Depends(verify_api_key)])
async def direct_inference(data: dict):
    """Direct vLLM inference endpoint (for AMD GPU benchmarking)."""
    if not vllm_client.health_check():
        raise HTTPException(status_code=503, detail="vLLM not available")
    result = vllm_client.generate(
        prompt=data.get("prompt", ""),
        model=data.get("model", VLLM_MODEL),
        max_tokens=data.get("max_tokens", 512),
    )
    return {"response": result, "model": VLLM_MODEL}


# ─── Background task processor ───────────────────────────────────────────────

async def _process_task(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        return
    task.status     = TaskStatus.RUNNING
    task.started_at = datetime.now()
    logger.info("⚙️  Processing task %s", task_id[:8])

    try:
        if task.task_type == TaskType.TEXT_GENERATION:
            result = await _text_gen(task)
        elif task.task_type == TaskType.IMAGE_CLASSIFICATION:
            result = {"type": "image_classification", "note": "Placeholder — integrate vision model"}
        elif task.task_type == TaskType.EMBEDDING:
            result = {"type": "embedding", "dimensions": 768, "note": "Placeholder"}
        else:
            result = {"output": "Lightweight task completed locally"}

        results_db[task_id] = result
        task.result         = result
        task.status         = TaskStatus.COMPLETED
        task.completed_at   = datetime.now()
        logger.info("✅ Task %s completed", task_id[:8])

    except Exception as exc:
        task.status       = TaskStatus.FAILED
        task.error        = str(exc)
        task.completed_at = datetime.now()
        logger.error("❌ Task %s failed: %s", task_id[:8], exc)


async def _text_gen(task: Task) -> Dict[str, Any]:
    prompt     = task.input_data.get("prompt", "")
    max_tokens = task.input_data.get("max_tokens", 256)
    if not vllm_client.health_check():
        raise RuntimeError("vLLM not available")
    response = vllm_client.generate(prompt=prompt, model=VLLM_MODEL, max_tokens=max_tokens)
    return {
        "type":     "text_generation",
        "prompt":   prompt,
        "response": response or "No response",
        "model":    VLLM_MODEL,
    }


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")
