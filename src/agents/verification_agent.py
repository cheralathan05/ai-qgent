"""Verification Agent - Visual confirmation of state changes.

Verifies that actions actually succeeded by capturing screen and
checking expected state. Returns confidence scores.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from agents.vision_agent import get_vision_agent, ScreenState, DetectedElement

logger = logging.getLogger(__name__)


class VerificationType(str, Enum):
    MESSAGE_SENT = "message_sent"
    CHAT_OPENED = "chat_opened"
    APP_OPENED = "app_opened"
    SCREEN_CHANGED = "screen_changed"
    TEXT_PRESENT = "text_present"
    ELEMENT_PRESENT = "element_present"
    SEARCH_OPENED = "search_opened"


@dataclass
class VerificationResult:
    verification_type: VerificationType
    passed: bool
    confidence: float
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    screenshot_path: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "type": self.verification_type.value,
            "passed": self.passed,
            "confidence": self.confidence,
            "message": self.message,
            "evidence": self.evidence,
            "screenshot_path": self.screenshot_path,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class VerificationAgent:
    """Verifies actions by capturing and analyzing screen state.

    Every action must be visually verified before being considered successful.
    """

    def __init__(self):
        self._vision = get_vision_agent()

    async def verify_message_sent(
        self, device_id: str, message_text: str, timeout_seconds: int = 10
    ) -> VerificationResult:
        """Verify that a message was actually sent by checking screen content."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            state = await self._vision.quick_analyze(device_id)
            if not state.success:
                await asyncio.sleep(1)
                continue

            if message_text.lower() in state.full_ocr_text.lower():
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VerificationResult(
                    verification_type=VerificationType.MESSAGE_SENT,
                    passed=True,
                    confidence=0.9,
                    message=f"Message text found on screen",
                    evidence={
                        "message_snippet": message_text[:50],
                        "ocr_engine": state.ocr_engine,
                        "attempts": attempt + 1,
                    },
                    screenshot_path=state.screenshot_path,
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.MESSAGE_SENT,
            passed=False,
            confidence=0.3,
            message=f"Message not verified as sent within {timeout_seconds}s",
            evidence={"message_text": message_text[:50], "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_chat_opened(
        self, device_id: str, contact_name: str, app_name: str, timeout_seconds: int = 10
    ) -> VerificationResult:
        """Verify that a chat with the contact is open."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            state = await self._vision.analyze_screen(device_id, app_name)
            if not state.success:
                await asyncio.sleep(1)
                continue

            name_present = contact_name.lower() in state.full_ocr_text.lower()
            has_input = state.has_element_type("input_field") or "type a message" in state.full_ocr_text.lower()
            has_send = state.find_send_button() is not None

            if name_present and (has_input or has_send):
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                confidence = 0.85 if has_input and has_send else 0.7
                return VerificationResult(
                    verification_type=VerificationType.CHAT_OPENED,
                    passed=True,
                    confidence=confidence,
                    message=f"Chat with {contact_name} verified open on {app_name}",
                    evidence={
                        "contact": contact_name,
                        "app": app_name,
                        "name_in_ocr": name_present,
                        "has_input": has_input,
                        "has_send": has_send,
                        "screen_type": state.screen_type,
                        "attempts": attempt + 1,
                    },
                    screenshot_path=state.screenshot_path,
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.CHAT_OPENED,
            passed=False,
            confidence=0.3,
            message=f"Chat with {contact_name} not verified on {app_name}",
            evidence={"contact": contact_name, "app": app_name, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_app_opened(
        self, device_id: str, expected_app: str, timeout_seconds: int = 10
    ) -> VerificationResult:
        """Verify that the expected app is open."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            state = await self._vision.analyze_screen(device_id)
            if not state.success:
                await asyncio.sleep(1)
                continue

            app_match = expected_app.lower() in (state.app_name or "").lower()
            app_in_text = expected_app.lower() in state.full_ocr_text.lower()

            if app_match or app_in_text:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VerificationResult(
                    verification_type=VerificationType.APP_OPENED,
                    passed=True,
                    confidence=0.85,
                    message=f"App {expected_app} verified open",
                    evidence={
                        "expected": expected_app,
                        "detected_app": state.app_name,
                        "screen_type": state.screen_type,
                        "attempts": attempt + 1,
                    },
                    screenshot_path=state.screenshot_path,
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.APP_OPENED,
            passed=False,
            confidence=0.3,
            message=f"App {expected_app} not verified within {timeout_seconds}s",
            evidence={"expected_app": expected_app, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_screen_changed(
        self, device_id: str, previous_ocr_text: str, timeout_seconds: int = 10
    ) -> VerificationResult:
        """Verify that the screen has changed from a previous state."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            await asyncio.sleep(1)
            state = await self._vision.quick_analyze(device_id)
            if not state.success:
                continue

            if state.full_ocr_text != previous_ocr_text and len(state.full_ocr_text) > 0:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VerificationResult(
                    verification_type=VerificationType.SCREEN_CHANGED,
                    passed=True,
                    confidence=0.75,
                    message="Screen content changed",
                    evidence={
                        "text_changed": True,
                        "attempts": attempt + 1,
                    },
                    screenshot_path=state.screenshot_path,
                    duration_ms=elapsed,
                )

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.SCREEN_CHANGED,
            passed=False,
            confidence=0.3,
            message="Screen did not change",
            duration_ms=elapsed,
        )

    async def verify_text_present(
        self, device_id: str, text: str, timeout_seconds: int = 10
    ) -> VerificationResult:
        """Verify that specific text is present on screen."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            state = await self._vision.quick_analyze(device_id)
            if state.success and text.lower() in state.full_ocr_text.lower():
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VerificationResult(
                    verification_type=VerificationType.TEXT_PRESENT,
                    passed=True,
                    confidence=0.85,
                    message=f"Text '{text}' found on screen",
                    evidence={"search_text": text, "attempts": attempt + 1},
                    screenshot_path=state.screenshot_path,
                    duration_ms=elapsed,
                )
            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.TEXT_PRESENT,
            passed=False,
            confidence=0.3,
            message=f"Text '{text}' not found on screen",
            evidence={"search_text": text, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_element_present(
        self, device_id: str, element_type: str, text: Optional[str] = None,
        timeout_seconds: int = 10,
    ) -> VerificationResult:
        """Verify that a specific UI element is present."""
        start = datetime.utcnow()

        for attempt in range(timeout_seconds):
            element = await self._vision.find_element(device_id, text or element_type, element_type)
            if element:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VerificationResult(
                    verification_type=VerificationType.ELEMENT_PRESENT,
                    passed=True,
                    confidence=element.confidence,
                    message=f"Element '{text or element_type}' found",
                    evidence={
                        "element_type": element.element_type,
                        "text": element.text,
                        "x": element.x, "y": element.y,
                        "attempts": attempt + 1,
                    },
                    duration_ms=elapsed,
                )
            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VerificationResult(
            verification_type=VerificationType.ELEMENT_PRESENT,
            passed=False,
            confidence=0.3,
            message=f"Element '{text or element_type}' not found",
            evidence={"element_type": element_type, "text": text, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )


_verification_agent: Optional[VerificationAgent] = None


def get_verification_agent() -> VerificationAgent:
    global _verification_agent
    if _verification_agent is None:
        _verification_agent = VerificationAgent()
    return _verification_agent
