# LightningBoost Backend API

This is the backend API for LightningBoost, tracking system resources and providing AI tips and task routing.

## Setup and Running Locally

1. Navigate to the `backend/` directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

The server will be available at: **http://localhost:5000**

## Running via Docker

To run the application using Docker, from the project root directory:

1. Build the Docker image:
   ```bash
   docker build -f Dockerfile.backend -t lightningboost-backend .
   ```
2. Run the container:
   ```bash
   docker run -p 5000:5000 lightningboost-backend
   ```

## API Endpoints

### 1. Health Check
* **URL**: `/health` or `/`
* **Method**: `GET`
* **Response Payload**:
  ```json
  {
    "status": "active",
    "message": "LightningBoost API is running.",
    "endpoints": ["/metrics", "/run", "/tips"]
  }
  ```

### 2. System Metrics
* **URL**: `/metrics`
* **Method**: `GET`
* **Response Payload**:
  ```json
  {
    "cpu_percent": 12.5,
    "ram_percent": 45.2,
    "status": "OK"
  }
  ```

### 3. AI Advisor Tips
* **URL**: `/tips`
* **Method**: `GET`
* **Response Payload**:
  ```json
  [
    "System is optimal",
    "Ready for workloads"
  ]
  ```

### 4. Run Task
* **URL**: `/run`
* **Method**: `POST`
* **Request Payload**:
  ```json
  {
    "task_type": "heavy_ai",
    "payload": {
      "data": "some task data"
    }
  }
  ```
* **Response Payload (Cloud Route)**:
  ```json
  {
    "routed_to": "cloud",
    "status": "success",
    "result": { ... }
  }
  ```
* **Response Payload (Local Route)**:
  ```json
  {
    "routed_to": "local",
    "status": "success",
    "result": "Task executed locally"
  }
  ```
