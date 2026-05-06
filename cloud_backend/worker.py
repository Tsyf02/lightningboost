"""
Worker module for background task processing
Can be deployed as separate service
"""
import logging
import asyncio
import time
from typing import Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.client import VLLMClient
from shared.config import VLLM_MODEL, LOCAL_TASK_TIMEOUT

logger = logging.getLogger(__name__)


class TaskWorker:
    """Background task worker"""

    def __init__(self, vllm_client: Optional[VLLMClient] = None):
        self.vllm_client = vllm_client or VLLMClient()
        self.processing = False

    async def process_text_task(self, prompt: str, max_tokens: int = 256) -> str:
        """Process text generation asynchronously"""
        try:
            result = self.vllm_client.generate(
                prompt=prompt,
                model=VLLM_MODEL,
                max_tokens=max_tokens
            )
            return result or "Generation failed"
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            raise

    async def process_batch(self, prompts: list, max_tokens: int = 256) -> list:
        """Process multiple prompts"""
        tasks = [
            self.process_text_task(prompt, max_tokens)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def start_worker(self, check_interval: int = 5):
        """Start worker loop (for standalone deployment)"""
        logger.info("🔄 TaskWorker starting...")
        self.processing = True
        
        try:
            while self.processing:
                # Placeholder for task queue checking
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Worker stopped")
            self.processing = False

    def stop_worker(self):
        """Stop the worker"""
        self.processing = False
        logger.info("Worker stopping...")
