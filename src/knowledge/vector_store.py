"""Vector Database Abstraction for Phase 3."""

import json
import logging
import os
import pickle
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    created_at: str = ""


@dataclass
class VectorSearchResult:
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    vector: Optional[List[float]] = None


class VectorStore(ABC):
    @abstractmethod
    async def create_collection(self, name: str, dimensions: int) -> bool: ...

    @abstractmethod
    async def delete_collection(self, name: str) -> bool: ...

    @abstractmethod
    async def add(self, collection: str, records: List[VectorRecord]) -> int: ...

    @abstractmethod
    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]: ...

    @abstractmethod
    async def delete(self, collection: str, ids: List[str]) -> bool: ...

    @abstractmethod
    async def count(self, collection: str) -> int: ...

    @abstractmethod
    async def list_collections(self) -> List[str]: ...


class InMemoryStore(VectorStore):
    """Pure-Python fallback vector store when FAISS is not available."""

    def __init__(self):
        self._collections: Dict[str, List[VectorRecord]] = {}

    async def create_collection(self, name: str, dimensions: int) -> bool:
        if name not in self._collections:
            self._collections[name] = []
        return True

    async def delete_collection(self, name: str) -> bool:
        self._collections.pop(name, None)
        return True

    async def add(self, collection: str, records: List[VectorRecord]) -> int:
        if collection not in self._collections:
            self._collections[collection] = []
        self._collections[collection].extend(records)
        return len(records)

    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        records = self._collections.get(collection, [])
        if not records:
            return []
        import math
        vec = np.array(vector)
        scored = []
        for r in records:
            rvec = np.array(r.vector)
            dot = np.dot(vec, rvec)
            norm = np.linalg.norm(vec) * np.linalg.norm(rvec)
            score = float(dot / norm) if norm > 0 else 0
            if filters:
                match = all(r.metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue
            scored.append((r, score))
        scored.sort(key=lambda x: -x[1])
        return [
            VectorSearchResult(id=r.id, text=r.text, metadata=r.metadata, score=s)
            for r, s in scored[:top_k]
        ]

    async def delete(self, collection: str, ids: List[str]) -> bool:
        if collection in self._collections:
            self._collections[collection] = [r for r in self._collections[collection] if r.id not in ids]
        return True

    async def count(self, collection: str) -> int:
        return len(self._collections.get(collection, []))

    async def list_collections(self) -> List[str]:
        return list(self._collections.keys())


class FAISSStore(VectorStore):
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "data", "vectors")
        os.makedirs(self.storage_path, exist_ok=True)
        self._collections: Dict[str, Any] = {}
        self._texts: Dict[str, List[Tuple[str, str, Dict]]] = {}
        self._loaded: bool = False

    def _load_index(self, name: str) -> Tuple[Any, int]:
        index_path = os.path.join(self.storage_path, f"{name}.index")
        meta_path = os.path.join(self.storage_path, f"{name}.meta")
        if os.path.exists(index_path):
            try:
                import faiss
                index = faiss.read_index(index_path)
                if os.path.exists(meta_path):
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    self._texts[name] = [(m["id"], m["text"], m.get("metadata", {})) for m in meta]
                    self._collections[name] = index
                    return index, index.ntotal
            except Exception as e:
                logger.error(f"Failed to load FAISS index {name}: {e}")
        return None, 0

    async def create_collection(self, name: str, dimensions: int) -> bool:
        try:
            import faiss
            index = faiss.IndexFlatIP(dimensions)
            self._collections[name] = index
            self._texts[name] = []
            logger.info(f"Created FAISS collection {name} with dim {dimensions}")
            return True
        except ImportError:
            logger.error("faiss not available, use InMemoryStore instead")
            return False
        except Exception as e:
            logger.error(f"Failed to create FAISS collection {name}: {e}")
            return False

    async def delete_collection(self, name: str) -> bool:
        if name in self._collections:
            del self._collections[name]
        if name in self._texts:
            del self._texts[name]
        for ext in ['.index', '.meta']:
            fpath = os.path.join(self.storage_path, f"{name}{ext}")
            if os.path.exists(fpath):
                os.remove(fpath)
        return True

    async def add(self, collection: str, records: List[VectorRecord]) -> int:
        if collection not in self._collections:
            dims = len(records[0].vector) if records else 768
            await self.create_collection(collection, dims)

        index = self._collections.get(collection)
        if index is None:
            return 0

        vectors = np.array([r.vector for r in records]).astype(np.float32)
        if len(vectors.shape) == 1:
            vectors = vectors.reshape(1, -1)

        index.add(vectors)
        if collection not in self._texts:
            self._texts[collection] = []
        for r in records:
            self._texts[collection].append((r.id, r.text, r.metadata))

        self._save_index(collection)
        return len(records)

    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        if collection not in self._collections:
            self._load_index(collection)
        index = self._collections.get(collection)
        if index is None or index.ntotal == 0:
            return []

        query = np.array([vector]).astype(np.float32)
        scores, indices = index.search(query, min(top_k, index.ntotal))

        results = []
        texts = self._texts.get(collection, [])
        for i, idx in enumerate(indices[0]):
            if idx < len(texts):
                doc_id, doc_text, doc_meta = texts[idx]
                if filters:
                    match = all(doc_meta.get(k) == v for k, v in filters.items())
                    if not match:
                        continue
                results.append(VectorSearchResult(
                    id=doc_id, text=doc_text,
                    metadata=doc_meta, score=float(scores[0][i]),
                ))
        return results

    async def delete(self, collection: str, ids: List[str]) -> bool:
        if collection in self._texts:
            self._texts[collection] = [(i, t, m) for i, t, m in self._texts[collection] if i not in ids]
        return True

    async def count(self, collection: str) -> int:
        if collection in self._collections:
            return self._collections[collection].ntotal
        idx, cnt = self._load_index(collection)
        return cnt

    async def list_collections(self) -> List[str]:
        collections = []
        for f in os.listdir(self.storage_path):
            if f.endswith('.index'):
                collections.append(f[:-6])
        return list(set(collections))

    def _save_index(self, name: str):
        try:
            index = self._collections.get(name)
            if index is None:
                return
            import faiss
            faiss.write_index(index, os.path.join(self.storage_path, f"{name}.index"))
            with open(os.path.join(self.storage_path, f"{name}.meta"), 'w') as f:
                json.dump([{"id": i, "text": t, "metadata": m} for i, t, m in self._texts.get(name, [])], f)
        except Exception as e:
            logger.error(f"Failed to save FAISS index {name}: {e}")


class ChromaStore(VectorStore):
    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
        os.makedirs(self.persist_dir, exist_ok=True)
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(path=self.persist_dir)
            except ImportError:
                logger.error("chromadb not available")
                raise
        return self._client

    async def create_collection(self, name: str, dimensions: int) -> bool:
        try:
            client = await self._get_client()
            client.get_or_create_collection(name=name)
            return True
        except Exception as e:
            logger.error(f"Chroma create collection {name}: {e}")
            return False

    async def delete_collection(self, name: str) -> bool:
        try:
            client = await self._get_client()
            client.delete_collection(name=name)
            return True
        except Exception as e:
            logger.error(f"Chroma delete collection {name}: {e}")
            return False

    async def add(self, collection: str, records: List[VectorRecord]) -> int:
        try:
            client = await self._get_client()
            coll = client.get_or_create_collection(name=collection)
            ids = [r.id for r in records]
            texts = [r.text for r in records]
            metas = [{**r.metadata, "created_at": r.created_at} for r in records]
            vectors = [r.vector for r in records]
            coll.add(ids=ids, documents=texts, metadatas=metas, embeddings=vectors)
            return len(records)
        except Exception as e:
            logger.error(f"Chroma add failed: {e}")
            return 0

    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        try:
            client = await self._get_client()
            coll = client.get_or_create_collection(name=collection)
            where = filters or None
            results = coll.query(query_embeddings=[vector], n_results=top_k, where=where)
            items = []
            for i in range(len(results['ids'][0])):
                items.append(VectorSearchResult(
                    id=results['ids'][0][i],
                    text=results['documents'][0][i] if results.get('documents') else "",
                    metadata=results['metadatas'][0][i] if results.get('metadatas') else {},
                    score=results['distances'][0][i] if results.get('distances') else 0.0,
                ))
            return items
        except Exception as e:
            logger.error(f"Chroma search failed: {e}")
            return []

    async def delete(self, collection: str, ids: List[str]) -> bool:
        try:
            client = await self._get_client()
            coll = client.get_or_create_collection(name=collection)
            coll.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Chroma delete failed: {e}")
            return False

    async def count(self, collection: str) -> int:
        try:
            client = await self._get_client()
            coll = client.get_or_create_collection(name=collection)
            return coll.count()
        except Exception:
            return 0

    async def list_collections(self) -> List[str]:
        try:
            client = await self._get_client()
            return [c.name for c in client.list_collections()]
        except Exception:
            return []


class QdrantStore(VectorStore):
    def __init__(self, host: str = "localhost", port: int = 6333, api_key: str = ""):
        self.host = host
        self.port = port
        self.api_key = api_key
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(host=self.host, port=self.port, api_key=self.api_key)
            except ImportError:
                logger.error("qdrant-client not available")
                raise
        return self._client

    async def create_collection(self, name: str, dimensions: int) -> bool:
        try:
            from qdrant_client.http.models import VectorParams, Distance
            client = await self._get_client()
            client.recreate_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )
            return True
        except Exception as e:
            logger.error(f"Qdrant create collection {name}: {e}")
            return False

    async def delete_collection(self, name: str) -> bool:
        try:
            client = await self._get_client()
            client.delete_collection(collection_name=name)
            return True
        except Exception as e:
            logger.error(f"Qdrant delete collection {name}: {e}")
            return False

    async def add(self, collection: str, records: List[VectorRecord]) -> int:
        try:
            from qdrant_client.http.models import PointStruct
            client = await self._get_client()
            points = [
                PointStruct(
                    id=hash(r.id) % (2**63),
                    vector=r.vector,
                    payload={"text": r.text, "metadata": r.metadata, "doc_id": r.id},
                )
                for r in records
            ]
            client.upsert(collection_name=collection, points=points)
            return len(points)
        except Exception as e:
            logger.error(f"Qdrant add failed: {e}")
            return 0

    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        try:
            client = await self._get_client()
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            qfilter = None
            if filters:
                conditions = [FieldCondition(key=f"metadata.{k}", match=MatchValue(value=v)) for k, v in filters.items()]
                qfilter = Filter(must=conditions)
            results = client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                query_filter=qfilter,
            )
            return [
                VectorSearchResult(
                    id=r.payload.get("doc_id", str(r.id)),
                    text=r.payload.get("text", ""),
                    metadata=r.payload.get("metadata", {}),
                    score=r.score,
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    async def delete(self, collection: str, ids: List[str]) -> bool:
        try:
            client = await self._get_client()
            hashes = [hash(i) % (2**63) for i in ids]
            client.delete(collection_name=collection, points_selector=hashes)
            return True
        except Exception:
            return False

    async def count(self, collection: str) -> int:
        try:
            client = await self._get_client()
            return client.count(collection_name=collection).count
        except Exception:
            return 0

    async def list_collections(self) -> List[str]:
        try:
            client = await self._get_client()
            return [c.name for c in client.get_collections().collections]
        except Exception:
            return []


class PgvectorStore(VectorStore):
    def __init__(self, connection_string: str = ""):
        self.connection_string = connection_string

    async def _execute(self, query: str, params: tuple = None):
        try:
            import psycopg2
            conn = psycopg2.connect(self.connection_string)
            cur = conn.cursor()
            cur.execute(query, params or ())
            conn.commit()
            result = cur.fetchall() if cur.description else []
            cur.close()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"pgvector query failed: {e}")
            return []

    async def create_collection(self, name: str, dimensions: int) -> bool:
        try:
            await self._execute(f'CREATE EXTENSION IF NOT EXISTS vector')
            await self._execute(f'''
                CREATE TABLE IF NOT EXISTS {name} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    metadata JSONB DEFAULT '{{}}',
                    embedding vector({dimensions}),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            return True
        except Exception as e:
            logger.error(f"pgvector create collection {name}: {e}")
            return False

    async def delete_collection(self, name: str) -> bool:
        try:
            await self._execute(f'DROP TABLE IF EXISTS {name}')
            return True
        except Exception as e:
            logger.error(f"pgvector delete collection {name}: {e}")
            return False

    async def add(self, collection: str, records: List[VectorRecord]) -> int:
        import psycopg2.extras
        count = 0
        for r in records:
            try:
                vec_str = '[' + ','.join(str(v) for v in r.vector) + ']'
                await self._execute(
                    f'INSERT INTO {collection} (id, text, metadata, embedding) VALUES (%s, %s, %s, %s::vector) ON CONFLICT (id) DO UPDATE SET text=EXCLUDED.text, metadata=EXCLUDED.metadata, embedding=EXCLUDED.embedding',
                    (r.id, r.text, json.dumps(r.metadata), vec_str)
                )
                count += 1
            except Exception as e:
                logger.error(f"pgvector add failed: {e}")
        return count

    async def search(self, collection: str, vector: List[float], top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[VectorSearchResult]:
        vec_str = '[' + ','.join(str(v) for v in vector) + ']'
        filter_clause = ""
        if filters:
            conditions = [f"metadata->>'{k}' = '{v}'" for k, v in filters.items()]
            filter_clause = "WHERE " + " AND ".join(conditions)
        rows = await self._execute(
            f'SELECT id, text, metadata, 1 - (embedding <=> %s::vector) as score FROM {collection} {filter_clause} ORDER BY embedding <=> %s::vector LIMIT %s',
            (vec_str, vec_str, top_k)
        )
        return [
            VectorSearchResult(id=r[0], text=r[1], metadata=r[2], score=float(r[3]))
            for r in rows
        ]

    async def delete(self, collection: str, ids: List[str]) -> bool:
        for i in ids:
            await self._execute(f'DELETE FROM {collection} WHERE id = %s', (i,))
        return True

    async def count(self, collection: str) -> int:
        rows = await self._execute(f'SELECT COUNT(*) FROM {collection}')
        return rows[0][0] if rows else 0

    async def list_collections(self) -> List[str]:
        rows = await self._execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        return [r[0] for r in rows]


_current_store: Optional[VectorStore] = None


def get_vector_store(store_type: str = "chroma") -> VectorStore:
    global _current_store
    if _current_store is None:
        try:
            if store_type == "faiss":
                import faiss
                _current_store = FAISSStore()
            elif store_type == "qdrant":
                import qdrant_client
                _current_store = QdrantStore()
            elif store_type == "pgvector":
                from config import Config
                _current_store = PgvectorStore(Config.get_database_config().connection_string)
            else:
                import chromadb
                _current_store = ChromaStore()
        except ImportError:
            logger.warning(f"{store_type} not available, falling back to InMemoryStore")
            _current_store = InMemoryStore()
    return _current_store


def set_vector_store(store: VectorStore):
    global _current_store
    _current_store = store
