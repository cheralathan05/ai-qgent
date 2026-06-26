"""Intent agent using universal action recognizer with LLM enhancement."""

import logging
from typing import Dict, Any, Optional

from understanding.action_recognizer import (
    ActionRecognizer, RecognitionResult, RecognizedAction, ActionCategory,
    get_action_recognizer,
)
from understanding.entity_extractor import (
    EntityExtractor, IntentResult, IntentType,
    get_command_understanding_engine,
)

logger = logging.getLogger(__name__)


class IntentAgent:
    """Detect intent and entities from user text using universal action recognizer.

    Combines fast regex patterns with LLM enhancement for accurate understanding
    of ANY user request - not just predefined commands.
    """

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.engine = get_command_understanding_engine()
        self.recognizer = get_action_recognizer()

    async def detect_intent(self, command: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        # Primary: use the universal action recognizer
        recognition = await self.recognizer.recognize(command, context=context)
        
        # Map recognition result to legacy IntentResult for backward compatibility
        legacy_intent = self._map_to_legacy_intent(recognition.action)
        
        intent_result = IntentResult(
            intent=legacy_intent,
            confidence=recognition.confidence,
            entities=[],
            slots=recognition.entities,
            raw_command=command,
            normalized_command=recognition.normalized_text,
            context=context,
        )
        
        logger.info(
            f"Intent: {recognition.action.value} (legacy: {legacy_intent.value}) | "
            f"conf={recognition.confidence:.2f} | "
            f"entities={recognition.entities} | "
            f"compound={recognition.is_compound} | "
            f"cmd={command!r}"
        )
        return intent_result

    async def recognize(self, command: str, context: Optional[Dict[str, Any]] = None) -> RecognitionResult:
        """Full recognition with action type, entities, and compound detection."""
        return await self.recognizer.recognize(command, context=context)

    def _map_to_legacy_intent(self, action: RecognizedAction) -> IntentType:
        mapping = {
            RecognizedAction.OPEN_APP: IntentType.OPEN_APP,
            RecognizedAction.CLOSE_APP: IntentType.CLOSE_APP,
            RecognizedAction.SEND_MESSAGE: IntentType.SEND_MESSAGE,
            RecognizedAction.REPLY_MESSAGE: IntentType.SEND_MESSAGE,
            RecognizedAction.MAKE_CALL: IntentType.MAKE_CALL,
            RecognizedAction.VIDEO_CALL: IntentType.MAKE_CALL,
            RecognizedAction.SEARCH_WEB: IntentType.WEB_SEARCH,
            RecognizedAction.SEARCH_APP: IntentType.SEARCH,
            RecognizedAction.SEARCH_FILE: IntentType.SEARCH,
            RecognizedAction.OPEN_CHAT: IntentType.OPEN_CHAT,
            RecognizedAction.OPEN_SETTINGS: IntentType.OPEN_SETTINGS,
            RecognizedAction.OPEN_SETTING_SECTION: IntentType.OPEN_SETTINGS,
            RecognizedAction.BATTERY_STATUS: IntentType.BATTERY_STATUS,
            RecognizedAction.SCREENSHOT: IntentType.TAKE_SCREENSHOT,
            RecognizedAction.SCREEN_RECORD: IntentType.TAKE_SCREENSHOT,
            RecognizedAction.OPEN_CAMERA: IntentType.OPEN_CAMERA,
            RecognizedAction.TAKE_PHOTO: IntentType.OPEN_CAMERA,
            RecognizedAction.SEND_EMAIL: IntentType.SEND_EMAIL,
            RecognizedAction.OPEN_FILE: IntentType.OPEN_FILE,
            RecognizedAction.OPEN_FOLDER: IntentType.OPEN_FOLDER,
            RecognizedAction.SEARCH_FILE: IntentType.OPEN_FOLDER,
            RecognizedAction.LOCK_DEVICE: IntentType.LOCK_DEVICE,
            RecognizedAction.READ_NOTIFICATIONS: IntentType.READ_NOTIFICATIONS,
            RecognizedAction.TOGGLE_WIFI: IntentType.WIFI_ON,
            RecognizedAction.TOGGLE_BLUETOOTH: IntentType.BLUETOOTH_ON,
            RecognizedAction.TOGGLE_FLASHLIGHT: IntentType.FLASH_ON,
            RecognizedAction.PLAY_MEDIA: IntentType.PLAY_MUSIC,
            RecognizedAction.GO_BACK: IntentType.NAVIGATE,
            RecognizedAction.GO_HOME: IntentType.NAVIGATE,
            RecognizedAction.GO_TO_SCREEN: IntentType.NAVIGATE,
            RecognizedAction.DEVICE_INFO: IntentType.FOREGROUND_APP,
        }
        return mapping.get(action, IntentType.UNKNOWN)


intent_agent = None


def get_intent_agent() -> IntentAgent:
    global intent_agent
    if intent_agent is None:
        intent_agent = IntentAgent()
    return intent_agent
