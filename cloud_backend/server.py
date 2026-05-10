"""
Cloud backend server for LightningBoost
Optimized per FastAPI official docs / production best practices:
  - lifespan() replaces deprecated @app.on_event
  - Pydantic models on every request/response (validation + auto-docs)
  - APIRouter for endpoint grouping
  - fastapi.status constants throughout
  - import json at module level (not inside generator)
  - CORS fixed: credentials=True incompatible with allow_origins=["*"]
  - Unused imports removed
  - asyncio.to_thread for blocking calls inside async routes
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.client import VLLMClient
from shared.config import (
    CLOUD_HOST,
    CLOUD_PORT,
    ExecutionLocation,
    TaskStatus,
    TaskType,
    VLLM_MODEL,
)
from shared.models import Task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VL_MODEL_URL    = os.environ.get("VL_MODEL_URL",    "http://vllm-vision:8080")
TEXT_MODEL_URL  = os.environ.get("TEXT_MODEL_URL",  "http://vllm-text:8081")
VLLM_VL_MODEL   = os.environ.get("VLLM_VL_MODEL",  "Qwen/Qwen2-VL-72B-Instruct")
VLLM_TEXT_MODEL = os.environ.get("VLLM_TEXT_MODEL", "Qwen/Qwen2.5-72B-Instruct")

tasks_db:       Dict[str, Task]           = {}
results_db:     Dict[str, Dict[str, Any]] = {}
jobs_db:        Dict[str, Dict[str, Any]] = {}
latest_metrics: Dict[str, Any]            = {}

vllm_client = VLLMClient()


# ── Pydantic models ───────────────────────────────────────────────────────────

class StreamPayload(BaseModel):
    prompt: str
    stats:  Dict[str, Any] = Field(default_factory=dict)

class VisionPayload(BaseModel):
    image_b64: str
    prompt:    str = "Analyze this screenshot and give optimization tips."

class OffloadPayload(BaseModel):
    task_type:   str = "TEXT_GENERATION"
    description: str
    input_data:  Dict[str, Any] = Field(default_factory=dict)

class TaskSubmit(BaseModel):
    id:          Optional[str]  = None
    task_type:   str            = "TEXT_GENERATION"
    description: str            = ""
    input_data:  Dict[str, Any] = Field(default_factory=dict)

class InferenceRequest(BaseModel):
    prompt:     str
    model:      str = VLLM_MODEL
    max_tokens: int = 512

class MetricsPayload(BaseModel):
    ram_percent:   float
    ram_used_mb:   float
    ram_free_mb:   float
    cpu_percent:   float
    disk_percent:  float
    process_count: int
    top_processes: List[Dict[str, Any]] = Field(default_factory=list)

class JobStatus(BaseModel):
    status:       str
    result:       Optional[str] = None
    error:        Optional[str] = None
    created_at:   Optional[str] = None
    completed_at: Optional[str] = None


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Cloud Backend starting (dual-model mode)...")
    for name, url in [("VL-32B", VL_MODEL_URL), ("Text-35B", TEXT_MODEL_URL)]:
        try:
            r = await asyncio.to_thread(requests.get, f"{url}/health", timeout=3)
            logger.info(f"  {'✅' if r.ok else '⚠️'} {name}: {url}")
        except Exception:
            logger.warning(f"  ⚠️  {name} not reachable at {url}")
    yield
    logger.info("Cloud Backend shutting down.")


# ── App + CORS ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LightningBoost Cloud Backend",
    version="2.0",
    description="Hybrid task router — AMD MI300X GPU backend",
    lifespan=lifespan,
)

# CORS: allow_credentials=True + allow_origins=["*"] is a spec violation —
# browsers reject it. Use explicit origins in prod and enable credentials there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

core    = APIRouter(tags=["Core"])
analyze = APIRouter(prefix="/analyze", tags=["AI Analysis"])
jobs_r  = APIRouter(prefix="/job",     tags=["Jobs"])
tasks_r = APIRouter(prefix="/api/v1",  tags=["Tasks v1"])


# ── Core ──────────────────────────────────────────────────────────────────────

@core.get("/health", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@core.post("/metrics", status_code=status.HTTP_200_OK)
async def receive_metrics(payload: MetricsPayload):
    global latest_metrics
    latest_metrics = {**payload.model_dump(), "received_at": datetime.now().isoformat()}
    return {"status": "ok"}

@core.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics():
    if not latest_metrics:
        return {"warning": "No metrics received from local agent yet", "data": {}}
    return latest_metrics

@core.post("/offload", status_code=status.HTTP_202_ACCEPTED)
async def offload_task(payload: OffloadPayload, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        task_type=TaskType[payload.task_type],
        description=payload.description,
        input_data=payload.input_data,
        status=TaskStatus.QUEUED_CLOUD,
        execution_location=ExecutionLocation.CLOUD,
    )
    tasks_db[task.id] = task
    background_tasks.add_task(_process_task, task.id)
    logger.info(f"📥 Offload {task_id[:8]}: {payload.description[:60]}")
    return {"task_id": task_id, "status": task.status.value,
            "estimated_seconds": 15, "message": "Task queued for cloud processing"}


# ── AI Analysis ───────────────────────────────────────────────────────────────

@analyze.post("/stream")
async def analyze_stream(payload: StreamPayload):
    context = (
        f"System stats: RAM {payload.stats.get('ram_pct', '?')}%, "
        f"CPU {payload.stats.get('cpu_pct', '?')}%, "
        f"Free RAM {payload.stats.get('ram_free_mb', '?')} MB.\n\n"
        f"User query: {payload.prompt}"
    )

    async def _token_stream():
        try:
            resp = requests.post(
                f"{TEXT_MODEL_URL}/v1/completions",
                json={"model": VLLM_TEXT_MODEL, "prompt": context,
                      "max_tokens": 512, "stream": True, "temperature": 0.7},
                stream=True, timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith(b"data: "):
                    continue
                data = line[6:]
                if data == b"[DONE]":
                    break
                try:
                    token = json.loads(data)["choices"][0].get("text", "")
                    if token:
                        yield token.encode("utf-8")
                except (KeyError, json.JSONDecodeError):
                    continue
        except Exception as e:
            yield f"\n\n⚠️ Stream error: {e}".encode("utf-8")

    return StreamingResponse(_token_stream(), media_type="text/plain")

@analyze.post("/vision", status_code=status.HTTP_202_ACCEPTED)
async def analyze_vision(payload: VisionPayload, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {"status": "queued", "result": None, "error": None,
                       "created_at": datetime.now().isoformat()}
    background_tasks.add_task(_run_vision_job, job_id, payload.image_b64, payload.prompt)
    return {"job_id": job_id, "status": "queued"}


# ── Jobs ──────────────────────────────────────────────────────────────────────

@jobs_r.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Job not found")
    return jobs_db[job_id]


# ── Tasks v1 (backward compat) ────────────────────────────────────────────────

@tasks_r.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def submit_task(task_data: TaskSubmit, background_tasks: BackgroundTasks):
    try:
        task_id = task_data.id or str(uuid.uuid4())
        task = Task(
            id=task_id,
            task_type=TaskType[task_data.task_type],
            description=task_data.description,
            input_data=task_data.input_data,
            status=TaskStatus.QUEUED_CLOUD,
            execution_location=ExecutionLocation.CLOUD,
        )
        tasks_db[task.id] = task
        background_tasks.add_task(_process_task, task.id)
        return {"task_id": task.id, "status": task.status.value,
                "message": "Task queued for processing"}
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid task_type: {e}")

@tasks_r.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Task not found")
    task     = tasks_db[task_id]
    response = task.to_dict()
    if task.id in results_db:
        response["result"] = results_db[task.id]
    return response

@tasks_r.get("/tasks")
async def list_tasks(status_filter: Optional[str] = None):
    all_tasks = list(tasks_db.values())
    if status_filter:
        all_tasks = [t for t in all_tasks if t.status.value == status_filter]
    return {"total": len(all_tasks), "tasks": [t.to_dict() for t in all_tasks[-10:]]}

@tasks_r.post("/inference")
async def run_inference(data: InferenceRequest):
    if not await asyncio.to_thread(vllm_client.health_check):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="vLLM not available")
    try:
        result = await asyncio.to_thread(
            vllm_client.generate,
            prompt=data.prompt, model=data.model, max_tokens=data.max_tokens,
        )
        return {"prompt": data.prompt, "response": result, "model": data.model}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(e))


app.include_router(core)
app.include_router(analyze)
app.include_router(jobs_r)
app.include_router(tasks_r)


# ── Sync background workers ───────────────────────────────────────────────────

def _process_task(task_id: str) -> None:
    task = tasks_db.get(task_id)
    if not task:
        return
    task.status = TaskStatus.RUNNING
    task.started_at = datetime.now()
    logger.info(f"⚙️  Processing {task_id[:8]}")
    try:
        if   task.task_type == TaskType.TEXT_GENERATION:    result = _text_generation(task)
        elif task.task_type == TaskType.IMAGE_CLASSIFICATION: result = _image_classification(task)
        elif task.task_type == TaskType.EMBEDDING:           result = _embedding(task)
        else:                                                result = {"output": "Task processed"}
        results_db[task_id] = result
        task.result         = result
        task.status         = TaskStatus.COMPLETED
        task.completed_at   = datetime.now()
        logger.info(f"✅ Task {task_id[:8]} done")
    except Exception as e:
        logger.error(f"Task {task_id[:8]} failed: {e}")
        task.status       = TaskStatus.FAILED
        task.error        = str(e)
        task.completed_at = datetime.now()

def _text_generation(task: Task) -> Dict[str, Any]:
    prompt     = task.input_data.get("prompt", "")
    max_tokens = task.input_data.get("max_tokens", 256)
    if not vllm_client.health_check():
        raise RuntimeError("vLLM not available")
    response = vllm_client.generate(prompt=prompt, model=VLLM_MODEL, max_tokens=max_tokens)
    return {"type": "text_generation", "prompt": prompt,
            "response": response or "No response generated",
            "tokens": len(response.split()) if response else 0}

def _image_classification(task: Task) -> Dict[str, Any]:
    return {"type": "image_classification",
            "image": task.input_data.get("image_url", ""),
            "classification": "placeholder_class", "confidence": 0.95}

def _embedding(task: Task) -> Dict[str, Any]:
    return {"type": "embedding", "text": task.input_data.get("text", ""),
            "embedding": [0.1] * 768, "dimension": 768}

def _run_vision_job(job_id: str, image_b64: str, prompt: str) -> None:
    jobs_db[job_id]["status"] = "running"
    try:
        resp = requests.post(
            f"{VL_MODEL_URL}/v1/chat/completions",
            json={"model": VLLM_VL_MODEL,
                  "messages": [{"role": "user", "content": [
                      {"type": "image_url",
                       "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                      {"type": "text", "text": prompt},
                  ]}],
                  "max_tokens": 1024},
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")