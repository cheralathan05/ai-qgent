"""Qwen service wrapper for local model inference."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from config import Config

logger = logging.getLogger(__name__)


class QwenServiceError(RuntimeError):
    pass


class QwenService:
    """Wraps Qwen-like model endpoints through Ollama."""

    def __init__(self, host: str, port: int, model: str, timeout_seconds: int = 60):
        self.host = host
        self.port = port
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = f"http://{self.host}:{self.port}"

    async def generate(self, prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/v1/completions",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                    "top_p": 0.95,
                },
            )
            if response.status_code != 200:
                raise QwenServiceError(f"Qwen request failed: {response.status_code} {response.text}")
            return response.json()

    async def generate_json(self, prompt: str) -> Dict[str, Any]:
        result = await self.generate(prompt)
        if "choices" not in result or not result["choices"]:
            raise QwenServiceError("Invalid response from Qwen service")
        text = result["choices"][0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise QwenServiceError(f"Qwen returned invalid JSON: {exc} | {text}")


qwen_service = None


def get_qwen_service() -> QwenService:
    global qwen_service
    if qwen_service is None:
        config = Config.get_ollama_config()
        qwen_service = QwenService(
            host=config.host,
            port=config.port,
            model="qwen3:8b",
            timeout_seconds=config.timeout,
        )
    return qwen_service
