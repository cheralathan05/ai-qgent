"""Index Manager for Phase 3 - tracks documents, chunks, and embeddings."""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    document_id: str = ""
    file_path: str = ""
    chunk_index: int = 0
    embedding_id: str = ""


@dataclass
class IndexedDocument:
    id: str
    file_name: str
    file_path: str
    source_type: str
    source_name: str
    mime_type: str
    file_size: int
    chunk_count: int = 0
    created_at: str = ""
    modified_at: str = ""
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class IndexManager:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "data", "index")
        os.makedirs(self.storage_path, exist_ok=True)
        self._documents: Dict[str, IndexedDocument] = {}
        self._chunks: Dict[str, Chunk] = {}
        self._doc_path = os.path.join(self.storage_path, "documents.json")
        self._chunk_path = os.path.join(self.storage_path, "chunks.json")
        self._load()

    def _load(self):
        try:
            if os.path.exists(self._doc_path):
                with open(self._doc_path, 'r') as f:
                    data = json.load(f)
                    for d in data:
                        doc = IndexedDocument(**d)
                        self._documents[doc.id] = doc
            if os.path.exists(self._chunk_path):
                with open(self._chunk_path, 'r') as f:
                    data = json.load(f)
                    for c in data:
                        chunk = Chunk(**c)
                        self._chunks[chunk.id] = chunk
            logger.info(f"Loaded {len(self._documents)} documents, {len(self._chunks)} chunks")
        except Exception as e:
            logger.warning(f"Failed to load index: {e}")

    def _save(self):
        try:
            with open(self._doc_path, 'w') as f:
                json.dump([asdict(d) for d in self._documents.values()], f, default=str)
            with open(self._chunk_path, 'w') as f:
                json.dump([asdict(c) for c in self._chunks.values()], f, default=str)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def add_document(self, metadata: Dict[str, Any]) -> IndexedDocument:
        doc = IndexedDocument(
            id=metadata.get("document_id", metadata.get("id", "")),
            file_name=metadata.get("file_name", ""),
            file_path=metadata.get("file_path", ""),
            source_type=metadata.get("source_type", ""),
            source_name=metadata.get("source_name", ""),
            mime_type=metadata.get("mime_type", ""),
            file_size=metadata.get("file_size", 0),
            checksum=metadata.get("checksum", ""),
            metadata=metadata,
        )
        self._documents[doc.id] = doc
        self._save()
        return doc

    def add_chunk(self, chunk: Chunk):
        self._chunks[chunk.id] = chunk
        doc_id = chunk.metadata.get("document_id", chunk.document_id)
        if doc_id and doc_id in self._documents:
            self._documents[doc_id].chunk_count = sum(
                1 for c in self._chunks.values()
                if c.metadata.get("document_id") == doc_id
            )
        self._save()

    def get_document(self, doc_id: str) -> Optional[IndexedDocument]:
        return self._documents.get(doc_id)

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        return self._chunks.get(chunk_id)

    def get_all_documents(self) -> List[IndexedDocument]:
        return list(self._documents.values())

    def get_all_chunks(self) -> List[Chunk]:
        return list(self._chunks.values())

    def get_document_count(self) -> int:
        return len(self._documents)

    def get_chunk_count(self) -> int:
        return len(self._chunks)

    def search_documents(self, query: str) -> List[IndexedDocument]:
        q = query.lower()
        results = []
        for doc in self._documents.values():
            if q in doc.file_name.lower() or q in doc.source_type.lower():
                results.append(doc)
        return results

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._documents:
            del self._documents[doc_id]
            self._chunks = {k: v for k, v in self._chunks.items()
                           if v.metadata.get("document_id") != doc_id}
            self._save()
            return True
        return False

    def clear(self):
        self._documents.clear()
        self._chunks.clear()
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": len(self._documents),
            "chunks": len(self._chunks),
            "sources": list(set(d.source_type for d in self._documents.values())),
        }


_index_manager: Optional[IndexManager] = None


def get_index_manager() -> IndexManager:
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager
