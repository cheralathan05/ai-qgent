"""Conversation and response orchestration for APA-OS voice interactions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from services.voice_session import VoiceSession, get_voice_session_store
from understanding.entity_extractor import IntentResult, IntentType


WAKE_WORDS = (
    "hey apa",
    "hello apa",
    "hi apa",
    "apa",
)

# Apps that have their own messaging feature (not SMS)
MESSAGING_APPS = {"instagram", "whatsapp", "facebook", "twitter", "x", "telegram", "signal"}


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

    def resolve_context(
        self,
        intent_result: IntentResult,
        session: VoiceSession,
    ) -> IntentResult:
        """Resolve ambiguous references using session context.

        Example: user opens Instagram, then says 'Open Messages'.
        Context: last app was Instagram → resolve 'Messages' as Instagram DMs.
        """
        if not session.last_intent and not session.last_target:
            return intent_result

        intent = intent_result.intent
        slots = intent_result.slots
        last_app = session.context.get("last_target") or session.last_target
        last_intent = session.context.get("last_intent") or session.last_intent

        if intent == IntentType.OPEN_APP:
            app = slots.get("app", "")
            app_lower = app.lower()

            # "Messages" after a messaging app → open that app's chat
            if app_lower in ("messages", "message", "chat", "dm", "inbox"):
                if last_app and last_intent in ("open_app", "open_chat", "send_message"):
                    last_app_lower = str(last_app).lower()
                    if last_app_lower in MESSAGING_APPS:
                        intent_result.intent = IntentType.OPEN_CHAT
                        intent_result.slots = {"app": last_app_lower, "recipient": ""}
                        intent_result.confidence = max(intent_result.confidence, 0.85)
                        return intent_result

            # "Contacts" after a messaging app → open that app's contacts/chat
            if app_lower in ("contacts", "people", "friends"):
                if last_app and last_app.lower() in MESSAGING_APPS:
                    intent_result.slots["app"] = str(last_app).lower()
                    intent_result.confidence = max(intent_result.confidence, 0.85)
                    return intent_result

        if intent == IntentType.OPEN_CHAT:
            app = slots.get("app", "")
            if not app or app == "":
                if last_app and last_app.lower() in MESSAGING_APPS:
                    intent_result.slots["app"] = str(last_app).lower()
                    intent_result.confidence = max(intent_result.confidence, 0.85)

        return intent_result

    @staticmethod
    def _extract_target(command: str) -> Optional[str]:
        """Extract the target noun from a natural command."""
        normalized = command.lower().strip()

        patterns = [
            r"^(?:open|launch|start|run)\s+(?:my\s+)?(.+?)(?:\s+app)?$",
            r"^go\s+to\s+(?:my\s+)?(.+?)$",
            r"^switch\s+to\s+(?:my\s+)?(.+?)$",
            r"^i\s+want\s+to\s+(?:open|launch|start|check|see|use)\s+(?:my\s+)?(.+?)(?:\s+app)?$",
            r"^can\s+(?:you|i)\s+(?:open|launch|start|run|check)\s+(?:my\s+)?(.+?)(?:\s+app)?$",
            r"^check\s+(?:on\s+)?(?:my\s+)?(.+?)$",
            r"^could\s+you\s+(?:open|launch|start|run|check)\s+(?:my\s+)?(.+?)(?:\s+app)?$",
        ]
        for pattern in patterns:
            match = re.match(pattern, normalized)
            if match:
                target = match.group(1).strip()
                target = re.sub(
                    r"\s+(?:on|in)\s+(?:my\s+)?(?:phone|laptop|computer|windows|android)$",
                    "", target,
                )
                return target.strip() or None

        return None

    @staticmethod
    def _pretty(name: str) -> str:
        if not name:
            return ""
        return str(name).replace("_", " ").replace("-", " ").title()

    def build_device_phrase(self, device_label: str, continuation: bool = False) -> str:
        if continuation:
            return "on the same device"
        if device_label == "phone":
            return "on your phone"
        if device_label == "laptop":
            return "on your laptop"
        return "now"

    def build_greeting(self, session: VoiceSession) -> str:
        return f"Hello {session.user_name}. How can I help you today?"

    def build_pre_execution_reply(
        self,
        *,
        command: str,
        intent: str,
        target: Optional[str],
        device_label: str,
        continuation: bool = False,
    ) -> str:
        device_phrase = self.build_device_phrase(device_label, continuation=continuation)
        intent_lower = intent.lower() if intent else ""

        if intent_lower == "open_app" and target:
            pretty = self._pretty(target)
            if device_phrase == "now":
                return f"Opening {pretty}."
            return f"Opening {pretty} {device_phrase}."

        if intent_lower == "close_app" and target:
            pretty = self._pretty(target)
            return f"Closing {pretty}."

        if intent_lower == "send_message":
            recipient = self._extract_recipient(command) or "your contact"
            return f"Sending message to {recipient}."

        if intent_lower == "call_contact":
            recipient = self._extract_recipient(command) or "your contact"
            return f"Calling {recipient}."

        if intent_lower == "open_chat":
            recipient = self._extract_recipient(command)
            app = self._extract_target(command) or target
            if recipient:
                return f"Opening chat with {recipient}."
            if app:
                return f"Opening {self._pretty(app)} chat."
            return "Opening chat."

        if intent_lower in ("search", "web_search"):
            query = self._extract_search_query(command)
            if query:
                return f"Searching for {query}."
            return "Searching."

        if intent_lower == "battery_status":
            return "Checking your battery level."

        if intent_lower == "foreground_app":
            return "Checking what is on your screen."

        if intent_lower == "take_screenshot":
            return "Taking a screenshot."

        if intent_lower == "open_settings":
            return "Opening settings."

        if intent_lower == "open_folder":
            folder = target or "downloads"
            return f"Opening {folder} folder."

        if device_phrase == "now":
            return f"Working on that."

        return f"Working on that {device_phrase}."

    def build_completion_reply(
        self,
        *,
        command: str,
        intent: str,
        target: Optional[str],
        device_label: str,
        selection_available: bool,
        result: Dict[str, Any],
        continuation: bool = False,
    ) -> str:
        if not selection_available:
            return "I cannot find your phone. Would you like me to use your laptop instead?"

        if not result.get("success"):
            return result.get("error") or "I could not complete that request."

        intent_lower = intent.lower() if intent else ""

        if intent_lower == "battery_status":
            battery = result.get("battery_level") or result.get("result", {}).get("battery_level")
            if battery is not None:
                return f"Your phone battery is currently {battery}%."
            return "I could not read the battery level right now."

        if intent_lower == "foreground_app":
            fg = result.get("foreground_app") or result.get("result", {}).get("foreground_app")
            if fg:
                return f"The current app is {fg}."
            return "I could not detect the foreground app."

        if intent_lower == "send_message":
            recipient = self._extract_recipient(command) or "your contact"
            return f"Message sent to {recipient} successfully."

        if intent_lower == "call_contact":
            recipient = self._extract_recipient(command) or "your contact"
            return f"Calling {recipient}."

        if intent_lower == "take_screenshot":
            return "Screenshot captured."

        if intent_lower in ("search", "web_search"):
            query = self._extract_search_query(command) or ""
            if query:
                return f"Search results for {query} are ready."
            return "Search completed."

        if target:
            pretty = self._pretty(target)
            if device_label == "phone":
                return f"{pretty} is ready."
            return f"{pretty} is ready on your laptop."

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
    def _extract_recipient(command: str) -> Optional[str]:
        normalized = command.lower().strip()
        patterns = [
            r"(?:send|message|text|call|ping|dm)\s+(?:a\s+)?(?:message\s+)?(?:to\s+)?(\w+)",
            r"(?:open)\s+(\w+)\s+chat",
            r"(?:chat\s+with)\s+(\w+)",
            r"(?:tell|say)\s+(?:\w+\s+)?(.+?)\s+to\s+(\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return match.group(1).strip().title()
        return None

    @staticmethod
    def _extract_search_query(command: str) -> Optional[str]:
        normalized = command.lower().strip()
        patterns = [
            r"(?:search|find|google|look up|look for)\s+(?:for\s+)?(.+?)(?:\s+(?:on|in|using)\s+\w+)?$",
            r"(?:search|find|google)\s+(?:for\s+)?(.+?)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return match.group(1).strip().rstrip(".")
        return None


conversation_manager = None


def get_conversation_manager() -> ConversationManager:
    global conversation_manager
    if conversation_manager is None:
        conversation_manager = ConversationManager()
    return conversation_manager
