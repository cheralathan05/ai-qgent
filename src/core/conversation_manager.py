"""
APA-OS Conversation Manager (Layer 1)

Multi-turn conversations:
- Context carry-over
- Session memory
- Conversation summarization
- Task continuation
- Interrupt handling
- Clarification handling
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A message in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "user"  # user or assistant
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    messages: List[Message] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    active_goal: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """
    Manages multi-turn conversations.
    
    Features:
    - Context carry-over between messages
    - Session memory
    - Active goal tracking
    - Task continuation
    - Interrupt handling
    - Clarification requests
    """

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation_id: Optional[str] = None
        self._max_history = 50

    def start_conversation(self) -> Conversation:
        """Start a new conversation."""
        conv = Conversation()
        self._conversations[conv.id] = conv
        self._active_conversation_id = conv.id
        return conv

    def get_active_conversation(self) -> Optional[Conversation]:
        """Get the active conversation."""
        if self._active_conversation_id:
            return self._conversations.get(self._active_conversation_id)
        return None

    def add_user_message(
        self,
        content: str,
        intent: str = "",
        entities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a user message to the active conversation."""
        conv = self.get_active_conversation()
        if not conv:
            conv = self.start_conversation()

        msg = Message(
            role="user",
            content=content,
            intent=intent,
            entities=entities or {},
            metadata=metadata or {},
        )
        conv.messages.append(msg)
        conv.last_active = time.time()

        # Trim if too long
        if len(conv.messages) > self._max_history:
            conv.messages = conv.messages[-self._max_history:]

        return msg

    def add_assistant_message(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add an assistant message to the active conversation."""
        conv = self.get_active_conversation()
        if not conv:
            conv = self.start_conversation()

        msg = Message(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )
        conv.messages.append(msg)
        conv.last_active = time.time()

        return msg

    def get_context(self) -> Dict[str, Any]:
        """Get the current conversation context."""
        conv = self.get_active_conversation()
        if not conv:
            return {}

        context = dict(conv.context)
        context["active_goal"] = conv.active_goal
        context["message_count"] = len(conv.messages)

        # Add recent messages for context
        recent = conv.messages[-5:] if conv.messages else []
        context["recent_messages"] = [
            {"role": m.role, "content": m.content[:200]}
            for m in recent
        ]

        return context

    def set_context(self, key: str, value: Any):
        """Set a context value."""
        conv = self.get_active_conversation()
        if conv:
            conv.context[key] = value

    def set_active_goal(self, goal: str):
        """Set the active goal for the conversation."""
        conv = self.get_active_conversation()
        if conv:
            conv.active_goal = goal

    def get_active_goal(self) -> str:
        """Get the active goal."""
        conv = self.get_active_conversation()
        return conv.active_goal if conv else ""

    def handle_interruption(self, new_command: str) -> bool:
        """Handle an interruption (new command during execution)."""
        conv = self.get_active_conversation()
        if conv and conv.active_goal:
            # Store the interrupted goal
            conv.metadata["interrupted_goal"] = conv.active_goal
            conv.metadata["interrupted_at"] = time.time()
            conv.active_goal = ""
            return True
        return False

    def resume_interrupted(self) -> Optional[str]:
        """Resume an interrupted task."""
        conv = self.get_active_conversation()
        if conv and "interrupted_goal" in conv.metadata:
            goal = conv.metadata.pop("interrupted_goal")
            conv.metadata.pop("interrupted_at", None)
            conv.active_goal = goal
            return goal
        return None

    def needs_clarification(self) -> bool:
        """Check if the conversation needs clarification."""
        conv = self.get_active_conversation()
        if not conv or not conv.messages:
            return False

        last_msg = conv.messages[-1]
        if last_msg.role == "assistant":
            content = last_msg.content.lower()
            clarification_phrases = [
                "could you clarify",
                "what do you mean",
                "which one",
                "can you specify",
                "did you mean",
                "please clarify",
                "which app",
                "which contact",
            ]
            return any(phrase in content for phrase in clarification_phrases)

        return False

    def request_clarification(self, question: str) -> Message:
        """Request clarification from the user."""
        return self.add_assistant_message(
            content=question,
            metadata={"type": "clarification_request"},
        )

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation."""
        conv = self.get_active_conversation()
        if not conv or not conv.messages:
            return "No active conversation."

        summary = f"Conversation {conv.id}:\n"
        summary += f"Messages: {len(conv.messages)}\n"
        if conv.active_goal:
            summary += f"Active goal: {conv.active_goal}\n"

        # Summarize recent messages
        recent = conv.messages[-5:]
        summary += "\nRecent messages:\n"
        for msg in recent:
            summary += f"- {msg.role}: {msg.content[:100]}\n"

        return summary

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Get all conversations."""
        return [
            {
                "id": c.id,
                "message_count": len(c.messages),
                "started_at": c.started_at,
                "last_active": c.last_active,
                "active_goal": c.active_goal,
            }
            for c in self._conversations.values()
        ]

    def clear_conversation(self, conversation_id: Optional[str] = None):
        """Clear a conversation."""
        if conversation_id:
            self._conversations.pop(conversation_id, None)
        else:
            self._conversations.clear()
            self._active_conversation_id = None

    def get_status(self) -> Dict[str, Any]:
        """Get conversation manager status."""
        return {
            "type": "conversation_manager",
            "active_conversation": self._active_conversation_id,
            "total_conversations": len(self._conversations),
            "conversations": self.get_all_conversations(),
        }


# Singleton
_conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
