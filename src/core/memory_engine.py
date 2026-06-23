"""
APA-OS Memory Engine

Remembers:
- Current Device
- Current App
- Current Screen
- Current Chat
- Current Contact
- Current File
- Recent Searches
- Recent Documents
- Recent Projects
- Recent Commands
- Workflow History
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryState:
    """Current memory state."""
    current_device_id: str = ""
    current_app: str = ""
    current_screen: str = ""
    current_chat: str = ""
    current_contact: str = ""
    current_file: str = ""
    current_workflow_id: str = ""
    
    recent_commands: List[Dict[str, Any]] = field(default_factory=list)
    recent_searches: List[str] = field(default_factory=list)
    recent_documents: List[str] = field(default_factory=list)
    recent_apps: List[str] = field(default_factory=list)
    recent_contacts: List[str] = field(default_factory=list)
    
    workflow_history: List[Dict[str, Any]] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryEngine:
    """
    Remembers everything about the user's interactions.
    
    Always knows:
    - What app is open
    - What screen is visible
    - What document is active
    - What workflow is running
    - What user is trying to achieve
    """

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "memory"
        )
        os.makedirs(self.storage_path, exist_ok=True)
        self._state = MemoryState()
        self._load()

    def _path(self) -> str:
        return os.path.join(self.storage_path, "memory.json")

    def _load(self):
        try:
            if os.path.exists(self._path()):
                with open(self._path(), 'r') as f:
                    data = json.load(f)
                    self._state = MemoryState(**data)
        except Exception as e:
            logger.warning(f"Failed to load memory: {e}")

    def _save(self):
        try:
            with open(self._path(), 'w') as f:
                json.dump(asdict(self._state), f, default=str)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def update(self, **kwargs):
        """Update memory state."""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        self._save()

    def get_state(self) -> MemoryState:
        return self._state

    def record_command(self, command: str, intent: str, success: bool):
        """Record a command."""
        entry = {
            "command": command,
            "intent": intent,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._state.recent_commands.append(entry)
        if len(self._state.recent_commands) > 50:
            self._state.recent_commands = self._state.recent_commands[-50:]
        self._save()

    def record_search(self, query: str):
        """Record a search."""
        if query in self._state.recent_searches:
            self._state.recent_searches.remove(query)
        self._state.recent_searches.append(query)
        if len(self._state.recent_searches) > 20:
            self._state.recent_searches = self._state.recent_searches[-20:]
        self._save()

    def record_document(self, doc_name: str):
        """Record a document access."""
        if doc_name in self._state.recent_documents:
            self._state.recent_documents.remove(doc_name)
        self._state.recent_documents.append(doc_name)
        if len(self._state.recent_documents) > 20:
            self._state.recent_documents = self._state.recent_documents[-20:]
        self._save()

    def record_app(self, app_name: str):
        """Record app usage."""
        if app_name in self._state.recent_apps:
            self._state.recent_apps.remove(app_name)
        self._state.recent_apps.append(app_name)
        if len(self._state.recent_apps) > 20:
            self._state.recent_apps = self._state.recent_apps[-20:]
        self._save()

    def record_contact(self, contact_name: str):
        """Record contact interaction."""
        if contact_name in self._state.recent_contacts:
            self._state.recent_contacts.remove(contact_name)
        self._state.recent_contacts.append(contact_name)
        if len(self._state.recent_contacts) > 20:
            self._state.recent_contacts = self._state.recent_contacts[-20:]
        self._save()

    def record_workflow(self, workflow_id: str, intent: str, description: str):
        """Record a workflow execution."""
        entry = {
            "workflow_id": workflow_id,
            "intent": intent,
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._state.workflow_history.append(entry)
        if len(self._state.workflow_history) > 100:
            self._state.workflow_history = self._state.workflow_history[-100:]
        self._save()

    def get_summary(self) -> Dict[str, Any]:
        """Get memory summary."""
        return {
            "current_device": self._state.current_device_id or "none",
            "current_app": self._state.current_app or "none",
            "current_screen": self._state.current_screen or "none",
            "current_chat": self._state.current_chat or "none",
            "current_file": self._state.current_file or "none",
            "recent_commands": len(self._state.recent_commands),
            "recent_searches": self._state.recent_searches[-5:],
            "recent_documents": self._state.recent_documents[-5:],
            "recent_apps": self._state.recent_apps[-5:],
            "recent_contacts": self._state.recent_contacts[-5:],
            "total_workflows": len(self._state.workflow_history),
        }

    def clear(self):
        """Clear memory."""
        self._state = MemoryState()
        self._save()


# Singleton
_memory_engine = None


def get_memory_engine() -> MemoryEngine:
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine()
    return _memory_engine
