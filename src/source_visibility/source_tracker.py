"""Source tracking module"""

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class SourceRecord:
    id: str
    source_name: str
    source_type: str
    location: str
    content_hash: str
    retrieval_timestamp: datetime
    confidence: float
    metadata: dict


class SourceTracker:
    def __init__(self):
        self._records: dict[str, SourceRecord] = {}
        self._db_available = False
        self._db_session_factory = None
        self._init_db()

    def _init_db(self):
        try:
            from database.connection import get_db_session, SessionLocal
            if SessionLocal is not None:
                self._db_available = True
                self._db_session_factory = get_db_session
        except Exception:
            self._db_available = False

    @staticmethod
    def compute_content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def track_source(
        self,
        source_name: str,
        source_type: str,
        location: str,
        content: str,
        confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> SourceRecord:
        record = SourceRecord(
            id=str(uuid.uuid4()),
            source_name=source_name,
            source_type=source_type,
            location=location,
            content_hash=self.compute_content_hash(content),
            retrieval_timestamp=datetime.utcnow(),
            confidence=confidence,
            metadata=metadata or {},
        )
        self._records[record.id] = record
        self._persist_to_db(record)
        return record

    def _persist_to_db(self, record: SourceRecord) -> None:
        if not self._db_available:
            return
        try:
            from database.models import SourceRecord as ORMSourceRecord

            session = self._db_session_factory()
            orm_record = ORMSourceRecord(
                id=record.id,
                workflow_id="source_visibility",
                result_id=record.source_name,
                source_type=record.source_type,
                source_location=record.location,
                confidence_score=record.confidence,
                relevance_score=None,
                extracted_data={
                    "content_hash": record.content_hash,
                    "source_name": record.source_name,
                },
                metadata_json=record.metadata,
                detected_at=record.retrieval_timestamp,
            )
            session.add(orm_record)
            session.commit()
            session.close()
        except Exception:
            pass

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        return self._records.get(source_id)

    def search_sources(
        self, query: str, source_type: Optional[str] = None
    ) -> list[SourceRecord]:
        results = []
        query_lower = query.lower()
        for record in self._records.values():
            if source_type and record.source_type != source_type:
                continue
            if query_lower in record.source_name.lower() or query_lower in record.location.lower():
                results.append(record)
        return results

    def get_sources_by_type(self, source_type: str) -> list[SourceRecord]:
        return [r for r in self._records.values() if r.source_type == source_type]

    def get_all_sources(self) -> list[SourceRecord]:
        return list(self._records.values())

    def get_source_count(self) -> int:
        return len(self._records)


_source_tracker_instance: Optional[SourceTracker] = None


def get_source_tracker() -> SourceTracker:
    global _source_tracker_instance
    if _source_tracker_instance is None:
        _source_tracker_instance = SourceTracker()
    return _source_tracker_instance
