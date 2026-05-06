# 🚀 LightningBoost: AI-Powered Hybrid Task Router

**"From Meows to the Moon" 🐱🌕 - Boost low-RAM laptops with AMD Cloud GPUs ⚡**

## Project Summary

LightningBoost is a complete, production-ready hybrid computing platform that intelligently routes computational tasks between local devices and AMD Cloud GPU resources. It monitors system resources in real-time, makes AI-powered routing decisions, and provides a modern dashboard for task management.

**Perfect for**: Hackathon Track 1 (AI Agents & Agentic Workflows) + X402 Payments Challenge

## What's Included

### ✅ Completed Components

#### 1. **Local Agent** (`local_agent/`)
- **`monitor.py`** - Real-time system monitoring (RAM, CPU, Disk, Processes)
- **`router.py`** - Intelligent task routing engine (rule-based + AI-enhanced)
- **`optimizer.py`** - AI recommendations using LLM
- **`main.py`** - Main orchestrator and monitoring loop
- Real-time metrics tracking with history
- Top process identification for optimization tips

#### 2. **Cloud Backend** (`cloud_backend/`)
- **`server.py`** - FastAPI server with full REST API
- **`worker.py`** - Background task processor
- **`Dockerfile`** - Containerized deployment
- **`deploy.py`** - Deployment helper script
- Task submission, queuing, and result management
- Support for text generation, image classification, embeddings
- Health checks and status monitoring

#### 3. **Frontend Dashboard** (`frontend/`)
- **`app.py`** - Streamlit web application
- **`Dockerfile`** - Container setup
- Real-time system metrics visualization
- Task submission interface with form
- Task history and status tracking
- Configuration management
- Performance analytics and recommendations

#### 4. **Shared Infrastructure** (`shared/`)
- **`config.py`** - Central configuration with environment support
- **`models.py`** - Data models (Task, SystemMetrics, RoutingDecision)
- **`client.py`** - HTTP clients (Cloud API, vLLM)
- **`prompts.py`** - LLM prompt templates for recommendations

#### 5. **Documentation** (`docs/`)
- **`ARCHITECTURE.md`** - Complete system architecture with diagrams
- **`SETUP.md`** - Comprehensive setup and deployment guide
- **`demo.py`** - Runnable demo script
- Deployment configurations

#### 6. **Deployment** (`infra/`)
- **`docker-compose.yml`** - Full stack orchestration (vLLM + Backend + Frontend)
- **`deploy.sh`** - Bash deployment script
- Ready for AMD Developer Cloud

#### 7. **Security Updates**
- Updated Dockerfile with security patches
- System vulnerability remediation

## Architecture Overview

```
┌──────────────────────────┐
│   Streamlit Dashboard    │
│  (Port 8501)            │
└────────────┬─────────────┘
             │
┌────────────┴──────────────────┐
│   Local Agent System          │
│  - Monitor (psutil)           │
│  - Router (AI + Rules)        │
│  - Optimizer (LLM)            │
└────────────┬──────────────────┘
             │
┌────────────▼──────────────────┐
│   Cloud Backend API           │
│  (FastAPI, Port 8000)        │
└────────────┬──────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────────┐   ┌──▼──────────┐
│  vLLM GPU   │   │  Task Queue │
│  (Port 8001)│   │  Processor  │
└─────────────┘   └─────────────┘
```

## Quick Start

### 1. **Local Development (5 minutes)**

```bash
# Install dependencies
pip install -r cloud_backend/requirements.txt
pip install -r local_agent/requirements.txt
pip install -r frontend/requirements.txt

# Terminal 1: Cloud Backend
python cloud_backend/server.py

# Terminal 2: Local Agent
python local_agent/main.py

# Terminal 3: Frontend
streamlit run frontend/app.py
```

Access at: http://localhost:8501

### 2. **Docker Deployment (10 minutes)**

```bash
cd infra
docker-compose up -d

# Services available at:
# - Frontend: http://localhost:8501
# - API: http://localhost:8000
# - vLLM: http://localhost:8001
```

### 3. **AMD Cloud Deployment**

```bash
# SSH into AMD Developer Cloud instance
ssh root@<instance-ip>

# Clone and deploy
git clone <your-repo>
cd infra
docker-compose up -d

# Open ports
ufw allow 8000
ufw allow 8501

# Access via http://<instance-ip>:8501
```

## Key Features

### 🧠 **Intelligent Task Routing**
- Rule-based initial routing (memory thresholds, task type)
- AI-enhanced decisions using Llama 3.1 (8B)
- Confidence scoring for each decision
- Fallback mechanisms for reliability

### 📊 **Real-time System Monitoring**
- CPU, RAM, and Disk usage tracking
- Top process identification
- Historical metrics storage
- System health indicators

### 💡 **AI-Powered Recommendations**
- Dynamic optimization tips based on system state
- Process-specific recommendations
- Memory savings estimation
- LLM-generated user-friendly suggestions

### 🎯 **Task Management**
- Multiple task types: Text Generation, Image Classification, Embeddings, Lightweight
- Async task execution
- Real-time status tracking
- Result caching and retrieval

### 🎨 **Modern Dashboard**
- Beautiful Streamlit interface
- Live metrics visualization (Plotly charts)
- Task submission form
- Task history and analytics
- Configuration management

### ☁️ **Cloud Integration**
- RESTful API for task submission
- vLLM inference engine on AMD GPUs
- Containerized deployment (Docker Compose)
- Health checks and monitoring

## API Endpoints

```bash
# Cloud Backend
POST   /api/v1/tasks               # Submit task
GET    /api/v1/tasks/{task_id}     # Get task status
GET    /api/v1/tasks               # List tasks
POST   /api/v1/tasks/{id}/cancel   # Cancel task
POST   /api/v1/inference           # Direct inference
GET    /health                     # Health check

# vLLM
GET    /v1/models                  # List models
POST   /v1/chat/completions        # Text generation
```

## Performance Metrics

| Metric | Local | Cloud |
|--------|-------|-------|
| Task Latency | ~10ms | ~500-1000ms |
| Throughput | Limited by RAM | GPU bandwidth |
| Max Tokens | 512 (configurable) | 2048+ |
| Concurrent Tasks | Single device | Multiple workers |
| Cost per Task | $0 | $0.10-1.00 |

## Hackathon Alignment

### Track 1: AI Agents & Agentic Workflows ✅
- ✅ Intelligent decision-making agent (routing engine)
- ✅ Real-time system observation and analysis
- ✅ Autonomous task execution
- ✅ LLM integration for recommendations

### X402 Payments Challenge (Optional) 📝
- Framework ready for payment integration
- Task-based billing structure
- Cost tracking per cloud inference

## File Structure

```
MeowMission-LightningBoost/
├── cloud_backend/
│   ├── server.py           # FastAPI backend
│   ├── worker.py           # Task processor
│   ├── Dockerfile          # Container
│   ├── deploy.py           # Deployment helper
│   └── requirements.txt
├── local_agent/
│   ├── main.py             # Main orchestrator
│   ├── monitor.py          # System monitoring
│   ├── router.py           # Task routing
│   ├── optimizer.py        # AI recommendations
│   └── requirements.txt
├── frontend/
│   ├── app.py              # Streamlit UI
│   ├── Dockerfile          # Container
│   └── requirements.txt
├── shared/
│   ├── config.py           # Configuration
│   ├── models.py           # Data models
│   ├── client.py           # HTTP clients
│   └── prompts.py          # LLM prompts
├── infra/
│   ├── docker-compose.yml  # Full stack
│   └── deploy.sh           # Deployment script
├── docs/
│   ├── ARCHITECTURE.md     # System design
│   ├── SETUP.md            # Installation guide
│   └── demo.py             # Demo script
└── README.md               # This file
```

## Technology Stack

| Component | Tech |
|-----------|------|
| Local Monitoring | Python, psutil |
| Task Routing | Python, LangChain (future) |
| Cloud Backend | FastAPI, Python 3.11 |
| Inference | vLLM, AMD MI300X GPU |
| Frontend | Streamlit, Plotly |
| Container | Docker, Docker Compose |
| LLM | Meta Llama 3.1 8B |

## Development Status

- ✅ System monitoring
- ✅ Task routing engine
- ✅ Cloud backend API
- ✅ Frontend dashboard
- ✅ Docker deployment
- ✅ Documentation
- ⏳ Database persistence (PostgreSQL)
- ⏳ Advanced authentication
- ⏳ Payment integration
- ⏳ Kubernetes manifests

## Running the Demo

```bash
# Quick demo of all components
python docs/demo.py

# Tests:
# 1. System monitoring
# 2. Intelligent routing
# 3. AI recommendations
# 4. Cloud connectivity
```

## Configuration

Environment variables in `.env`:

```bash
# Backend
CLOUD_HOST=0.0.0.0
CLOUD_PORT=8000

# vLLM
VLLM_BASE_URL=http://localhost:8001
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct

# Thresholds
RAM_THRESHOLD_HIGH=80
MIN_LOCAL_RAM_MB=500

# Monitoring
MONITOR_INTERVAL=2
```

## Troubleshooting

### "vLLM not available"
- Ensure vLLM is running: `docker-compose up vllm`
- Check GPU availability: `nvidia-smi` or `rocm-smi`

### "Connection refused"
- Verify backend is running: `curl http://localhost:8000/health`
- Check port availability: `lsof -i :8000`

### "ModuleNotFoundError"
- Install dependencies: `pip install -r <module>/requirements.txt`
- Add parent dir to PYTHONPATH

## Next Steps for Hackathon

1. **Deploy to AMD Cloud** (1 hour)
   - Use tutorial VM setup
   - Run docker-compose

2. **Create Demo Video** (1-2 hours)
   - Show local monitor → routing decision → cloud execution
   - Highlight AI recommendations
   - Display task results

3. **Prepare Pitch** (1 hour)
   - Problem: Low-RAM devices lag
   - Solution: AI-powered task routing to cloud
   - Impact: Seamless performance boost
   - Tech: LLM routing, AMD GPUs

4. **Submit Deliverables**
   - GitHub repo (clean, documented)
   - Live demo URL (Streamlit on HF Space)
   - 2-min demo video
   - Pitch deck (5-7 slides)

## Resources

- 📖 [Architecture Documentation](docs/ARCHITECTURE.md)
- 🔧 [Setup & Deployment Guide](docs/SETUP.md)
- 🎯 [Demo Script](docs/demo.py)
- 🐳 [Docker Compose Config](infra/docker-compose.yml)
- 📚 [AMD Developer Program](https://developer.amd.com)
- 🤗 [HuggingFace Spaces](https://huggingface.co/spaces)

## Team Credits

**LightningBoost Team**
- AI Agent Architecture
- Cloud Backend & Deployment
- Frontend & Dashboard
- Documentation & Demo

## License

MIT License - Open for hackathon evaluation

---

**Made for AMD Developer Hackathon 2024**

"From Meows to the Moon" 🐱➡️🌕⚡
