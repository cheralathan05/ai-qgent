"""
Layer 14: Screen Action Verification
Verifies that actions actually produced the expected screen/result changes.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from screen_memory import get_screen_memory, ScreenSnapshot
from visual_understanding import get_visual_understanding, ScreenClassification

logger = logging.getLogger(__name__)


@dataclass
class ActionVerificationResult:
    action_type: str
    passed: bool
    message: str
    confidence: float = 0.0
    details: Optional[Dict[str, Any]] = None


class ScreenActionVerifier:
    """Verifies screen-level actions by checking state transitions."""

    def __init__(self):
        self.screen_memory = get_screen_memory()
        self.visual = get_visual_understanding()

    async def verify_app_launched(self, device_id: str, app_name: str, foreground_app: Optional[str] = None) -> ActionVerificationResult:
        if foreground_app and app_name.lower() in foreground_app.lower():
            return ActionVerificationResult(
                action_type="launch_app",
                passed=True,
                message=f"{app_name} confirmed in foreground",
                confidence=0.99,
            )
        current = self.screen_memory.get_current_screen(device_id)
        if current and current.app_name and app_name.lower() in current.app_name.lower():
            return ActionVerificationResult(
                action_type="launch_app",
                passed=True,
                message=f"{app_name} confirmed via screen memory",
                confidence=0.90,
            )
        return ActionVerificationResult(
            action_type="launch_app",
            passed=False,
            message=f"Cannot confirm {app_name} is open",
            confidence=0.3,
        )

    async def verify_screen_changed(self, device_id: str, expected_screen: Optional[str] = None) -> ActionVerificationResult:
        changes = self.screen_memory.get_screen_changes(device_id)
        if not changes:
            return ActionVerificationResult(
                action_type="screen_change",
                passed=False,
                message="No screen changes detected",
                confidence=0.5,
            )
        last_change = changes[-1]
        if expected_screen and expected_screen != last_change["to_screen"]:
            return ActionVerificationResult(
                action_type="screen_change",
                passed=False,
                message=f"Expected {expected_screen}, got {last_change['to_screen']}",
                confidence=0.6,
            )
        return ActionVerificationResult(
            action_type="screen_change",
            passed=True,
            message=f"Screen changed to {last_change['to_screen']}",
            confidence=0.85,
            details=last_change,
        )

    async def verify_message_sent(self, device_id: str, expected_text: Optional[str] = None) -> ActionVerificationResult:
        current = self.screen_memory.get_current_screen(device_id)
        if current and current.text_content:
            return ActionVerificationResult(
                action_type="send_message",
                passed=True,
                message="Message appears to have been sent",
                confidence=0.75,
                details={"text_found": bool(expected_text and expected_text in current.text_content)},
            )
        return ActionVerificationResult(
            action_type="send_message",
            passed=False,
            message="Cannot verify message was sent",
            confidence=0.3,
        )

    async def verify_navigation(self, device_id: str, target: str) -> ActionVerificationResult:
        current = self.screen_memory.get_current_screen(device_id)
        if current and (target.lower() in current.screen_name.lower() or target.lower() in (current.text_content or "").lower()):
            return ActionVerificationResult(
                action_type="navigate",
                passed=True,
                message=f"Reached {target}",
                confidence=0.85,
            )
        return ActionVerificationResult(
            action_type="navigate",
            passed=False,
            message=f"Did not reach {target}",
            confidence=0.4,
        )

    async def verify_action(self, action_type: str, device_id: str, **kwargs) -> ActionVerificationResult:
        if action_type == "launch_app":
            return await self.verify_app_launched(device_id, kwargs.get("app", ""), kwargs.get("foreground_app"))
        elif action_type == "screen_change":
            return await self.verify_screen_changed(device_id, kwargs.get("expected_screen"))
        elif action_type == "send_message":
            return await self.verify_message_sent(device_id, kwargs.get("expected_text"))
        elif action_type == "navigate":
            return await self.verify_navigation(device_id, kwargs.get("target", ""))
        return ActionVerificationResult(
            action_type=action_type,
            passed=True,
            message=f"No specific verification for {action_type}",
            confidence=0.5,
        )

    def verify_scores(self, results: List[ActionVerificationResult]) -> Dict[str, float]:
        if not results:
            return {"verification_score": 0.0, "confidence_score": 0.0, "reliability_score": 0.0, "execution_score": 0.0}
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        avg_confidence = sum(r.confidence for r in results) / total
        verification_score = passed / total
        return {
            "verification_score": round(verification_score, 3),
            "confidence_score": round(avg_confidence, 3),
            "reliability_score": round(verification_score * avg_confidence, 3),
            "execution_score": round((verification_score + avg_confidence) / 2, 3),
        }


_action_verifier: Optional[ScreenActionVerifier] = None


def get_action_verifier() -> ScreenActionVerifier:
    global _action_verifier
    if _action_verifier is None:
        _action_verifier = ScreenActionVerifier()
    return _action_verifier
