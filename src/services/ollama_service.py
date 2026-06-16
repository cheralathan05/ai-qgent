"""Ollama service wrapper for local LLM calls."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from config import Config

logger = logging.getLogger(__name__)


class OllamaServiceError(RuntimeError):
    pass


class OllamaService:
    """Wraps local Ollama HTTP API for model inference."""

    def __init__(self, host: str, port: int, model: str, timeout_seconds: int = 60):
        self.host = host
        self.port = port
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = f"http://{self.host}:{self.port}"

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            return response.status_code == 200

    async def generate(self, prompt: str, max_tokens: int = 512) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "top_p": 0.95,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/v1/completions", json=payload)
            if response.status_code != 200:
                raise OllamaServiceError(f"Ollama request failed: {response.status_code} {response.text}")
            return response.json()

    async def generate_json(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        result = await self.generate(prompt)
        if "choices" not in result or not result["choices"]:
            raise OllamaServiceError("Invalid response from Ollama")
        text = result["choices"][0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise OllamaServiceError(f"Ollama returned invalid JSON: {exc} | {text}")


ollama_service = None


def get_ollama_service() -> OllamaService:
    global ollama_service
    if ollama_service is None:
        config = Config.get_ollama_config()
        ollama_service = OllamaService(
            host=config.host,
            port=config.port,
            model=config.model,
            timeout_seconds=config.timeout,
        )
    return ollama_service
