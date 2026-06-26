import logging
from typing import Dict, Any, Optional, List
from .models import AgenticAction, PerceivedState, ActionOutcome

logger = logging.getLogger(__name__)

class RecoveryEngine:
    """
    Handles failures in the agentic loop by applying recovery strategies.
    Returns a new suggested Action or a signal to re-plan.
    """
    def __init__(self):
        pass

    async def handle_failure(self, device_id: str, action: AgenticAction,
                            outcome: ActionOutcome, current_state: PerceivedState) -> Optional[AgenticAction]:
        """
        Analyzes the failure and returns a recovery action if possible.
        """
        logger.warning(f"Recovery engine triggered for action {action.action_type} on target {action.target}")

        # Strategy 1: If it was a TAP and target not found, try a 'search' for similar labels
        if action.action_type.value == "tap":
            recovery_action = await self._attempt_semantic_recovery(action, current_state)
            if recovery_action:
                return recovery_action

        # Strategy 2: If target is missing, try going back to the previous screen
        if not self._is_target_visible(action.target, current_state):
            logger.info("Target not visible, attempting to go back")
            from .models import ActionType
            return AgenticAction(
                action_type=ActionType.BACK,
                target="previous_screen",
                description="Going back to find the missing element"
            )

        # Strategy 3: If all else fails, signal re-planning (return None)
        logger.info("No specific recovery action found, requesting re-plan")
        return None

    async def _attempt_semantic_recovery(self, action: AgenticAction, state: PerceivedState) -> Optional[AgenticAction]:
        """
        Tries to find a similar label to the target in the current state.
        """
        target = action.target.lower()

        # Look for partial matches in the elements
        for el in state.elements:
            label = el.label.lower()
            if target in label or label in target:
                logger.info(f"Semantic recovery: found similar element '{label}' for target '{target}'")
                from .models import ActionType
                return AgenticAction(
                    action_type=ActionType.TAP,
                    target=el.label, # Use the actual found label
                    description=f"Recovery tap on similar element {el.label}"
                )

        return None

    def _is_target_visible(self, target: str, state: PerceivedState) -> bool:
        """Checks if the target label is present in the perceived state."""
        target = target.lower()
        return any(target in el.label.lower() for el in state.elements)

def get_recovery_engine() -> RecoveryEngine:
    return RecoveryEngine()
