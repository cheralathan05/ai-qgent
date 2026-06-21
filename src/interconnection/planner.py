import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from understanding.entity_extractor import (
    get_command_understanding_engine,
    CommandUnderstandingEngine,
    IntentType,
)

logger = logging.getLogger(__name__)


class UnifiedIntentType(str, Enum):
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SEND_MESSAGE = "send_message"
    OPEN_CHAT = "open_chat"
    REPLY = "reply"
    TAKE_SCREENSHOT = "take_screenshot"
    CHECK_BATTERY = "check_battery"
    GET_FOREGROUND_APP = "foreground_app"
    OPEN_SETTINGS = "open_settings"
    CALL_CONTACT = "call_contact"
    SEARCH_WEB = "search"
    KNOWLEDGE_QUERY = "knowledge_query"
    SCREEN_AWARE = "screen_aware"
    NAVIGATE = "navigate"
    NAVIGATE_HOME = "navigate_home"
    GO_BACK = "go_back"
    SCROLL = "scroll"
    TAP = "tap"
    TYPE_TEXT = "type_text"
    OPEN_FOLDER = "open_folder"
    UNKNOWN = "unknown"


class UnifiedPlanner:
    """Routes every command through a unified Phase1→Phase2→Phase3 plan."""

    def __init__(self):
        self.command_engine = get_command_understanding_engine()

    def create_plan(self, command: str) -> Tuple[UnifiedIntentType, Dict[str, Any], List[Dict[str, Any]]]:
        intent_result = self.command_engine.understand(command)
        intent_val = intent_result.intent.value if hasattr(intent_result.intent, 'value') else str(intent_result.intent)
        unified_intent = self._map_intent(intent_val)
        slots = intent_result.slots

        plan = self._build_plan(unified_intent, slots, command)
        return unified_intent, slots, plan

    def _map_intent(self, intent_val: str) -> UnifiedIntentType:
        mapping = {
            "open_app": UnifiedIntentType.OPEN_APP,
            "close_app": UnifiedIntentType.CLOSE_APP,
            "send_message": UnifiedIntentType.SEND_MESSAGE,
            "open_chat": UnifiedIntentType.OPEN_CHAT,
            "reply": UnifiedIntentType.REPLY,
            "take_screenshot": UnifiedIntentType.TAKE_SCREENSHOT,
            "check_battery": UnifiedIntentType.CHECK_BATTERY,
            "foreground_app": UnifiedIntentType.GET_FOREGROUND_APP,
            "open_settings": UnifiedIntentType.OPEN_SETTINGS,
            "call_contact": UnifiedIntentType.CALL_CONTACT,
            "search": UnifiedIntentType.SEARCH_WEB,
            "web_search": UnifiedIntentType.SEARCH_WEB,
            "ask": UnifiedIntentType.KNOWLEDGE_QUERY,
            "find": UnifiedIntentType.KNOWLEDGE_QUERY,
            "knowledge": UnifiedIntentType.KNOWLEDGE_QUERY,
            "navigate": UnifiedIntentType.NAVIGATE,
            "navigate_home": UnifiedIntentType.NAVIGATE_HOME,
            "go_back": UnifiedIntentType.GO_BACK,
            "scroll": UnifiedIntentType.SCROLL,
            "tap": UnifiedIntentType.TAP,
            "type_text": UnifiedIntentType.TYPE_TEXT,
            "open_folder": UnifiedIntentType.OPEN_FOLDER,
        }
        return mapping.get(intent_val, UnifiedIntentType.UNKNOWN)

    def _build_plan(self, intent: UnifiedIntentType, slots: Dict[str, Any], command: str) -> List[Dict[str, Any]]:
        plan = []
        is_knowledge = intent in (
            UnifiedIntentType.KNOWLEDGE_QUERY,
            UnifiedIntentType.SEARCH_WEB,
        )
        is_screen_aware = intent == UnifiedIntentType.SCREEN_AWARE or \
            any(word in command.lower() for word in ["what am i looking at", "what is on my screen", "what app", "current screen"])

        if is_knowledge:
            plan.append({"phase": "phase3", "action": "knowledge_search", "query": command})
            return plan

        if is_screen_aware:
            plan.append({"phase": "phase2", "action": "capture_and_analyze"})
            plan.append({"phase": "phase3", "action": "reason_about_screen"})
            return plan

        if intent == UnifiedIntentType.OPEN_APP:
            app = slots.get("app", "")
            plan.append({"phase": "phase1", "action": "launch_app", "app": app})
            plan.append({"phase": "phase2", "action": "verify_and_classify", "expected": "app"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "app_opened"})
            return plan

        if intent == UnifiedIntentType.SEND_MESSAGE:
            recipient = slots.get("recipient", "")
            message = slots.get("message", "")
            app = slots.get("app", "whatsapp")
            plan.append({"phase": "phase1", "action": "send_message", "recipient": recipient, "message": message, "app": app})
            plan.append({"phase": "phase2", "action": "verify_send_message", "message": message})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "message_sent"})
            return plan

        if intent == UnifiedIntentType.OPEN_CHAT:
            recipient = slots.get("recipient", "")
            app = slots.get("app", "instagram")
            plan.append({"phase": "phase1", "action": "open_chat", "recipient": recipient, "app": app})
            plan.append({"phase": "phase2", "action": "verify_and_classify", "expected": "chat"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "chat_opened"})
            return plan

        if intent == UnifiedIntentType.REPLY:
            message = slots.get("message", "")
            plan.append({"phase": "phase1", "action": "reply", "message": message})
            plan.append({"phase": "phase2", "action": "verify_send_message", "message": message})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "reply_sent"})
            return plan

        if intent == UnifiedIntentType.TAKE_SCREENSHOT:
            plan.append({"phase": "phase1", "action": "take_screenshot"})
            plan.append({"phase": "phase2", "action": "capture_and_analyze"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "screenshot_taken"})
            return plan

        if intent == UnifiedIntentType.CHECK_BATTERY:
            plan.append({"phase": "phase1", "action": "check_battery"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "battery_check"})
            return plan

        if intent == UnifiedIntentType.GET_FOREGROUND_APP:
            plan.append({"phase": "phase1", "action": "get_foreground_app"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "foreground_check"})
            return plan

        if intent == UnifiedIntentType.OPEN_SETTINGS:
            section = slots.get("section", "")
            plan.append({"phase": "phase1", "action": "open_settings", "section": section})
            plan.append({"phase": "phase2", "action": "verify_and_classify", "expected": "app"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "settings_opened"})
            return plan

        if intent == UnifiedIntentType.CALL_CONTACT:
            recipient = slots.get("recipient", "")
            plan.append({"phase": "phase1", "action": "call_contact", "recipient": recipient})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "call_initiated"})
            return plan

        if intent in (UnifiedIntentType.NAVIGATE_HOME, UnifiedIntentType.GO_BACK, UnifiedIntentType.SCROLL):
            plan.append({"phase": "phase1", "action": intent.value})
            plan.append({"phase": "phase2", "action": "capture_and_analyze"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "navigation"})
            return plan

        if intent == UnifiedIntentType.NAVIGATE:
            screen = slots.get("target", slots.get("screen", ""))
            app = slots.get("app", "")
            plan.append({"phase": "phase1", "action": "navigate", "screen": screen, "app": app})
            plan.append({"phase": "phase2", "action": "verify_and_classify", "expected": "screen"})
            plan.append({"phase": "phase3", "action": "store_context", "context_type": "navigation"})
            return plan

        plan.append({"phase": "phase3", "action": "knowledge_search", "query": command})
        return plan


def get_unified_planner():
    return UnifiedPlanner()
