import logging
from typing import Dict, Any, Optional
from .models import ActionOutcome, PerceivedState

logger = logging.getLogger(__name__)

class VerificationEngine:
    """
    Verifies if an action achieved its intended effect
    by comparing before and after states.
    """
    def __init__(self):
        pass

    async def verify(self, outcome: ActionOutcome) -> bool:
        """
        Main verification entry point.
        """
        state_before = outcome.state_before
        state_after = outcome.state_after
        action = outcome.action

        if not outcome.success:
            return False

        # Verification logic based on action type
        if action.action_type.value == "tap":
            return await self._verify_tap(action, state_before, state_after)
        elif action.action_type.value == "type":
            return await self._verify_type(action, state_before, state_after)
        elif action.action_type.value == "open_app":
            return await self._verify_app_opened(action, state_before, state_after)

        # Default: return true if state changed significantly
        return state_before.elements != state_after.elements

    async def _verify_tap(self, action, before: PerceivedState, after: PerceivedState) -> bool:
        """
        Verify a tap: either the target disappeared (confirmation)
        or the screen changed (navigation).
        """
        target = action.target.lower()

        # Case 1: Target was a button that should trigger a screen change
        if before.screen_type != after.screen_type:
            return True

        # Case 2: Target was a button that should disappear (e.g. "Submit")
        was_present = any(target in el.label.lower() for el in before.elements)
        is_present = any(target in el.label.lower() for el in after.elements)

        if was_present and not is_present:
            return True

        # Case 3: Some other element appeared as a result
        # (This is generic and might need more specific logic per action)
        return False

    async def _verify_type(self, action, before: PerceivedState, after: PerceivedState) -> bool:
        """Verify that text was actually typed into the field."""
        text = action.params.get("text", "")
        if not text:
            return True

        # Check if the text now appears in the screen's full text
        return text.lower() in after.full_text.lower()

    async def _verify_app_opened(self, action, before: PerceivedState, after: PerceivedState) -> bool:
        """Verify that the requested app is now in the foreground."""
        app = action.target.lower()
        if after.current_app and app in after.current_app.lower():
            return True
        return False

def get_verification_engine() -> VerificationEngine:
    return VerificationEngine()
