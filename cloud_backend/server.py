"""
Cloud backend server for LightningBoost
Handles task submission, routing, and result management
"""
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.models import Task, SystemMetrics
from shared.config import (
    TaskStatus, ExecutionLocation, TaskType,
    CLOUD_HOST, CLOUD_PORT, VLLM_MODEL
)
from shared.client import VLLMClient
from shared.prompts import SYSTEM_OPTIMIZATION_PROMPT

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="LightningBoost Cloud Backend", version="1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task storage (in production, use database)
tasks_db: Dict[str, Task] = {}
results_db: Dict[str, Dict[str, Any]] = {}

# vLLM client
vllm_client = VLLMClient()


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 Cloud Backend Starting...")
    
    # Check vLLM availability
    if vllm_client.health_check():
        models = vllm_client.list_models()
        logger.info(f"✅ vLLM Available. Models: {len(models) if models else 0}")
    else:
        logger.warning("⚠️ vLLM endpoint not available")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vllm_available": vllm_client.health_check()
    }


@app.post("/api/v1/tasks")
async def submit_task(task_data: dict, background_tasks: BackgroundTasks):
    """Submit a new task for processing"""
    try:
        task_id = task_data.get("id") or str(uuid.uuid4())
        
        # Create task object
        task = Task(
            id=task_id,
            task_type=TaskType[task_data.get("task_type", "TEXT_GENERATION")],
            description=task_data.get("description", ""),
            input_data=task_data.get("input_data", {}),
            status=TaskStatus.QUEUED_CLOUD,
            execution_location=ExecutionLocation.CLOUD
        )
        
        # Store task
        tasks_db[task.id] = task
        
        # Process in background
        background_tasks.add_task(process_task, task.id)
        
        logger.info(f"📥 Task {task.id[:8]} submitted: {task.description}")
        
        return {
            "task_id": task.id,
            "status": task.status.value,
            "message": "Task queued for processing"
        }
    
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task status and result"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    response = task.to_dict()
    
    if task.id in results_db:
        response["result"] = results_db[task.id]
    
    return response


@app.get("/api/v1/tasks")
async def list_tasks(status: Optional[str] = None):
    """List all tasks, optionally filtered by status"""
    tasks = list(tasks_db.values())
    
    if status:
        tasks = [t for t in tasks if t.status.value == status]
    
    return {
        "total": len(tasks),
        "tasks": [t.to_dict() for t in tasks[-10:]]  # Return last 10
    }


@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a task"""
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_db[task_id]
    if task.status not in [TaskStatus.PENDING, TaskStatus.QUEUED_CLOUD]:
        raise HTTPException(status_code=400, detail="Cannot cancel running/completed task")
    
    task.status = TaskStatus.FAILED
    task.error = "Cancelled by user"
    
    logger.info(f"❌ Task {task_id[:8]} cancelled")
    return {"status": "cancelled"}


@app.post("/api/v1/inference")
async def run_inference(data: dict):
    """Direct inference endpoint (for testing)"""
    try:
        prompt = data.get("prompt", "")
        model = data.get("model", VLLM_MODEL)
        max_tokens = data.get("max_tokens", 512)
        
        if not vllm_client.health_check():
            raise HTTPException(status_code=503, detail="vLLM not available")
        
        result = vllm_client.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens
        )
        
        return {
            "prompt": prompt,
            "response": result,
            "model": model
        }
    
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_task(task_id: str):
    """Process a task in the background"""
    try:
        task = tasks_db.get(task_id)
        if not task:
            return
        
        # Update status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        logger.info(f"⚙️ Processing task {task_id[:8]}")
        
        # Process based on task type
        if task.task_type == TaskType.TEXT_GENERATION:
            result = await process_text_generation(task)
        elif task.task_type == TaskType.IMAGE_CLASSIFICATION:
            result = await process_image_classification(task)
        elif task.task_type == TaskType.EMBEDDING:
            result = await process_embedding(task)
        else:
            result = {"output": "Task processed"}
        
        # Store result
        results_db[task_id] = result
        task.result = result
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        
        logger.info(f"✅ Task {task_id[:8]} completed")
    
    except Exception as e:
        logger.error(f"Task {task_id[:8]} failed: {e}")
        task = tasks_db.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()


async def process_text_generation(task: Task) -> Dict[str, Any]:
    """Process text generation task"""
    prompt = task.input_data.get("prompt", "")
    max_tokens = task.input_data.get("max_tokens", 256)
    
    if not vllm_client.health_check():
        raise Exception("vLLM not available")
    
    response = vllm_client.generate(
        prompt=prompt,
        model=VLLM_MODEL,
        max_tokens=max_tokens
    )
    
    return {
        "type": "text_generation",
        "prompt": prompt,
        "response": response or "No response generated",
        "tokens": len(response.split()) if response else 0
    }


async def process_image_classification(task: Task) -> Dict[str, Any]:
    """Process image classification task"""
    # Placeholder for image classification
    image_url = task.input_data.get("image_url", "")
    
    return {
        "type": "image_classification",
        "image": image_url,
        "classification": "placeholder_class",
        "confidence": 0.95
    }


async def process_embedding(task: Task) -> Dict[str, Any]:
    """Process embedding task"""
    text = task.input_data.get("text", "")
    
    return {
        "type": "embedding",
        "text": text,
        "embedding": [0.1] * 768,  # Placeholder 768-dim embedding
        "dimension": 768
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=CLOUD_HOST,
        port=CLOUD_PORT,
        log_level="info"
    )
