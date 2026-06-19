import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np

from vision.screen_capture import ScreenCaptureService, ScreenCaptureResult, get_screen_capture_service
from vision.ocr_service import OCRService, OCRResult, get_ocr_service
from vision.ui_detector import UIDetector, DetectedUIElement, UIDetectionResult, get_ui_detector
from vision.screen_classifier import ScreenClassifier, ScreenClassificationResult, ScreenType, get_screen_classifier
from vision.layout_detector import LayoutDetector, LayoutResult, get_layout_detector
from vision.phone_memory import PhoneMemory, get_phone_memory

logger = logging.getLogger(__name__)


class VisualVerificationType(str, Enum):
    SCREEN_MATCH = "screen_match"
    TEXT_PRESENT = "text_present"
    TEXT_ABSENT = "text_absent"
    ELEMENT_PRESENT = "element_present"
    ELEMENT_ABSENT = "element_absent"
    SCREEN_CHANGE = "screen_change"
    APP_OPENED = "app_opened"
    CHAT_OPENED = "chat_opened"
    MESSAGE_SENT = "message_sent"
    NAVIGATION_COMPLETE = "navigation_complete"
    LAYOUT_MATCH = "layout_match"
    IMAGE_MATCH = "image_match"


@dataclass
class VisualVerificationResult:
    verification_type: VisualVerificationType
    passed: bool
    message: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "type": self.verification_type.value,
            "passed": self.passed,
            "message": self.message,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class VisualVerifier:
    def __init__(self):
        self._capture = get_screen_capture_service()
        self._ocr = get_ocr_service()
        self._ui = get_ui_detector()
        self._classifier = get_screen_classifier()
        self._layout = get_layout_detector()
        self._memory = get_phone_memory()

    async def verify_app_opened(
        self,
        device_id: str,
        expected_app: str,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        for attempt in range(timeout_seconds):
            capture = await self._capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                await asyncio.sleep(1)
                continue

            ocr = await self._ocr.extract_text(capture.image)
            ui_result = await self._ui.detect_elements(capture.image)
            classification = await self._classifier.classify(
                image=capture.image,
                text_content=ocr.full_text,
                ui_result=ui_result,
            )

            expected_lower = expected_app.lower()
            app_in_text = expected_lower in ocr.full_text.lower()
            app_in_class = classification.app_name and expected_lower in classification.app_name.lower()
            app_in_elements = any(
                expected_lower in e.text.lower()
                for e in ui_result.elements if e.text
            )

            if app_in_text or app_in_class or app_in_elements:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.APP_OPENED,
                    passed=True,
                    message=f"App {expected_app} verified open on screen",
                    confidence=0.85,
                    evidence={
                        "expected_app": expected_app,
                        "classified_app": classification.app_name,
                        "screen_type": classification.screen_type.value,
                        "text_found": app_in_text,
                        "attempts": attempt + 1,
                    },
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.APP_OPENED,
            passed=False,
            message=f"App {expected_app} not verified within {timeout_seconds}s",
            confidence=0.5,
            evidence={"expected_app": expected_app, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_chat_opened(
        self,
        device_id: str,
        contact_name: str,
        app_name: str,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        for attempt in range(timeout_seconds):
            capture = await self._capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                await asyncio.sleep(1)
                continue

            ocr = await self._ocr.extract_text(capture.image)
            ui_result = await self._ui.detect_elements(capture.image)
            classification = await self._classifier.classify(
                image=capture.image,
                foreground_app=app_name,
                text_content=ocr.full_text,
                ui_result=ui_result,
            )

            is_chat_screen = classification.screen_type in (
                ScreenType.WHATSAPP_CHAT, ScreenType.INSTAGRAM_DM_CHAT,
                ScreenType.TELEGRAM_CHAT, ScreenType.DISCORD_CHAT,
                ScreenType.MESSENGER_CHAT,
            )
            name_present = contact_name.lower() in ocr.full_text.lower()
            has_input = any(e.element_type == "input" for e in ui_result.elements)
            has_send = any("send" in e.text.lower() for e in ui_result.elements if e.text)

            if is_chat_screen and name_present:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.CHAT_OPENED,
                    passed=True,
                    message=f"Chat with {contact_name} verified on {app_name}",
                    confidence=0.85 if has_input else 0.7,
                    evidence={
                        "contact": contact_name,
                        "app": app_name,
                        "screen_type": classification.screen_type.value,
                        "name_present_in_ocr": name_present,
                        "has_input_field": has_input,
                        "attempts": attempt + 1,
                    },
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.CHAT_OPENED,
            passed=False,
            message=f"Chat with {contact_name} not verified on {app_name}",
            confidence=0.4,
            evidence={"contact": contact_name, "app": app_name, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_message_sent(
        self,
        device_id: str,
        message_text: Optional[str] = None,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        capture_before = await self._capture.capture_from_adb(device_id)
        if not capture_before.success or capture_before.image is None:
            return VisualVerificationResult(
                verification_type=VisualVerificationType.MESSAGE_SENT,
                passed=False,
                message="Could not capture screen before verification",
                confidence=0.0,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

        ocr_before = await self._ocr.extract_text(capture_before.image)

        for attempt in range(max(1, timeout_seconds - 1)):
            await asyncio.sleep(1)
            capture_after = await self._capture.capture_from_adb(device_id)
            if not capture_after.success or capture_after.image is None:
                continue

            ocr_after = await self._ocr.extract_text(capture_after.image)

            diff = self._compute_text_diff(ocr_before.full_text, ocr_after.full_text)

            if message_text:
                msg_lower = message_text.lower()
                text_added = msg_lower in ocr_after.full_text.lower()
                if text_added:
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                    return VisualVerificationResult(
                        verification_type=VisualVerificationType.MESSAGE_SENT,
                        passed=True,
                        message=f"Message text found on screen",
                        confidence=0.9,
                        evidence={
                            "message_snippet": message_text[:50],
                            "attempts": attempt + 2,
                        },
                        duration_ms=elapsed,
                    )

            if diff.get("added", 0) > 2:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.MESSAGE_SENT,
                    passed=True,
                    message="Screen changed, message likely sent",
                    confidence=0.7,
                    evidence={
                        "text_diff": diff,
                        "attempts": attempt + 2,
                    },
                    duration_ms=elapsed,
                )

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.MESSAGE_SENT,
            passed=False,
            message=f"Message not verified as sent within {timeout_seconds}s",
            confidence=0.5,
            evidence={"message_text": message_text, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_text_present(
        self,
        device_id: str,
        text: str,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        for attempt in range(timeout_seconds):
            capture = await self._capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                await asyncio.sleep(1)
                continue

            ocr = await self._ocr.extract_text(capture.image)
            if ocr.has_text(text):
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.TEXT_PRESENT,
                    passed=True,
                    message=f"Text '{text}' found on screen",
                    confidence=0.85,
                    evidence={"search_text": text, "attempts": attempt + 1},
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.TEXT_PRESENT,
            passed=False,
            message=f"Text '{text}' not found on screen",
            confidence=0.5,
            evidence={"search_text": text, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_text_absent(
        self,
        device_id: str,
        text: str,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        for attempt in range(timeout_seconds):
            capture = await self._capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                await asyncio.sleep(1)
                continue

            ocr = await self._ocr.extract_text(capture.image)
            if not ocr.has_text(text):
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.TEXT_ABSENT,
                    passed=True,
                    message=f"Text '{text}' no longer on screen",
                    confidence=0.85,
                    evidence={"search_text": text, "attempts": attempt + 1},
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.TEXT_ABSENT,
            passed=False,
            message=f"Text '{text}' still on screen after {timeout_seconds}s",
            confidence=0.5,
            evidence={"search_text": text, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_screen_type(
        self,
        device_id: str,
        expected_screen: ScreenType,
        expected_app: Optional[str] = None,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        for attempt in range(timeout_seconds):
            capture = await self._capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                await asyncio.sleep(1)
                continue

            ocr = await self._ocr.extract_text(capture.image)
            ui_result = await self._ui.detect_elements(capture.image)
            classification = await self._classifier.classify(
                image=capture.image,
                foreground_app=expected_app,
                text_content=ocr.full_text,
                ui_result=ui_result,
            )

            if classification.screen_type == expected_screen:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.SCREEN_MATCH,
                    passed=True,
                    message=f"Screen is {expected_screen.value}",
                    confidence=classification.confidence,
                    evidence={
                        "expected": expected_screen.value,
                        "detected": classification.screen_type.value,
                        "confidence": classification.confidence,
                        "attempts": attempt + 1,
                    },
                    duration_ms=elapsed,
                )

            await asyncio.sleep(1)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.SCREEN_MATCH,
            passed=False,
            message=f"Screen did not become {expected_screen.value}",
            confidence=0.4,
            evidence={"expected": expected_screen.value, "timeout_seconds": timeout_seconds},
            duration_ms=elapsed,
        )

    async def verify_screen_changed(
        self,
        device_id: str,
        timeout_seconds: int = 10,
    ) -> VisualVerificationResult:
        start = datetime.utcnow()
        before_capture = await self._capture.capture_from_adb(device_id)
        if not before_capture.success or before_capture.image is None:
            return VisualVerificationResult(
                verification_type=VisualVerificationType.SCREEN_CHANGE,
                passed=False, message="Could not capture initial screen",
                confidence=0.0,
                duration_ms=(datetime.utcnow() - start).total_seconds() * 1000,
            )

        ocr_before = await self._ocr.extract_text(before_capture.image)
        ui_before = await self._ui.detect_elements(before_capture.image)

        for attempt in range(timeout_seconds):
            await asyncio.sleep(1)
            after_capture = await self._capture.capture_from_adb(device_id)
            if not after_capture.success or after_capture.image is None:
                continue

            ocr_after = await self._ocr.extract_text(after_capture.image)

            text_diff = ocr_before.full_text != ocr_after.full_text
            if text_diff and len(ocr_after.full_text) > 0:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return VisualVerificationResult(
                    verification_type=VisualVerificationType.SCREEN_CHANGE,
                    passed=True,
                    message="Screen content changed",
                    confidence=0.75,
                    evidence={
                        "text_changed": True,
                        "attempts": attempt + 2,
                    },
                    duration_ms=elapsed,
                )

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return VisualVerificationResult(
            verification_type=VisualVerificationType.SCREEN_CHANGE,
            passed=False, message="Screen did not change",
            confidence=0.4,
            duration_ms=elapsed,
        )

    @staticmethod
    def _compute_text_diff(before: str, after: str) -> Dict[str, Any]:
        before_words = set(before.lower().split())
        after_words = set(after.lower().split())
        added = after_words - before_words
        removed = before_words - after_words
        return {
            "added": len(added),
            "removed": len(removed),
            "added_words": list(added)[:10],
            "removed_words": list(removed)[:10],
        }

    async def full_verification_pipeline(
        self,
        device_id: str,
        expected_screen: Optional[ScreenType] = None,
        expected_app: Optional[str] = None,
        expected_text: Optional[str] = None,
        verify_text_absent: Optional[str] = None,
        timeout_seconds: int = 10,
    ) -> List[VisualVerificationResult]:
        results = []

        capture = await self._capture.capture_from_adb(device_id)
        if not capture.success:
            results.append(VisualVerificationResult(
                verification_type=VisualVerificationType.SCREEN_MATCH,
                passed=False, message=f"Capture failed: {capture.error}",
                confidence=0.0,
            ))
            return results

        ocr = await self._ocr.extract_text(capture.image)
        ui_result = await self._ui.detect_elements(capture.image)
        classification = await self._classifier.classify(
            image=capture.image,
            foreground_app=expected_app,
            text_content=ocr.full_text,
            ui_result=ui_result,
        )

        if expected_screen:
            screen_match = classification.screen_type == expected_screen
            results.append(VisualVerificationResult(
                verification_type=VisualVerificationType.SCREEN_MATCH,
                passed=screen_match,
                message=f"Screen is {classification.screen_type.value} (expected {expected_screen.value})",
                confidence=classification.confidence if screen_match else 0.4,
                evidence={
                    "expected": expected_screen.value,
                    "detected": classification.screen_type.value,
                    "classification_confidence": classification.confidence,
                    "reason": classification.classification_reason,
                },
            ))

        if expected_text:
            text_found = ocr.has_text(expected_text)
            results.append(VisualVerificationResult(
                verification_type=VisualVerificationType.TEXT_PRESENT,
                passed=text_found,
                message=f"Text '{expected_text}' {'found' if text_found else 'not found'} on screen",
                confidence=0.85 if text_found else 0.5,
                evidence={"search_text": expected_text, "found": text_found},
            ))

        if verify_text_absent:
            text_gone = not ocr.has_text(verify_text_absent)
            results.append(VisualVerificationResult(
                verification_type=VisualVerificationType.TEXT_ABSENT,
                passed=text_gone,
                message=f"Text '{verify_text_absent}' {'absent' if text_gone else 'still present'}",
                confidence=0.85 if text_gone else 0.5,
                evidence={"search_text": verify_text_absent, "absent": text_gone},
            ))

        return results


_visual_verifier: Optional[VisualVerifier] = None


def get_visual_verifier() -> VisualVerifier:
    global _visual_verifier
    if _visual_verifier is None:
        _visual_verifier = VisualVerifier()
    return _visual_verifier
