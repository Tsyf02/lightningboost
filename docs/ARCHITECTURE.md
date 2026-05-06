# LightningBoost Architecture

## System Overview

LightningBoost is an AI-powered hybrid task router that intelligently distributes computational tasks between local devices and cloud GPU resources. It monitors system resources in real-time and makes smart offloading decisions.

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (Streamlit)               │
│                   - Monitor dashboard                        │
│                   - Task submission                          │
│                   - Performance analytics                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
┌────────▼─────┐  ┌────▼─────┐  ┌───▼──────────┐
│ Local Agent  │  │  Router   │  │   Monitor    │
│              │  │  Engine   │  │  Dashboard   │
│ - Monitor    │  │           │  │              │
│ - Optimize   │  │ - AI Route│  │ - Real-time  │
│ - Cache      │  │ - Fallback│  │   metrics    │
└────────┬─────┘  └────┬─────┘  └───┬──────────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   Cloud Backend (FastAPI)  │
         │                            │
         │ - Task Queue              │
         │ - Load Balancer           │
         │ - Result Manager          │
         └────────────┬──────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
    ┌────▼─────┐ ┌────▼─────┐ ┌──▼────────┐
    │  vLLM    │ │  Task    │ │ Model     │
    │ Inference│ │ Processor│ │ Cache     │
    │          │ │          │ │           │
    │ AMD GPU  │ │ MI300X   │ │ HuggingFace
    └──────────┘ └──────────┘ └───────────┘
```

## Component Breakdown

### 1. **Local Agent** (`local_agent/`)

Runs on user's device, continuously monitors system resources.

#### Files:
- **`monitor.py`**: Real-time system metrics collection
  - RAM/CPU/Disk monitoring via `psutil`
  - Process tracking
  - Historical metrics storage

- **`optimizer.py`**: AI-powered recommendations
  - Analyzes system health
  - Generates optimization tips via vLLM
  - Tracks memory efficiency

- **`router.py`**: Intelligent task routing
  - Rule-based initial routing decisions
  - AI-enhanced routing using LLM
  - Confidence scoring

- **`main.py`**: Main orchestrator
  - Monitoring loop
  - Integration of all components
  - Cloud communication

### 2. **Cloud Backend** (`cloud_backend/`)

RESTful API handling task submission, queuing, and execution.

#### Files:
- **`server.py`**: FastAPI application
  - Task submission endpoint
  - Status polling
  - Result retrieval
  - Direct inference endpoint

- **`worker.py`**: Background task processor
  - Async task execution
  - Batch processing
  - Result caching

- **`Dockerfile`**: Container setup for cloud deployment

### 3. **Frontend** (`frontend/`)

Streamlit dashboard for visualization and interaction.

#### Features:
- Real-time system metrics dashboard
- Task submission interface
- Task history and results
- Performance analytics
- Configuration settings

### 4. **Shared Components** (`shared/`)

Shared across all components.

- **`config.py`**: Configuration & constants
- **`models.py`**: Data models (Task, SystemMetrics, etc.)
- **`client.py`**: HTTP clients for cloud/vLLM communication
- **`prompts.py`**: LLM prompt templates

## Routing Algorithm

```python
Input: Task, SystemMetrics
Output: ExecutionLocation (LOCAL or CLOUD)

1. Check if memory is critically low
   → Route to CLOUD (confidence: 0.95)

2. Check task type
   - TEXT_GENERATION: 
     → CLOUD if RAM > 60% or CPU > 70%
     → LOCAL otherwise
   - IMAGE_CLASSIFICATION: 
     → CLOUD (better suited for GPU)
   - EMBEDDING: 
     → CLOUD if available, else LOCAL
   - LIGHTWEIGHT: 
     → LOCAL always

3. Fallback: Check available resources
   → LOCAL if RAM available, else CLOUD

4. Optional AI Refinement:
   → Use LLM to validate decision
   → Adjust confidence based on feedback
```

## Task Flow

```
User Input
    │
    ├─→ [Local Agent] ──→ [Router] ──→ Routing Decision
    │                                       │
    │                                  CLOUD?
    │                                  /    \
    │                                YES     NO
    │                                /        \
    │     [Cloud Backend]    /         \     [Local Exec]
    │     [Queue Task]      /           \         │
    │     [Execute]        /             \        │
    │     [Return]        /               \       │
    │         │         /                 \      │
    │         └────────┴───────────────────┴─────┘
    │                  │
    └──────────────[Result Aggregation]
                      │
                 [Display UI]
```

## Data Models

### Task
```python
- id: UUID
- task_type: ENUM (text_gen, image_class, embedding, lightweight)
- description: str
- input_data: dict
- status: ENUM (pending, running, completed, failed)
- execution_location: ENUM (local, cloud, hybrid)
- result: dict
- timestamps: created, started, completed
```

### SystemMetrics
```python
- timestamp: datetime
- ram_percent: float (0-100)
- ram_used_mb: float
- ram_available_mb: float
- cpu_percent: float
- disk_percent: float
- process_count: int
- top_processes: list
```

### RoutingDecision
```python
- task_id: UUID
- location: ENUM (local, cloud)
- confidence: float (0-1)
- reasoning: str
- estimated_times: local_sec, cloud_sec
```

## API Endpoints

### Cloud Backend

```
POST   /api/v1/tasks              - Submit task
GET    /api/v1/tasks/{task_id}    - Get task status
GET    /api/v1/tasks              - List tasks
POST   /api/v1/tasks/{id}/cancel  - Cancel task
POST   /api/v1/inference          - Direct inference
GET    /health                    - Health check
```

### vLLM

```
GET    /v1/models                 - List models
POST   /v1/chat/completions       - Text generation
GET    /health                    - Health check
```

## Deployment Architecture

### Local Deployment
```
machine1 (8GB RAM)
├─ local_agent/
├─ frontend/ (Streamlit)
└─ cloud_backend/ (if available)

cloud (AMD MI300X)
├─ vllm_endpoint
├─ cloud_backend
└─ database
```

### Docker-Compose Setup
```
docker-compose up
├─ vllm service (GPU)
├─ cloud-backend (API)
└─ frontend (UI)
```

## Performance Characteristics

| Metric | Local | Cloud |
|--------|-------|-------|
| Latency | ~10ms | ~500-1000ms |
| Throughput | Limited by RAM | GPU bandwidth |
| Cost | $0 | $0.10-1.00 per task |
| Scaling | Single device | Unlimited |
| Cold start | Instant | ~2-5sec |

## Security Considerations

1. **Authentication**: API key for cloud backend (future)
2. **Data Privacy**: Tasks contain potentially sensitive data
3. **Rate Limiting**: Prevent abuse of cloud resources
4. **Encryption**: HTTPS for cloud communication (future)
5. **Resource Limits**: Max token length, timeout settings

## Future Enhancements

- [ ] Database persistence (PostgreSQL)
- [ ] Distributed cache (Redis)
- [ ] Multi-cloud support (GCP, AWS)
- [ ] Advanced scheduling (task priorities)
- [ ] Payment integration (X402)
- [ ] WebSocket support for real-time updates
- [ ] Kubernetes deployment templates
- [ ] Advanced observability (Prometheus, Grafana)
