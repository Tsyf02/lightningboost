"""
LightningBoost — Local Backend API
Converted from Flask → FastAPI.

Runs on the user's local machine (not cloud).
psutil here is correct — this process reads the laptop's own resources.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware




from monitor import get_system_metrics
from router import route_task
from advisor import generate_tips

app = FastAPI(title="LightningBoost Local Backend", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.get("/health")
async def health():
    return {
        "status": "active",
        "message": "LightningBoost API is running.",
        "endpoints": ["/metrics", "/run", "/tips"],
    }


@app.get("/metrics")
async def metrics():
    """Live psutil snapshot from this machine."""
    return get_system_metrics()


@app.post("/run")
async def run_task(body: dict = {}):
    """Submit a task — auto-routed local or cloud."""
    task_type = body.get("task_type", "default")
    payload   = body.get("payload", {})
    return route_task(task_type, payload)


@app.get("/tips")
async def tips():
    """AI optimization tips based on current metrics."""
    data = get_system_metrics()
    return generate_tips(data)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")