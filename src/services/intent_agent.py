"""Intent agent using local Qwen model and rule-based fallback."""

import logging
import json
from typing import Dict, Any, Optional
from understanding.entity_extractor import EntityExtractor, IntentResult, IntentType
from services.qwen_service import get_qwen_service, QwenServiceError

logger = logging.getLogger(__name__)


class IntentAgent:
    """Detect intent and entities from user text."""

    PROMPT_TEMPLATE = (
        "You are an intent extraction agent. Respond with strict JSON only. "
        "Analyze the user command and return an object with keys: intent, target, confidence, requires_approval. "
        "Valid intents are open_app, close_app, send_message, make_call, search, navigate, unlock_device, get_info, settings, unknown. "
        "Example output:\n{\n  \"intent\": \"open_app\",\n  \"target\": \"chrome\",\n  \"confidence\": 0.99,\n  \"requires_approval\": false\n}\n"
    )

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.qwen_service = get_qwen_service()

    def _build_open_app_result(self, command: str, normalized: str):
        entities = self.entity_extractor.extract_all(normalized)
        slots = self.entity_extractor._fill_slots(IntentType.OPEN_APP, entities)
        target = slots.get("app") or slots.get("target")
        if target:
            return IntentResult(
                intent=IntentType.OPEN_APP,
                confidence=0.99,
                entities=entities,
                slots={"app": target},
                raw_command=command,
                normalized_command=normalized,
            )
        return None

    async def detect_intent(self, command: str) -> IntentResult:
        normalized = self.entity_extractor.normalizer.normalize(command)
        open_app_result = self._build_open_app_result(command, normalized)
        if open_app_result is not None:
            return open_app_result

        try:
            prompt = self.PROMPT_TEMPLATE + f"\nUser command: {normalized}\n"
            payload = await self.qwen_service.generate_json(prompt)
            intent_text = payload.get("intent", "unknown")
            target = payload.get("target")
            confidence = float(payload.get("confidence", 0.0))
            requires_approval = bool(payload.get("requires_approval", False))

            intent_type = IntentType(intent_text) if intent_text in IntentType._value2member_map_ else IntentType.UNKNOWN
            entities = self.entity_extractor.extract_all(normalized)
            slots = self.entity_extractor._fill_slots(intent_type, entities)
            if target and intent_type == IntentType.OPEN_APP and "app" not in slots:
                slots["app"] = target

            if intent_type == IntentType.OPEN_APP and slots.get("app"):
                confidence = max(confidence, 0.99)

            return IntentResult(
                intent=intent_type,
                confidence=confidence,
                entities=entities,
                slots=slots,
                raw_command=command,
                normalized_command=normalized,
            )

        except Exception as exc:
            logger.warning(f"Qwen intent detection failed, using fallback: {exc}")
            intent_type, confidence = self.entity_extractor.intent_classifier.classify(normalized)
            entities = self.entity_extractor.extract_all(normalized)
            slots = self.entity_extractor._fill_slots(intent_type, entities)
            if intent_type == IntentType.OPEN_APP and slots.get("app"):
                confidence = 0.99
            return IntentResult(
                intent=intent_type,
                confidence=confidence,
                entities=entities,
                slots=slots,
                raw_command=command,
                normalized_command=normalized,
            )


intent_agent = None


def get_intent_agent() -> IntentAgent:
    global intent_agent
    if intent_agent is None:
        intent_agent = IntentAgent()
    return intent_agent
