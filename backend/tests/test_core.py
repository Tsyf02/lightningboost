import sys
import os
import pytest

# Add backend directory to sys.path so app can be imported properly
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_path)

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("status") == "active"
    assert "LightningBoost API is running" in data.get("message")

def test_metrics_endpoint(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    data = response.get_json()
    assert 'ram_percent' in data
    assert 'cpu_percent' in data

def test_tips_endpoint(client):
    response = client.get('/tips')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
