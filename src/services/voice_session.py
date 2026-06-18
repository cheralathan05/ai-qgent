"""Voice session state for APA-OS with smart context management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

@dataclass
class VoiceMessage:
    role: str
    text: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class VoiceSession:
    session_id: str
    user_id: str
    user_name: str = "Cheralathan"
    current_device_id: Optional[str] = None
    current_device_type: Optional[str] = None
    current_device_label: Optional[str] = None
    last_command: Optional[str] = None
    last_intent: Optional[str] = None
    last_target: Optional[str] = None
    last_response: Optional[str] = None
    history: List[VoiceMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def record_user_message(self, text: str) -> None:
        """Appends user voice command string to runtime message queue thread history."""
        self.history.append(VoiceMessage(role="user", text=text))
        self.last_command = text
        self.updated_at = datetime.utcnow()

    def record_assistant_message(self, text: str) -> None:
        """Appends assistant vocal or text tracking string statement into matching logs."""
        self.history.append(VoiceMessage(role="assistant", text=text))
        self.last_response = text
        self.updated_at = datetime.utcnow()

    def update_automation_context(self, intent: str, target: Optional[str], device_id: str) -> None:
        """Updates automation operational parameters to manage quick conversational updates."""
        self.last_intent = intent
        self.last_target = target
        self.current_device_id = device_id
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "current_device_id": self.current_device_id,
            "current_device_type": self.current_device_type,
            "current_device_label": self.current_device_label,
            "last_command": self.last_command,
            "last_intent": self.last_intent,
            "last_target": self.last_target,
            "last_response": self.last_response,
            "history": [message.to_dict() for message in self.history[-20:]],
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class VoiceSessionStore:
    """In-memory voice session registry providing thread-safe conversational lookups."""

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}

    def _key(self, user_id: str, session_id: Optional[str]) -> str:
        return session_id if session_id else user_id

    def get_session(self, user_id: str, session_id: Optional[str] = None) -> VoiceSession:
        """Fetches an existing conversational session or bootstraps a clean one if missing."""
        key = self._key(user_id, session_id)
        session = self._sessions.get(key)
        
        if session is None:
            session = VoiceSession(
                session_id=key if session_id else f"sess_{uuid.uuid4().hex[:8]}", 
                user_id=user_id
            )
            self._sessions[key] = session
        return session

    def update_session(self, session: VoiceSession) -> VoiceSession:
        """Saves session mutations directly into internal dictionary state registry."""
        self._sessions[session.session_id] = session
        return session

    def clear(self) -> None:
        """Purges stored session state entries cleanly."""
        self._sessions.clear()


# Shared Singleton memory allocations instance
voice_session_store = None


def get_voice_session_store() -> VoiceSessionStore:
    """Returns the globally runtime shared VoiceSessionStore instance."""
    global voice_session_store
    if voice_session_store is None:
        voice_session_store = VoiceSessionStore()
    return voice_session_store