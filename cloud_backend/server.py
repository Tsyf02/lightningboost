"""
Cloud backend server for LightningBoost
Fixes applied:
  BUG 1 - Added /analyze/stream, /analyze/vision, /job/{id}, /offload endpoints
  BUG 2 - Removed psutil; cloud stores metrics POSTed by local_agent
  BUG 3 - process_task / process_text_generation changed to sync def
           (FastAPI runs sync background tasks in threadpool, keeps event loop free)
"""
import logging
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Task, SystemMetrics
from shared.config import (
    TaskStatus, ExecutionLocation, TaskType,
    CLOUD_HOST, CLOUD_PORT, VLLM_MODEL
)
from shared.client import VLLMClient
from shared.prompts import SYSTEM_OPTIMIZATION_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LightningBoost Cloud Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory stores ──────────────────────────────────────────────────────────
tasks_db:   Dict[str, Task]         = {}
results_db: Dict[str, Dict[str, Any]] = {}
jobs_db:    Dict[str, Dict[str, Any]] = {}   # vision job store

# BUG 2 FIX: local_agent POSTs metrics here; cloud never runs psutil
latest_metrics: Dict[str, Any] = {}

# Dual-model clients (BUG 5 companion — backend knows both ports)
VL_MODEL_URL   = os.environ.get("VL_MODEL_URL",   "http://vllm-vision:8080")
TEXT_MODEL_URL = os.environ.get("TEXT_MODEL_URL",  "http://vllm-text:8081")

vllm_client = VLLMClient()   # still used for legacy /api/v1/inference


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Cloud Backend Starting (dual-model mode)...")
    for name, url in [("VL-32B", VL_MODEL_URL), ("Text-35B", TEXT_MODEL_URL)]:
        try:
            r = requests.get(f"{url}/health", timeout=3)
            logger.info(f"  {'✅' if r.ok else '⚠️'} {name}: {url}")
        except Exception:
            logger.warning(f"  ⚠️  {name} not reachable at {url}")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ── BUG 2 FIX: Metrics endpoints (no psutil on cloud) ────────────────────────

@app.post("/metrics")
async def receive_metrics(payload: dict):
    """Local agent POSTs its psutil data here."""
    global latest_metrics
    latest_metrics = {**payload, "received_at": datetime.now().isoformat()}
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics():
    """Frontend reads laptop metrics from here (not psutil on cloud)."""
    if not latest_metrics:
        return {"warning": "No metrics received from local agent yet", "data": {}}
    return latest_metrics


# ── BUG 1 FIX: /analyze/stream — streaming text via Qwen3.5 (port 8081) ──────

@app.post("/analyze/stream")
async def analyze_stream(payload: dict):
    """
    Stream tokens from fast text model (Qwen3.5-35B on port 8081).
    Frontend uses requests.post(..., stream=True) and iter_content().
    """
    prompt = payload.get("prompt", "")
    stats  = payload.get("stats", {})

    # Build context-aware prompt
    context = (
        f"System stats: RAM {stats.get('ram_pct', '?')}%, "
        f"CPU {stats.get('cpu_pct', '?')}%, "
        f"Free RAM {stats.get('ram_free_mb', '?')} MB.\n\n"
        f"User query: {prompt}"
    )

    def _token_stream():
        try:
            resp = requests.post(
                f"{TEXT_MODEL_URL}/v1/completions",
                json={
                    "model":       os.environ.get("VLLM_TEXT_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
                    "prompt":      context,
                    "max_tokens":  512,
                    "stream":      True,
                    "temperature": 0.7,
                },
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line and line.startswith(b"data: "):
                    data = line[6:]
                    if data == b"[DONE]":
                        break
                    import json
                    try:
                        chunk = json.loads(data)
                        token = chunk["choices"][0].get("text", "")
                        if token:
                            yield token.encode("utf-8")
                    except Exception:
                        continue
        except Exception as e:
            yield f"\n\n⚠️ Stream error: {e}".encode("utf-8")

    return StreamingResponse(_token_stream(), media_type="text/plain")


# ── BUG 1 FIX: /analyze/vision — queue vision job to Qwen3-VL (port 8080) ───

@app.post("/analyze/vision")
async def analyze_vision(payload: dict, background_tasks: BackgroundTasks):
    """
    Accept base64 image + prompt. Returns job_id immediately.
    Frontend polls GET /job/{job_id} for result.
    """
    job_id   = str(uuid.uuid4())
    image_b64 = payload.get("image_b64", "")
    prompt    = payload.get("prompt", "Analyze this screenshot and give optimization tips.")

    jobs_db[job_id] = {"status": "queued", "result": None, "error": None,
                       "created_at": datetime.now().isoformat()}

    # BUG 3 FIX: sync def → FastAPI runs in threadpool, event loop stays free
    background_tasks.add_task(_run_vision_job, job_id, image_b64, prompt)

    return {"job_id": job_id, "status": "queued"}


def _run_vision_job(job_id: str, image_b64: str, prompt: str):
    """Sync background task — safe to block; runs in threadpool."""
    jobs_db[job_id]["status"] = "running"
    try:
        resp = requests.post(
            f"{VL_MODEL_URL}/v1/chat/completions",
            json={
                "model": os.environ.get("VLLM_VL_MODEL", "Qwen/Qwen2-VL-72B-Instruct"),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "max_tokens": 1024,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        jobs_db[job_id].update({"status": "completed", "result": content,
                                 "completed_at": datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Vision job {job_id[:8]} failed: {e}")
        jobs_db[job_id].update({"status": "failed", "error": str(e),
                                 "completed_at": datetime.now().isoformat()})


# ── BUG 1 FIX: /job/{job_id} — polling endpoint ──────────────────────────────

@app.get("/job/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]


# ── BUG 1 FIX: /offload — general heavy task submission ──────────────────────

@app.post("/offload")
async def offload_task(payload: dict, background_tasks: BackgroundTasks):
    """
    General-purpose cloud offload. Frontend Task Offload tab uses this.
    Wraps existing /api/v1/tasks logic under the endpoint the frontend expects.
    """
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        task_type=TaskType[payload.get("task_type", "TEXT_GENERATION")],
        description=payload.get("description", ""),
        input_data=payload.get("input_data", {}),
        status=TaskStatus.QUEUED_CLOUD,
        execution_location=ExecutionLocation.CLOUD,
    )
    tasks_db[task.id] = task

    # BUG 3 FIX: sync def background task
    background_tasks.add_task(process_task, task.id)

    logger.info(f"📥 Offload task {task_id[:8]}: {task.description[:60]}")
    return {
        "task_id":           task_id,
        "status":            task.status.value,
        "estimated_seconds": 15,
        "message":           "Task queued for cloud processing",
    }


# ── Existing /api/v1/* endpoints (keep for backward compat) ──────────────────

@app.post("/api/v1/tasks")
async def submit_task(task_data: dict, background_tasks: BackgroundTasks):
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
        background_tasks.add_task(process_task, task.id)   # BUG 3 FIX: sync fn
        logger.info(f"📥 Task {task.id[:8]} submitted")
        return {"task_id": task.id, "status": task.status.value,
                "message": "Task queued for processing"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_db[task_id]
    response = task.to_dict()
    if task.id in results_db:
        response["result"] = results_db[task.id]
    return response


@app.get("/api/v1/tasks")
async def list_tasks(status: Optional[str] = None):
    tasks = list(tasks_db.values())
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    return {"total": len(tasks), "tasks": [t.to_dict() for t in tasks[-10:]]}


@app.post("/api/v1/inference")
async def run_inference(data: dict):
    try:
        prompt     = data.get("prompt", "")
        model      = data.get("model", VLLM_MODEL)
        max_tokens = data.get("max_tokens", 512)
        if not vllm_client.health_check():
            raise HTTPException(status_code=503, detail="vLLM not available")
        result = vllm_client.generate(prompt=prompt, model=model, max_tokens=max_tokens)
        return {"prompt": prompt, "response": result, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── BUG 3 FIX: sync def background tasks (threadpool, not event loop) ─────────

def process_task(task_id: str):
    """Sync — FastAPI runs this in threadpool. Blocking HTTP calls are safe here."""
    try:
        task = tasks_db.get(task_id)
        if not task:
            return
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        logger.info(f"⚙️  Processing task {task_id[:8]}")

        if task.task_type == TaskType.TEXT_GENERATION:
            result = process_text_generation(task)
        elif task.task_type == TaskType.IMAGE_CLASSIFICATION:
            result = process_image_classification(task)
        elif task.task_type == TaskType.EMBEDDING:
            result = process_embedding(task)
        else:
            result = {"output": "Task processed"}

        results_db[task_id] = result
        task.result         = result
        task.status         = TaskStatus.COMPLETED
        task.completed_at   = datetime.now()
        logger.info(f"✅ Task {task_id[:8]} completed")

    except Exception as e:
        logger.error(f"Task {task_id[:8]} failed: {e}")
        task = tasks_db.get(task_id)
        if task:
            task.status       = TaskStatus.FAILED
            task.error        = str(e)
            task.completed_at = datetime.now()


def process_text_generation(task: Task) -> Dict[str, Any]:
    """Sync — safe to block; runs in threadpool."""
    prompt     = task.input_data.get("prompt", "")
    max_tokens = task.input_data.get("max_tokens", 256)
    if not vllm_client.health_check():
        raise Exception("vLLM not available")
    response = vllm_client.generate(prompt=prompt, model=VLLM_MODEL, max_tokens=max_tokens)
    return {
        "type":     "text_generation",
        "prompt":   prompt,
        "response": response or "No response generated",
        "tokens":   len(response.split()) if response else 0,
    }


def process_image_classification(task: Task) -> Dict[str, Any]:
    image_url = task.input_data.get("image_url", "")
    return {"type": "image_classification", "image": image_url,
            "classification": "placeholder_class", "confidence": 0.95}


def process_embedding(task: Task) -> Dict[str, Any]:
    text = task.input_data.get("text", "")
    return {"type": "embedding", "text": text,
            "embedding": [0.1] * 768, "dimension": 768}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")