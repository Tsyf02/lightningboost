import os
import requests
from monitor import get_system_metrics

def route_task(task_type, payload):
    metrics = get_system_metrics()
    cloud_worker_url = os.environ.get("CLOUD_WORKER_URL", "http://localhost:8000")
    
    if metrics.get("status") == "CRITICAL" or task_type == "heavy_ai":
        # Route to AMD Cloud Worker
        url = cloud_worker_url if cloud_worker_url.startswith("http") else f"http://{cloud_worker_url}"
        
        try:
            response = requests.post(f"{url}/run", json={"task_type": task_type, "payload": payload})
            response.raise_for_status()
            return {
                "routed_to": "cloud", 
                "status": "success", 
                "result": response.json()
            }
        except Exception as e:
            return {
                "routed_to": "cloud", 
                "status": "error", 
                "error": str(e)
            }
    else:
        # Process locally
        return {
            "routed_to": "local", 
            "status": "success", 
            "result": "Task executed locally"
        }
