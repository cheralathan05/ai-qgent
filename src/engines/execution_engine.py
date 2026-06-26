import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from .models import AgenticAction, ActionOutcome, PerceivedState, ActionType
from services.adb_service import get_adb_service, find_adb_binary
from .perception_engine import get_perception_engine

logger = logging.getLogger(__name__)

class ActionExecutionEngine:
    """
    Executes AgenticActions on the Android device,
    providing state snapshots before and after.
    """
    def __init__(self):
        self.adb = get_adb_service(find_adb_binary())
        self.perception = get_perception_engine()

    async def execute(self, device_id: str, action: AgenticAction) -> ActionOutcome:
        """Execute an action with state snapshotting."""

        # 1. Capture State Before
        state_before = await self.perception.perceive(device_id)

        # 2. Resolve Target to Coordinates
        coords = await self._resolve_target(device_id, action, state_before)

        success = False
        error = None

        try:
            # 3. Perform the action
            if action.action_type == ActionType.TAP:
                if coords:
                    await self.adb.input_tap(device_id, coords[0], coords[1])
                    success = True
                else:
                    error = f"Could not resolve target '{action.target}' to coordinates"

            elif action.action_type == ActionType.TYPE:
                text = action.params.get("text", "")
                await self.adb.input_text(device_id, text)
                success = True

            elif action.action_type == ActionType.SCROLL:
                direction = action.params.get("direction", "down")
                if direction == "down":
                    await self.adb.shell(device_id, "input swipe 500 1000 500 200")
                elif direction == "up":
                    await self.adb.shell(device_id, "input swipe 500 200 500 1000")
                success = True

            elif action.action_type == ActionType.BACK:
                await self.adb.press_back(device_id)
                success = True

            elif action.action_type == ActionType.HOME:
                await self.adb.press_home(device_id)
                success = True

            elif action.action_type == ActionType.OPEN_APP:
                app = action.target
                await self.adb.open_app(device_id, app)
                success = True

            else:
                error = f"Unsupported action type: {action.action_type}"

            await asyncio.sleep(1.5) # Stabilization delay

        except Exception as e:
            logger.exception(f"Action execution failed: {e}")
            error = str(e)
            success = False

        # 4. Capture State After
        state_after = await self.perception.perceive(device_id)

        return ActionOutcome(
            action=action,
            success=success,
            state_before=state_before,
            state_after=state_after,
            error=error
        )

    async def _resolve_target(self, device_id: str, action: AgenticAction, state: PerceivedState) -> Optional[Tuple[int, int]]:
        """
        Resolves a semantic target to (x, y) coordinates.
        Implementation: Accessibility Tree -> Vision Analysis -> Fallback.
        """
        target = action.target.lower()

        # 1. Try to find a match in the PerceivedState elements
        # Sorted by confidence and source (Accessibility > Vision)
        best_match = None
        max_score = -1.0

        for el in state.elements:
            score = 0.0
            label = el.label.lower()

            if label == target:
                score = 1.0
            elif target in label or label in target:
                score = 0.7

            # Boost score based on source
            if el.source == "accessibility":
                score += 0.2
            elif el.source == "vision":
                score += 0.1

            if score > max_score:
                max_score = score
                best_match = el

        if best_match and max_score > 0.5:
            bbox = best_match.bbox # [x, y, w, h]
            if bbox and any(bbox):
                # Calculate center
                center_x = int(bbox[0] + bbox[2]/2)
                center_y = int(bbox[1] + bbox[3]/2)
                return (center_x, center_y)

        # 2. Fallback: If coordinates are provided in params
        if "x" in action.params and "y" in action.params:
            return (action.params["x"], action.params["y"])

        return None

def get_execution_engine() -> ActionExecutionEngine:
    return ActionExecutionEngine()
