"""Conversation and response orchestration for APA-OS voice interactions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from services.voice_session import VoiceSession, get_voice_session_store


WAKE_WORDS = (
    "hey apa",
    "hello apa",
    "hi apa",
    "apa",
)


@dataclass
class ConversationResult:
    session: VoiceSession
    should_execute: bool
    command_text: str
    assistant_text: str
    wake_word_detected: bool = False
    wake_only: bool = False
    continuation: bool = False


class ConversationManager:
    """Keeps short-lived session context and crafts assistant-style replies."""

    def __init__(self, user_name: str = "Cheralathan"):
        self.user_name = user_name
        self.session_store = get_voice_session_store()

    @staticmethod
    def _normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip())

    def get_session(self, user_id: str, session_id: Optional[str] = None) -> VoiceSession:
        session = self.session_store.get_session(user_id=user_id, session_id=session_id)
        if not session.user_name:
            session.user_name = self.user_name
        return session

    def _detect_wake_word(self, text: str) -> Tuple[bool, str]:
        normalized = self._normalize_text(text)
        lower = normalized.lower()

        for wake_word in WAKE_WORDS:
            if lower == wake_word:
                return True, ""
            if lower.startswith(f"{wake_word} "):
                remainder = normalized[len(wake_word):].strip()
                return True, remainder

        return False, normalized

    def process_input(
        self,
        *,
        user_id: str,
        text: str,
        session_id: Optional[str] = None,
    ) -> ConversationResult:
        session = self.get_session(user_id=user_id, session_id=session_id)
        session.record_user_message(text)

        wake_word_detected, command_text = self._detect_wake_word(text)

        if wake_word_detected and not command_text:
            assistant_text = self.build_greeting(session)
            session.record_assistant_message(assistant_text)
            self.session_store.update_session(session)
            return ConversationResult(
                session=session,
                should_execute=False,
                command_text="",
                assistant_text=assistant_text,
                wake_word_detected=True,
                wake_only=True,
            )

        continuation = bool(session.current_device_id)
        normalized_command = command_text or self._normalize_text(text)

        return ConversationResult(
            session=session,
            should_execute=bool(normalized_command),
            command_text=normalized_command,
            assistant_text="",
            wake_word_detected=wake_word_detected,
            wake_only=False,
            continuation=continuation,
        )

    def build_greeting(self, session: VoiceSession) -> str:
        return f"Hello {session.user_name}. How can I help you today?"

    def build_device_phrase(self, device_label: str, continuation: bool = False) -> str:
        if continuation:
            return "on the same device"
        if device_label == "phone":
            return "on your phone"
        if device_label == "laptop":
            return "on your laptop"
        return "now"

    def build_pre_execution_reply(self, *, command: str, device_label: str, continuation: bool = False) -> str:
        app = self._extract_open_app_target(command)
        device_phrase = self.build_device_phrase(device_label, continuation=continuation)

        if app:
            if device_phrase == "now":
                return f"Opening {app}."
            return f"Opening {app} {device_phrase}."

        if device_phrase == "now":
            return f"Executing {command}."

        return f"Working on that {device_phrase}."

    def build_completion_reply(
        self,
        *,
        command: str,
        device_label: str,
        selection_available: bool,
        result: Dict[str, Any],
        continuation: bool = False,
    ) -> str:
        if not selection_available:
            return "I cannot find your phone. Would you like me to use your laptop instead?"

        if not result.get("success"):
            error = result.get("error") or "I could not complete that request."
            return error

        app = self._extract_open_app_target(command) or result.get("target") or result.get("intent") or "it"
        intent = (result.get("intent") or "").lower()

        if intent == "get_info" and "battery" in command.lower():
            battery = result.get("battery_level") or result.get("result", {}).get("battery_level")
            if battery is not None:
                return f"Your phone battery is currently {battery}%."
            return "I could not read the battery level right now."

        if app:
            pretty_app = str(app).replace("_", " ").title()
            if device_label == "phone":
                return f"{pretty_app} is ready."
            return f"{pretty_app} is ready on your laptop."

        if continuation:
            return "Done."

        return "Done."

    def build_error_reply(self, *, error: str, selection_available: bool) -> str:
        if not selection_available:
            return "I cannot find your phone. Would you like me to use your laptop instead?"
        return error or "I could not complete that request."

    def finalize_session(
        self,
        *,
        session: VoiceSession,
        command: str,
        intent: str,
        target: Optional[str],
        device_id: Optional[str],
        device_type: Optional[str],
        device_label: str,
        assistant_text: str,
    ) -> VoiceSession:
        session.last_command = command
        session.last_intent = intent
        session.last_target = target
        session.current_device_id = device_id
        session.current_device_type = device_type
        session.current_device_label = device_label
        session.context.update(
            {
                "last_command": command,
                "last_intent": intent,
                "last_target": target,
                "last_device_id": device_id,
                "last_device_type": device_type,
            }
        )
        session.record_assistant_message(assistant_text)
        self.session_store.update_session(session)
        return session

    @staticmethod
    def _extract_open_app_target(command: str) -> Optional[str]:
        normalized = command.lower().strip()
        match = re.match(r"^(?:open|launch|start|run)\s+(.+)$", normalized)
        if not match:
            return None

        target = match.group(1).strip()
        target = re.sub(r"\s+(?:on|in)\s+(?:my\s+)?(?:phone|laptop|computer|windows|android)$", "", target)
        return target.strip() or None


conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    return conversation_manager