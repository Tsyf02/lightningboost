from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

from monitor import get_system_metrics
from router import route_task
from advisor import generate_tips

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def index():
    """Root endpoint to verify the API is running."""
    return jsonify({
        "status": "active",
        "message": "LightningBoost API is running.",
        "endpoints": ["/metrics", "/run", "/tips"]
    })

@app.route('/metrics', methods=['GET'])
def metrics():
    """Endpoint to get current system RAM and CPU usage."""
    data = get_system_metrics()
    return jsonify(data)

@app.route('/run', methods=['POST'])
def run_task():
    """Endpoint to execute a task, routed locally or to the cloud."""
    content = request.json or {}
    task_type = content.get('task_type', 'default')
    payload = content.get('payload', {})
    
    result = route_task(task_type, payload)
    return jsonify(result)

@app.route('/tips', methods=['GET'])
def tips():
    """Endpoint to get optimization tips based on system metrics."""
    data = get_system_metrics()
    tips_list = generate_tips(data)
    return jsonify(tips_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
