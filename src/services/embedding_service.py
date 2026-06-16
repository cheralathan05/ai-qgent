"""Embedding service wrapper for nomic-embed-text."""

import json
import logging
from typing import Dict, Any, List
import httpx
from config import Config

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    pass


class EmbeddingService:
    """Local embedding service.
    Uses Ollama model deployment for nomic-embed-text.
    """

    def __init__(self, host: str, port: int, model: str, timeout_seconds: int = 60):
        self.host = host
        self.port = port
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = f"http://{self.host}:{self.port}"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                json={"model": self.model, "input": texts},
            )
            if response.status_code != 200:
                raise EmbeddingServiceError(f"Embedding request failed: {response.status_code} {response.text}")
            result = response.json()
            if "data" not in result:
                raise EmbeddingServiceError("Invalid embedding response")
            return [item["embedding"] for item in result["data"]]


embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global embedding_service
    if embedding_service is None:
        config = Config.get_ollama_config()
        embedding_service = EmbeddingService(
            host=config.host,
            port=config.port,
            model="nomic-embed-text",
            timeout_seconds=config.timeout,
        )
    return embedding_service
