"""Intent agent using rule-based understanding engine with optional Qwen LLM enhancement."""

import logging
from typing import Dict, Any

from understanding.entity_extractor import (
    EntityExtractor, IntentResult, IntentType,
    get_command_understanding_engine,
)

logger = logging.getLogger(__name__)


class IntentAgent:
    """Detect intent and entities from user text using the understanding engine."""

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.engine = get_command_understanding_engine()

    async def detect_intent(self, command: str) -> IntentResult:
        result = await self.engine.understand(command)
        logger.info(
            f"Intent: {result.intent.value} | conf={result.confidence:.2f} | "
            f"slots={result.slots} | cmd={command!r}"
        )
        return result


intent_agent = None


def get_intent_agent() -> IntentAgent:
    global intent_agent
    if intent_agent is None:
        intent_agent = IntentAgent()
    return intent_agent
