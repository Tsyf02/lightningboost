# LightningBoost Setup & Deployment Guide

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for cloud deployment)
- 8GB+ RAM recommended
- AMD GPU (optional, for cloud vLLM)

### Local Development Setup

1. **Clone and navigate to project**
```bash
cd MeowMission-LightningBoost
```

2. **Create Python virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
# Install all component requirements
pip install -r cloud_backend/requirements.txt
pip install -r local_agent/requirements.txt
pip install -r frontend/requirements.txt
```

4. **Run local agent (System monitor)**
```bash
python local_agent/main.py
```

5. **In a new terminal, run cloud backend**
```bash
python cloud_backend/server.py
# Runs on http://localhost:8000
```

6. **In another terminal, run frontend**
```bash
streamlit run frontend/app.py
# Opens http://localhost:8501
```

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- AMD GPU with ROCm (for vLLM)

### Deployment Steps

1. **Navigate to infrastructure directory**
```bash
cd infra
```

2. **Build and start services**
```bash
docker-compose up -d
```

Services will be available at:
- Frontend: http://localhost:8501
- Cloud Backend API: http://localhost:8000
- vLLM Endpoint: http://localhost:8001

3. **Check service status**
```bash
docker-compose ps
```

4. **View logs**
```bash
docker-compose logs -f
# Or specific service
docker-compose logs -f cloud-backend
```

5. **Stop services**
```bash
docker-compose down
```

## Cloud Deployment (AMD Developer Cloud)

### Setup on AMD Cloud Instance

1. **SSH into instance**
```bash
ssh root@<instance-ip>
```

2. **Install Docker**
```bash
# Ubuntu/Debian
apt-get update && apt-get install -y docker.io docker-compose
systemctl start docker
```

3. **Clone repository**
```bash
git clone <your-repo-url>
cd MeowMission-LightningBoost
```

4. **Deploy**
```bash
cd infra
docker-compose up -d
```

5. **Configure firewall**
```bash
ufw allow 8000
ufw allow 8501
ufw allow 8001
```

6. **Access remotely**
```
http://<instance-ip>:8501  (Frontend)
http://<instance-ip>:8000  (API)
```

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Cloud Backend
CLOUD_HOST=0.0.0.0
CLOUD_PORT=8000
CLOUD_BASE_URL=http://localhost:8000

# vLLM
VLLM_BASE_URL=http://localhost:8001
VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
VLLM_TIMEOUT=120

# Local Agent
RAM_THRESHOLD_HIGH=80
RAM_THRESHOLD_MEDIUM=60
MIN_LOCAL_RAM_MB=500
MONITOR_INTERVAL=2

# Frontend
FRONTEND_HOST=0.0.0.0
FRONTEND_PORT=8501
```

### Configuration Files

- **`shared/config.py`**: Central configuration
- **`cloud_backend/requirements.txt`**: Backend dependencies
- **`frontend/requirements.txt`**: Frontend dependencies
- **`local_agent/requirements.txt`**: Local agent dependencies

## Running Demos

### Demo Script
```bash
python docs/demo.py
```

Tests:
- System monitoring
- Task routing logic
- AI recommendations
- Cloud connectivity

## Testing

### Unit Tests (Future)
```bash
pytest tests/
```

### Integration Testing

1. **Test local monitoring**
```bash
python -c "from local_agent.monitor import SystemMonitor; m = SystemMonitor(); print(m.get_current_metrics())"
```

2. **Test cloud backend**
```bash
curl http://localhost:8000/health
```

3. **Test vLLM**
```bash
curl http://localhost:8001/v1/models
```

4. **Submit test task**
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "TEXT_GENERATION",
    "description": "Test prompt",
    "input_data": {"prompt": "Hello"}
  }'
```

## Troubleshooting

### Local Agent Issues

**Problem**: `psutil` import error
```bash
# Solution: Install psutil
pip install psutil
```

**Problem**: High CPU usage in monitoring
```python
# Solution: Increase MONITOR_INTERVAL in config.py
MONITOR_INTERVAL = 5  # Increase from 2
```

### Cloud Backend Issues

**Problem**: "vLLM not available"
```bash
# Ensure vLLM is running
docker-compose up vllm
```

**Problem**: Port 8000 already in use
```bash
# Change port in config or kill process
lsof -i :8000
kill -9 <pid>
```

### Frontend Issues

**Problem**: "Connection refused" to backend
```bash
# Check if backend is running
curl http://localhost:8000/health
```

**Problem**: Streamlit port conflict
```bash
# Use custom port
streamlit run frontend/app.py --server.port=8502
```

## Performance Tuning

### For Low-RAM Systems (< 4GB)

```python
# shared/config.py
RAM_THRESHOLD_HIGH = 70
MIN_LOCAL_RAM_MB = 200
MONITOR_INTERVAL = 5
```

### For High-Performance Systems

```python
# shared/config.py
RAM_THRESHOLD_HIGH = 90
MIN_LOCAL_RAM_MB = 1000
MONITOR_INTERVAL = 1
```

### vLLM GPU Optimization

```yaml
# In docker-compose.yml
environment:
  - CUDA_VISIBLE_DEVICES=0
  - FLASH_ATTN=true
  - QUANTIZATION=awq  # For faster inference
```

## Monitoring & Logs

### Centralized Logging (Future)
```bash
# View all logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Specific service
docker-compose logs cloud-backend
```

### Metrics Export (Future)
```bash
# Prometheus endpoint
http://localhost:9090/metrics
```

## Scaling

### Horizontal Scaling

1. **Multiple frontend instances** (behind load balancer)
2. **Multiple backend instances** (with shared database)
3. **Multiple vLLM workers** (task distribution)

### Vertical Scaling

```bash
# Increase vLLM memory
docker-compose up vllm -e VLLM_GPU_MEMORY_UTILIZATION=0.95
```

## Backup & Recovery

### Backup Task Database
```bash
# Future: When database is implemented
docker-compose exec cloud-backend pg_dump > backup.sql
```

### Recovery
```bash
# Future implementation
docker-compose exec -T cloud-backend psql < backup.sql
```

## Security Hardening

1. **Enable authentication**
```python
# Future: API key middleware
@app.middleware("http")
async def validate_api_key(request, call_next):
    if request.headers.get("X-API-Key") != os.getenv("API_KEY"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
```

2. **HTTPS setup**
```bash
# Generate SSL certificates
certbot certonly --standalone -d yourdomain.com

# Update docker-compose to use SSL
```

3. **Rate limiting**
```python
# Future: Add slowapi middleware
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
```

## Support & Issues

1. Check logs: `docker-compose logs`
2. Review [ARCHITECTURE.md](ARCHITECTURE.md)
3. Run `docs/demo.py` to verify setup
4. Check GitHub issues (if applicable)

## Next Steps

- [ ] Set up continuous deployment (GitHub Actions)
- [ ] Configure monitoring dashboard (Grafana)
- [ ] Implement payment integration
- [ ] Add model fine-tuning capability
- [ ] Create Kubernetes deployment manifests
