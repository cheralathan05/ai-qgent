"""Document Ingestion Pipeline for Phase 3."""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .source_connectors import (
    SourceDocument, KnowledgeSourceConnector, get_all_connectors,
    LocalFileConnector, ensure_default_connectors,
)
from .parsers import get_parser_for_file, ParsedDocument
from .embedding_engine import get_embedding_engine
from .vector_store import get_vector_store, VectorRecord
from .indexer import IndexManager, Chunk

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    total_documents: int = 0
    indexed_documents: int = 0
    total_chunks: int = 0
    indexed_chunks: int = 0
    errors: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    time_ms: float = 0.0
    completed_at: datetime = field(default_factory=datetime.utcnow)


class DocumentIngestionPipeline:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._index_manager = None

    @property
    def index_manager(self):
        if self._index_manager is None:
            from .indexer import get_index_manager
            self._index_manager = get_index_manager()
        return self._index_manager

    def chunk_text(self, text: str, file_path: str = "", metadata: Dict = None) -> List[Chunk]:
        chunks = []
        words = text.split()
        start = 0
        chunk_index = 0

        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            chunk_id = hashlib.md5(f"{file_path}:{chunk_index}:{chunk_text[:50]}".encode()).hexdigest()

            chunk_meta = dict(metadata or {})
            chunk_meta["chunk_index"] = chunk_index
            chunk_meta["chunk_start"] = start
            chunk_meta["chunk_end"] = min(end, len(words))

            chunks.append(Chunk(
                id=chunk_id,
                text=chunk_text,
                metadata=chunk_meta,
                document_id=metadata.get("document_id", "") if metadata else "",
                file_path=file_path,
                chunk_index=chunk_index,
            ))

            chunk_index += 1
            start += self.chunk_size - self.chunk_overlap

        return chunks

    async def ingest_document(self, document: SourceDocument) -> Optional[List[Chunk]]:
        try:
            parser = get_parser_for_file(document.file_path or document.file_name)
            parsed = parser.parse(
                document.content.encode('utf-8') if isinstance(document.content, str) else document.content,
                document.file_path or document.file_name,
            )

            base_meta = {
                "document_id": document.id,
                "source_type": document.source_type,
                "source_name": document.source_name,
                "file_name": document.file_name,
                "file_path": document.file_path,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "checksum": document.checksum,
            }
            base_meta.update(document.metadata)
            if parsed.metadata:
                base_meta.update(parsed.metadata)

            doc_meta = {**base_meta, "type": "document"}
            doc_chunk = Chunk(
                id=document.id + "_doc",
                text=parsed.text,
                metadata=doc_meta,
                document_id=document.id,
                file_path=document.file_path,
                chunk_index=-1,
            )
            self.index_manager.add_document(doc_meta)

            chunks = self.chunk_text(parsed.text, document.file_path, base_meta)
            return [doc_chunk] + chunks

        except Exception as e:
            logger.error(f"Ingestion failed for {document.file_name}: {e}")
            return None

    async def ingest_documents(self, documents: List[SourceDocument]) -> IngestionResult:
        start = time.time()
        result = IngestionResult()
        result.total_documents = len(documents)
        seen_sources = set()

        all_chunks = []
        for doc in documents:
            try:
                chunks = await self.ingest_document(doc)
                if chunks:
                    all_chunks.extend(chunks)
                    result.indexed_documents += 1
                    result.total_chunks += len(chunks)
                    seen_sources.add(doc.source_type)
            except Exception as e:
                result.errors.append(f"{doc.file_name}: {e}")

        result.sources = list(seen_sources)

        if all_chunks:
            await self._index_chunks(all_chunks)
            result.indexed_chunks = len(all_chunks)

        result.time_ms = (time.time() - start) * 1000
        return result

    async def _index_chunks(self, chunks: List[Chunk]):
        try:
            engine = get_embedding_engine()
            texts = [c.text for c in chunks]
            # Split into smaller batches and add timeout per batch
            batch_size = 10
            vectors = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                try:
                    batch_vectors = await asyncio.wait_for(
                        engine.embed_batch(batch),
                        timeout=120.0,
                    )
                    vectors.extend(batch_vectors)
                except asyncio.TimeoutError:
                    logger.warning(f"Embedding batch {i//batch_size} timed out, using zeros")
                    vectors.extend([[0.0] * engine.dimensions() for _ in batch])
                except Exception as e:
                    logger.warning(f"Embedding batch {i//batch_size} failed: {e}")
                    vectors.extend([[0.0] * engine.dimensions() for _ in batch])

            store = get_vector_store()
            records = []
            for chunk, vector in zip(chunks, vectors):
                records.append(VectorRecord(
                    id=chunk.id,
                    vector=vector,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    created_at=datetime.utcnow().isoformat(),
                ))
                self.index_manager.add_chunk(chunk)

            if records:
                await store.add("documents", records)
                await store.add("chunks", records)
                logger.info(f"Indexed {len(records)} chunks to vector store")
        except Exception as e:
            logger.error(f"Failed to index chunks: {e}")

    async def ingest_documents_background(self, documents: List[SourceDocument], background_tasks) -> str:
        """Run ingestion in background and return a job ID for tracking."""
        import uuid
        job_id = str(uuid.uuid4())
        self._jobs = getattr(self, '_jobs', {})
        self._jobs[job_id] = {"status": "running", "progress": 0}

        async def _run():
            try:
                result = await self.ingest_documents(documents)
                self._jobs[job_id] = {"status": "completed", "result": {
                    "indexed_documents": result.indexed_documents,
                    "total_documents": result.total_documents,
                    "total_chunks": result.total_chunks,
                    "time_ms": result.time_ms,
                    "errors": result.errors,
                }}
            except Exception as e:
                self._jobs[job_id] = {"status": "failed", "error": str(e)}

        background_tasks.add_task(_run)
        return job_id

    def get_ingestion_job(self, job_id: str) -> Optional[Dict]:
        return getattr(self, '_jobs', {}).get(job_id)

    async def run_full_ingestion(self) -> IngestionResult:
        ensure_default_connectors()
        connectors = get_all_connectors()
        all_docs = []

        for connector in connectors:
            try:
                if not connector.is_connected:
                    await connector.connect()
                if connector.is_connected:
                    files = await connector.list_files()
                    for f in files:
                        doc = await connector.read_file(f.get("id", ""))
                        if doc is None and "file_path" in f:
                            if hasattr(connector, "read_file_by_path"):
                                doc = await connector.read_file_by_path(f["file_path"])
                        if doc is not None:
                            all_docs.append(doc)
            except Exception as e:
                logger.error(f"Connector {connector.name} failed: {e}")

        if not all_docs:
            logger.warning("No documents found from any source")
            return IngestionResult()

        return await self.ingest_documents(all_docs)

    def get_status(self) -> Dict[str, Any]:
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "indexed_documents": self.index_manager.get_document_count(),
            "total_chunks": self.index_manager.get_chunk_count(),
        }


_pipeline: Optional[DocumentIngestionPipeline] = None


def get_ingestion_pipeline() -> DocumentIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentIngestionPipeline()
    return _pipeline
