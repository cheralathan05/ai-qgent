"""Memory Engine - Short, Medium, Long Term Memory for Phase 3."""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    CONVERSATION = "conversation"
    DEVICE = "device"
    KNOWLEDGE = "knowledge"
    WORKFLOW = "workflow"
    PREFERENCE = "preference"
    SESSION = "session"


@dataclass
class Memory:
    id: str
    type: MemoryType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    embedding: Optional[List[float]] = None


@dataclass
class MemoryQuery:
    query: str
    memory_type: Optional[MemoryType] = None
    user_id: str = ""
    session_id: str = ""
    top_k: int = 10
    min_importance: float = 0.0


class MemoryEngine:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "data", "memory")
        os.makedirs(self.storage_path, exist_ok=True)
        self._short_term: Dict[str, List[Memory]] = {}
        self._medium_term: Dict[str, List[Memory]] = {}
        self._long_term: Dict[str, List[Memory]] = {}
        self._conversations: Dict[str, List[Memory]] = {}
        self._preferences: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _get_path(self, name: str) -> str:
        return os.path.join(self.storage_path, f"{name}.json")

    @staticmethod
    def _parse_memory(m: dict) -> Memory:
        if isinstance(m.get("timestamp"), str):
            m["timestamp"] = datetime.fromisoformat(m["timestamp"])
        if isinstance(m.get("expires_at"), str):
            m["expires_at"] = datetime.fromisoformat(m["expires_at"])
        if isinstance(m.get("last_accessed"), str):
            m["last_accessed"] = datetime.fromisoformat(m["last_accessed"])
        return Memory(**m)

    def _load(self):
        for fname in ["short_term", "medium_term", "long_term", "conversations", "preferences"]:
            fpath = self._get_path(fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r') as f:
                        data = json.load(f)
                    if fname == "preferences":
                        self._preferences = data
                    else:
                        container = getattr(self, f"_{fname}")
                        for key, mem_list in data.items():
                            container[key] = [self._parse_memory(m) for m in mem_list]
                except Exception as e:
                    logger.warning(f"Failed to load {fname} memory: {e}")

    def _save(self):
        for fname in ["short_term", "medium_term", "long_term", "conversations"]:
            container = getattr(self, f"_{fname}")
            data = {}
            for key, mem_list in container.items():
                data[key] = [asdict(m) for m in mem_list]
            try:
                with open(self._get_path(fname), 'w') as f:
                    json.dump(data, f, default=str)
            except Exception as e:
                logger.error(f"Failed to save {fname}: {e}")
        try:
            with open(self._get_path("preferences"), 'w') as f:
                json.dump(self._preferences, f, default=str)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")

    def store(self, memory: Memory):
        if memory.type == MemoryType.SHORT_TERM:
            key = memory.session_id or "default"
            if key not in self._short_term:
                self._short_term[key] = []
            self._short_term[key].append(memory)
            if len(self._short_term[key]) > 100:
                self._short_term[key] = self._short_term[key][-100:]

        elif memory.type in (MemoryType.MEDIUM_TERM, MemoryType.WORKFLOW, MemoryType.DEVICE):
            key = memory.user_id or "default"
            if key not in self._medium_term:
                self._medium_term[key] = []
            self._medium_term[key].append(memory)
            if len(self._medium_term[key]) > 500:
                self._medium_term[key] = self._medium_term[key][-500:]

        elif memory.type in (MemoryType.LONG_TERM, MemoryType.KNOWLEDGE, MemoryType.PREFERENCE):
            key = memory.user_id or "default"
            if key not in self._long_term:
                self._long_term[key] = []
            self._long_term[key].append(memory)

        elif memory.type == MemoryType.CONVERSATION:
            key = memory.session_id or memory.user_id or "default"
            if key not in self._conversations:
                self._conversations[key] = []
            self._conversations[key].append(memory)

        self._save()

    def store_conversation(self, user_id: str, session_id: str, user_message: str, assistant_message: str, metadata: Dict = None):
        self.store(Memory(
            id=f"conv_{user_id}_{session_id}_{datetime.utcnow().timestamp()}",
            type=MemoryType.CONVERSATION,
            content=user_message,
            metadata={"role": "user", "assistant_message": assistant_message, **(metadata or {})},
            user_id=user_id, session_id=session_id,
        ))
        self.store(Memory(
            id=f"conv_{user_id}_{session_id}_{datetime.utcnow().timestamp()}_resp",
            type=MemoryType.CONVERSATION,
            content=assistant_message,
            metadata={"role": "assistant", **(metadata or {})},
            user_id=user_id, session_id=session_id,
        ))

    def query(self, query: MemoryQuery) -> List[Memory]:
        results = []
        key = query.user_id or query.session_id or "default"

        if query.memory_type is None or query.memory_type == MemoryType.SHORT_TERM:
            skey = query.session_id or "default"
            results.extend(self._short_term.get(skey, []))

        if query.memory_type is None or query.memory_type == MemoryType.MEDIUM_TERM:
            results.extend(self._medium_term.get(key, []))

        if query.memory_type is None or query.memory_type in (MemoryType.LONG_TERM, MemoryType.KNOWLEDGE):
            results.extend(self._long_term.get(key, []))

        if query.memory_type is None or query.memory_type == MemoryType.CONVERSATION:
            ckey = query.session_id or key
            results.extend(self._conversations.get(ckey, []))

        results = [m for m in results if m.importance >= query.min_importance]
        results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return results[:query.top_k]

    def get_conversation(self, session_id: str, limit: int = 50) -> List[Memory]:
        convs = self._conversations.get(session_id, [])
        return convs[-limit:]

    def get_recent_activities(self, user_id: str, limit: int = 20) -> List[Memory]:
        results = []
        results.extend(self._medium_term.get(user_id, []))
        results.extend(self._short_term.get("default", []))
        results.sort(key=lambda m: m.timestamp, reverse=True)
        return results[:limit]

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        user_prefs = self._preferences.get(user_id, {})
        return user_prefs.get(key, default)

    def set_preference(self, user_id: str, key: str, value: Any):
        if user_id not in self._preferences:
            self._preferences[user_id] = {}
        self._preferences[user_id][key] = value
        self._save()

    def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        return self._preferences.get(user_id, {})

    def clear_session(self, session_id: str):
        self._short_term.pop(session_id, None)
        self._conversations.pop(session_id, None)
        self._save()

    def clear_all(self, user_id: str = ""):
        if user_id:
            self._medium_term.pop(user_id, None)
            self._long_term.pop(user_id, None)
            self._preferences.pop(user_id, None)
        else:
            self._short_term.clear()
            self._medium_term.clear()
            self._long_term.clear()
            self._conversations.clear()
            self._preferences.clear()
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "short_term": sum(len(v) for v in self._short_term.values()),
            "medium_term": sum(len(v) for v in self._medium_term.values()),
            "long_term": sum(len(v) for v in self._long_term.values()),
            "conversations": sum(len(v) for v in self._conversations.values()),
            "preferences": sum(len(v) for v in self._preferences.values()),
            "total_sessions": len(self._short_term) + len(self._conversations),
        }

    def get_current_session_context(self, session_id: str) -> Dict[str, Any]:
        memories = self._short_term.get(session_id, [])
        convs = self._conversations.get(session_id, [])
        return {
            "session_id": session_id,
            "recent_memories": len(memories),
            "conversation_turns": len(convs) // 2,
            "last_activity": memories[-1].timestamp.isoformat() if memories else None,
            "last_message": convs[-1].content if convs else None,
        }


_memory_engine: Optional[MemoryEngine] = None


def get_memory_engine() -> MemoryEngine:
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine()
    return _memory_engine
