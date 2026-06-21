"""Multi-model Embedding Engine for Phase 3."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    vector: List[float]
    dimensions: int
    model: str
    text: str


class EmbeddingEngine(ABC):
    @abstractmethod
    async def embed(self, text: str) -> List[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    def dimensions(self) -> int: ...

    @abstractmethod
    def model_name(self) -> str: ...


class LRUCache:
    """Simple thread-safe LRU cache."""
    def __init__(self, maxsize: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        if len(self._cache) >= self._maxsize:
            self._cache.clear()
        self._cache[key] = value


class OllamaEmbedding(EmbeddingEngine):
    def __init__(self, host: str = "localhost", port: int = 11434, model: str = "nomic-embed-text"):
        self.host = host
        self.port = port
        self.model_name_str = model
        self.base_url = f"http://{host}:{port}"
        self._dimensions = 768
        self._cache = LRUCache(maxsize=500)

    async def embed(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self._dimensions
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        results = await self.embed_batch([text])
        result = results[0] if results else [0.0] * self._dimensions
        self._cache.set(text, result)
        return result

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model_name_str, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("embeddings", [])
                resp = await client.post(
                    f"{self.base_url}/v1/embeddings",
                    json={"model": self.model_name_str, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return [item["embedding"] for item in data.get("data", [])]
            except Exception as e:
                logger.error(f"Ollama embedding failed: {e}")
        return [[0.0] * self._dimensions for _ in texts]

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self.model_name_str


class BGEEmbedding(EmbeddingEngine):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name_str = model_name
        self._model = None
        self._dimensions = 384

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name_str)
                self._dimensions = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not available for BGE")
                raise

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()
        if self._model is None:
            return [[0.0] * self._dimensions for _ in texts]
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, texts)
        return embeddings.tolist()

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self.model_name_str


class NomicEmbedding(EmbeddingEngine):
    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        self.model_name_str = model_name
        self._model = None
        self._dimensions = 768

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name_str, trust_remote_code=True)
                self._dimensions = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not available for Nomic")
                raise

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()
        if self._model is None:
            return [[0.0] * self._dimensions for _ in texts]
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, texts)
        return embeddings.tolist()

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self.model_name_str


class E5Embedding(EmbeddingEngine):
    def __init__(self, model_name: str = "intfloat/e5-small-v2"):
        self.model_name_str = model_name
        self._model = None
        self._dimensions = 384

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name_str)
                self._dimensions = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not available for E5")
                raise

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()
        if self._model is None:
            return [[0.0] * self._dimensions for _ in texts]
        prefixed = [f"query: {t}" for t in texts]
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, prefixed)
        return embeddings.tolist()

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self.model_name_str


class SentenceTransformerEmbedding(EmbeddingEngine):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name_str = model_name
        self._model = None
        self._dimensions = 384

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name_str)
                self._dimensions = self._model.get_sentence_embedding_dimension()
            except ImportError:
                logger.error("sentence-transformers not available")
                raise

    async def embed(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        await self._load_model()
        if self._model is None:
            return [[0.0] * self._dimensions for _ in texts]
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self._model.encode, texts)
        return embeddings.tolist()

    def dimensions(self) -> int:
        return self._dimensions

    def model_name(self) -> str:
        return self.model_name_str


_current_engine: Optional[EmbeddingEngine] = None


def get_embedding_engine(engine_type: str = "ollama") -> EmbeddingEngine:
    global _current_engine
    if _current_engine is None:
        from config import Config
        config = Config.get_ollama_config()
        if engine_type == "bge":
            _current_engine = BGEEmbedding()
        elif engine_type == "nomic":
            _current_engine = NomicEmbedding()
        elif engine_type == "e5":
            _current_engine = E5Embedding()
        elif engine_type == "sentence_transformer":
            _current_engine = SentenceTransformerEmbedding()
        else:
            _current_engine = OllamaEmbedding(
                host=config.host,
                port=config.port,
                model="nomic-embed-text",
            )
    return _current_engine


def set_embedding_engine(engine: EmbeddingEngine):
    global _current_engine
    _current_engine = engine
