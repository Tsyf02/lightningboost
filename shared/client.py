"""
HTTP client for communicating with cloud backend and vLLM
"""
import requests
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator
import aiohttp
import asyncio

from config import CLOUD_BASE_URL, VLLM_BASE_URL, CLOUD_TASK_TIMEOUT

logger = logging.getLogger(__name__)


class CloudClient:
    """Client for cloud backend API"""

    def __init__(self, base_url: str = CLOUD_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def submit_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a task to the cloud backend"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/tasks",
                json=task_data,
                timeout=CLOUD_TASK_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to submit task to cloud: {e}")
            raise

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Poll for task result"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/tasks/{task_id}",
                timeout=10
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get task result: {e}")
            return None

    def get_health(self) -> bool:
        """Check if cloud backend is healthy"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def close(self):
        """Close the session"""
        self.session.close()


class VLLMClient:
    """Client for vLLM endpoint"""

    def __init__(self, base_url: str = VLLM_BASE_URL):
        self.base_url = base_url.rstrip('/')

    def list_models(self) -> Optional[list]:
        """List available models on vLLM"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/models",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except requests.RequestException as e:
            logger.error(f"Failed to list vLLM models: {e}")
            return None

    def generate(self, prompt: str, model: str, max_tokens: int = 512, **kwargs) -> Optional[str]:
        """Generate text using vLLM"""
        try:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                **kwargs
            }
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
        except requests.RequestException as e:
            logger.error(f"Failed to generate with vLLM: {e}")
            return None

    async def stream_generate(self, prompt: str, model: str, max_tokens: int = 512) -> AsyncIterator[str]:
        """Stream text generation from vLLM"""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith('data: '):
                                data_str = line_str[6:]
                                if data_str != '[DONE]':
                                    try:
                                        data = json.loads(data_str)
                                        if data.get('choices'):
                                            chunk = data['choices'][0].get('delta', {}).get('content', '')
                                            if chunk:
                                                yield chunk
                                    except json.JSONDecodeError:
                                        continue
        except Exception as e:
            logger.error(f"Failed to stream from vLLM: {e}")

    def health_check(self) -> bool:
        """Check if vLLM is healthy"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
