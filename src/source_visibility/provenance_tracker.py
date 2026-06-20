"""Document provenance module"""

import hashlib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ProvenanceRecord:
    id: str
    document_name: str
    file_path: str
    source_location: str
    retrieval_method: str
    retrieved_at: datetime
    checksum: str
    file_size: int
    metadata: dict


class ProvenanceTracker:
    def __init__(self):
        self._records: dict[str, ProvenanceRecord] = {}

    def track_document(
        self,
        document_name: str,
        file_path: str,
        source_location: str,
        retrieval_method: str = "local_file",
        metadata: Optional[dict] = None,
    ) -> ProvenanceRecord:
        checksum = ""
        file_size = 0
        if os.path.isfile(file_path):
            checksum = self._compute_file_checksum(file_path)
            file_size = os.path.getsize(file_path)

        record = ProvenanceRecord(
            id=str(uuid.uuid4()),
            document_name=document_name,
            file_path=file_path,
            source_location=source_location,
            retrieval_method=retrieval_method,
            retrieved_at=datetime.utcnow(),
            checksum=checksum,
            file_size=file_size,
            metadata=metadata or {},
        )
        self._records[record.id] = record
        return record

    @staticmethod
    def _compute_file_checksum(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_provenance(self, document_id: str) -> Optional[ProvenanceRecord]:
        return self._records.get(document_id)

    def find_documents(self, query: str) -> list[ProvenanceRecord]:
        query_lower = query.lower()
        return [
            r
            for r in self._records.values()
            if query_lower in r.document_name.lower()
            or query_lower in r.file_path.lower()
        ]

    def get_recent_documents(self, limit: int = 20) -> list[ProvenanceRecord]:
        sorted_records = sorted(
            self._records.values(), key=lambda r: r.retrieved_at, reverse=True
        )
        return sorted_records[:limit]

    def verify_document_integrity(self, document_id: str, current_checksum: str) -> bool:
        record = self._records.get(document_id)
        if record is None:
            return False
        return record.checksum == current_checksum

    def get_document_count(self) -> int:
        return len(self._records)


_provenance_tracker_instance: Optional[ProvenanceTracker] = None


def get_provenance_tracker() -> ProvenanceTracker:
    global _provenance_tracker_instance
    if _provenance_tracker_instance is None:
        _provenance_tracker_instance = ProvenanceTracker()
    return _provenance_tracker_instance
