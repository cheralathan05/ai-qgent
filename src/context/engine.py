"""Context Engine for Phase 3 - Tracks device, screen, app, workflow, conversation, knowledge context."""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextSnapshot:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    current_device_id: str = ""
    current_device_type: str = ""
    current_screen: str = ""
    current_app: str = ""
    current_workflow_id: str = ""
    current_conversation_id: str = ""
    current_knowledge_context: str = ""
    last_command: str = ""
    last_intent: str = ""
    last_target: str = ""
    active_document: str = ""
    active_document_path: str = ""
    recent_searches: List[str] = field(default_factory=list)
    recent_documents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "data", "context")
        os.makedirs(self.storage_path, exist_ok=True)
        self._current: Optional[ContextSnapshot] = None
        self._history: List[ContextSnapshot] = []
        self._max_history = 1000
        self._load()

    def _path(self):
        return os.path.join(self.storage_path, "context.json")

    def _load(self):
        try:
            if os.path.exists(self._path()):
                with open(self._path(), 'r') as f:
                    data = json.load(f)
                    self._current = ContextSnapshot(**data.get("current", {}))
                    self._history = [ContextSnapshot(**h) for h in data.get("history", [])]
        except Exception as e:
            logger.warning(f"Failed to load context: {e}")

    def _save(self):
        try:
            with open(self._path(), 'w') as f:
                json.dump({
                    "current": asdict(self._current) if self._current else {},
                    "history": [asdict(h) for h in self._history[-self._max_history:]],
                }, f, default=str)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def update(self, **kwargs):
        if self._current:
            self._history.append(self._current)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        base = {}
        if self._current is not None:
            base = asdict(self._current)
        base.update(kwargs)
        base["timestamp"] = datetime.utcnow()
        snapshot = ContextSnapshot(**base)
        self._current = snapshot
        self._save()

    def get_current(self) -> ContextSnapshot:
        if self._current is None:
            self._current = ContextSnapshot()
        return self._current

    def get_history(self, limit: int = 50) -> List[ContextSnapshot]:
        return self._history[-limit:]

    def get_context_summary(self) -> Dict[str, Any]:
        ctx = self.get_current()
        return {
            "device": f"{ctx.current_device_type}:{ctx.current_device_id}" if ctx.current_device_id else "none",
            "screen": ctx.current_screen or "unknown",
            "app": ctx.current_app or "none",
            "workflow": ctx.current_workflow_id or "none",
            "conversation": ctx.current_conversation_id or "none",
            "last_command": ctx.last_command or "none",
            "last_intent": ctx.last_intent or "none",
            "active_document": ctx.active_document or "none",
            "recent_searches": ctx.recent_searches[-5:],
            "recent_documents": ctx.recent_documents[-5:],
        }

    def add_search(self, query: str):
        ctx = self.get_current()
        searches = list(ctx.recent_searches)
        if query in searches:
            searches.remove(query)
        searches.append(query)
        if len(searches) > 20:
            searches = searches[-20:]
        self.update(recent_searches=searches)

    def add_document(self, doc_name: str, doc_path: str = ""):
        ctx = self.get_current()
        docs = list(ctx.recent_documents)
        if doc_name in docs:
            docs.remove(doc_name)
        docs.append(doc_name)
        if len(docs) > 20:
            docs = docs[-20:]
        self.update(
            recent_documents=docs,
            active_document=doc_name,
            active_document_path=doc_path,
        )

    def clear(self):
        self._current = None
        self._history = []
        if os.path.exists(self._path()):
            os.remove(self._path())


_context_engine: Optional[ContextEngine] = None


def get_context_engine() -> ContextEngine:
    global _context_engine
    if _context_engine is None:
        _context_engine = ContextEngine()
    return _context_engine
