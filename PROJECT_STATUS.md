


Based on the current state of the project (after the successful merging of the prototype into the main codebase, the addition of the vision features, the `psutil` threading fixes, and the transition to ROCm/AMD GPUs), here are the updated files. 

I have updated the `PROJECT_STATUS.md` to reflect the new **Qwen3** dual-model architecture, updated `shared/config.py` using your requested thread-safe Singleton template, and migrated the hardcoded prompts from the frontend into `shared/prompts.py`.

### 1. `PROJECT_STATUS.md`
```markdown
# 🚀 LightningBoost: AI-Powered Hybrid Task Router

**"From Meows to the Moon" 🐱🌕 - Boost low-RAM laptops with AMD Cloud GPUs ⚡**

## Project Summary

LightningBoost is a complete, production-ready hybrid computing platform that intelligently routes computational tasks between local devices and AMD Cloud GPU resources. It monitors system resources in real-time, makes AI-powered routing decisions, and provides a modern Dark OLED dashboard for task management.

**Perfect for**: 
- Hackathon Track 1 (AI Agents & Agentic Workflows)
- Hackathon Track 3 (Vision & Multimodal AI)

## 🧠 AI Models Architecture (AMD MI300X Optimized)
We have transitioned to a dual-model architecture optimized for AMD ROCm:
- **Primary (Vision & Text):** `Qwen3-VL-32B-Instruct-GGUF Q4_K_M` (~19GB VRAM). Used for multimodal screenshot analysis and heavy lifting. 
- **Secondary (Fast Text):** `Qwen3.5-35B-A3B-GGUF Q4_K_M` (~20GB VRAM). Used for instant, streaming responses to text-based system queries.

## What's Included & Current State

### ✅ Completed Components

#### 1. **Cloud Backend & Local Agent Integration** (`cloud_backend/` & `local_agent/`)
- **`server.py`** - FastAPI server handling real-time `psutil` data and task routing.
- **Authentication** - Implemented `X-API-Key` middleware to protect AMD cloud resources.
- **Threaded Monitor** - `monitor.py` now runs `psutil` in a background daemon thread, eliminating UI blocking/stuttering.
- **Streaming & Polling** - Supports real-time text streaming (`st.write_stream`) and async job polling for Vision tasks.

#### 2. **Frontend Dashboard** (`frontend/app.py`)
- **Modern UI** - Dark OLED design system (Space Grotesk + DM Sans).
- **Live Telemetry** - Sparklines and Plotly gauges dynamically fetching data from the backend API.
- **Multimodal Support** - Drag-and-drop screenshot analyzer linked to the Qwen3-VL-32B model.
- **Streaming AI Analysis** - Fast Qwen3.5 queries with automatic `</think>` token stripping.

#### 3. **Infrastructure & Deployment** (`infra/`)
- **ROCm Fixes** - Replaced CUDA containers with `rocm/vllm:latest` and fixed device mappings (`/dev/kfd`, `/dev/dri`, `HIP_VISIBLE_DEVICES="0"`).
- **Environment Parity** - Standardized `.env` using a strictly typed, thread-safe configuration singleton.

## Architecture Overview

```text
┌──────────────────────────┐
│   Streamlit Dashboard    │
│   (Live Gauges & Chat)   │
└────────────┬─────────────┘
             │ (REST / Streaming)
┌────────────┴──────────────────┐
│   FastAPI Cloud Backend       │
│  - X-API-Key Auth             │
│  - Threaded psutil Monitor    │
│  - Task Queue & Router        │
└────────────┬─────────┬────────┘
             │         │
    ┌────────▼─┐     ┌─▼────────┐
    │ Qwen3.5  │     │ Qwen3-VL │
    │ 35B-A3B  │     │ 32B-Inst │
    │ (Port    │     │ (Port    │
    │  8081)   │     │  8080)   │
    └──────────┘     └──────────┘
           AMD MI300X GPU
```

## Development Status

- ✅ System monitoring (Thread-safe daemon)
- ✅ Task routing engine (AI + Rule-based)
- ✅ Cloud backend API with Auth
- ✅ Frontend dashboard (Dark OLED, Plotly)
- ✅ Docker deployment (AMD ROCm ready)
- ✅ Multimodal / Vision integration
- ⏳ Database persistence (PostgreSQL)
- ⏳ Payment integration (X402)


