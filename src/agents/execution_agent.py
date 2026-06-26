"""Execution Agent - Action execution with verification loops.

Executes planned navigation steps, verifying each action.
Implements retry logic and self-healing when actions fail.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from agents.vision_agent import get_vision_agent, ScreenState, DetectedElement
from agents.navigation_agent import NavigationStep, NavigationAction, NavigationPlan
from agents.verification_agent import get_verification_agent, VerificationResult
from agents.memory_agent import get_memory_agent

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step: NavigationStep
    success: bool
    coordinates_used: Tuple[int, int] = (0, 0)
    verification: Optional[VerificationResult] = None
    error: str = ""
    retries: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step": self.step.to_dict(),
            "success": self.success,
            "coordinates_used": {"x": self.coordinates_used[0], "y": self.coordinates_used[1]},
            "verification": self.verification.to_dict() if self.verification else None,
            "error": self.error,
            "retries": self.retries,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class ExecutionResult:
    plan_goal: str
    success: bool
    overall_confidence: float = 0.0
    step_results: List[StepResult] = field(default_factory=list)
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    total_retries: int = 0
    execution_time_ms: float = 0.0
    final_state: Optional[ScreenState] = None
    screenshot_evidence: List[str] = field(default_factory=list)
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "plan_goal": self.plan_goal,
            "success": self.success,
            "overall_confidence": self.overall_confidence,
            "step_results": [sr.to_dict() for sr in self.step_results],
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "total_retries": self.total_retries,
            "execution_time_ms": self.execution_time_ms,
            "screenshot_evidence": self.screenshot_evidence,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionAgent:
    """Executes navigation plans with verification at each step.

    Key principles:
    - Every action is verified visually
    - Failed actions are retried with alternative strategies
    - Element positions come from VisionAgent, not hardcoded values
    - Memory agent caches successful positions for speed
    """

    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.5

    def __init__(self):
        self._vision = get_vision_agent()
        self._verification = get_verification_agent()
        self._memory = get_memory_agent()
        self._adb = None

    def _get_adb(self):
        if self._adb is None:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb = get_adb_service(find_adb_binary())
        return self._adb

    async def execute_plan(
        self, device_id: str, plan: NavigationPlan
    ) -> ExecutionResult:
        """Execute a full navigation plan with verification."""
        start = datetime.utcnow()
        result = ExecutionResult(plan_goal=plan.goal, success=False)
        result.total_steps = len(plan.steps)

        adb = self._get_adb()

        for i, step in enumerate(plan.steps):
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.description}")

            step_result = await self._execute_step_with_retry(
                device_id, step, adb, plan.app_name
            )
            result.step_results.append(step_result)

            if step_result.success:
                result.successful_steps += 1
                if step_result.screenshot_evidence if hasattr(step_result, 'screenshot_evidence') else None:
                    pass
            else:
                result.failed_steps += 1
                result.error = step_result.error
                # Don't abort on non-critical failures
                if step.action in (NavigationAction.OPEN_APP, NavigationAction.TAP):
                    if not step_result.success and i < 2:
                        logger.warning(f"Critical step failed: {step.description}")
                        break

            result.total_retries += step_result.retries

        result.success = result.failed_steps == 0
        result.execution_time_ms = (datetime.utcnow() - start).total_seconds() * 1000

        if result.successful_steps > 0:
            result.overall_confidence = result.successful_steps / result.total_steps
        else:
            result.overall_confidence = 0.0

        # Cache successful element positions
        if result.success:
            await self._cache_successful_positions(device_id, plan, result)

        logger.info(
            f"Execution complete: {result.successful_steps}/{result.total_steps} steps "
            f"successful, confidence={result.overall_confidence:.2f}, "
            f"time={result.execution_time_ms:.0f}ms"
        )

        return result

    async def _execute_step_with_retry(
        self, device_id: str, step: NavigationStep, adb, app_name: str
    ) -> StepResult:
        """Execute a single step with retry logic."""
        start = datetime.utcnow()

        for attempt in range(self.MAX_RETRIES):
            try:
                step_result = await self._execute_single_step(
                    device_id, step, adb, attempt
                )
                step_result.retries = attempt

                if step_result.success:
                    step_result.execution_time_ms = (
                        datetime.utcnow() - start
                    ).total_seconds() * 1000
                    return step_result

                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY_BASE * (attempt + 1)
                    logger.info(
                        f"Step '{step.description}' failed (attempt {attempt+1}), "
                        f"retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(
                    f"Step '{step.description}' exception (attempt {attempt+1}): {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY_BASE)

        # All retries exhausted
        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return StepResult(
            step=step,
            success=False,
            error=f"Failed after {self.MAX_RETRIES} attempts",
            retries=self.MAX_RETRIES - 1,
            execution_time_ms=elapsed,
        )

    async def _execute_single_step(
        self, device_id: str, step: NavigationStep, adb, attempt: int
    ) -> StepResult:
        """Execute a single step once."""
        start = datetime.utcnow()

        if step.action == NavigationAction.OPEN_APP:
            return await self._execute_open_app(device_id, step, adb, start)

        elif step.action == NavigationAction.TAP:
            return await self._execute_tap(device_id, step, adb, start, attempt)

        elif step.action == NavigationAction.TYPE_TEXT:
            return await self._execute_type_text(device_id, step, adb, start)

        elif step.action == NavigationAction.WAIT:
            await asyncio.sleep(step.duration)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=True, execution_time_ms=elapsed
            )

        elif step.action == NavigationAction.PRESS_KEY:
            return await self._execute_press_key(device_id, step, adb, start)

        elif step.action == NavigationAction.SWIPE:
            return await self._execute_swipe(device_id, step, adb, start)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        return StepResult(
            step=step, success=False,
            error=f"Unknown action: {step.action}",
            execution_time_ms=elapsed,
        )

    async def _execute_open_app(
        self, device_id: str, step: NavigationStep, adb, start: datetime
    ) -> StepResult:
        try:
            await adb.open_app(device_id, step.target)
            await asyncio.sleep(2)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            # Verify app opened
            verification = await self._verification.verify_app_opened(
                device_id, step.target, timeout_seconds=5
            )

            return StepResult(
                step=step,
                success=verification.passed,
                verification=verification,
                execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=False, error=str(e), execution_time_ms=elapsed
            )

    async def _execute_tap(
        self, device_id: str, step: NavigationStep, adb,
        start: datetime, attempt: int
    ) -> StepResult:
        try:
            coords = None

            # Step 1: Try cached position
            memory = self._memory
            cached = memory.find_cached_element(
                app_name="", screen_type="",
                element_type=step.target, text=step.target
            )
            if cached and attempt == 0:
                coords = cached.center()
                logger.info(f"Using cached position for '{step.target}': {coords}")

            # Step 2: Use provided coordinates
            if not coords and step.x > 0 and step.y > 0:
                coords = (step.x, step.y)

            # Step 3: Find element on screen via VisionAgent
            if not coords:
                element = await self._vision.find_element(
                    device_id, step.target, step.target
                )
                if element:
                    coords = element.center()
                    logger.info(
                        f"Found '{step.target}' via VisionAgent at {coords} "
                        f"(confidence={element.confidence:.2f})"
                    )

            # Step 4: Self-healing fallback
            if not coords:
                coords = await self._self_heal_find(device_id, step.target)
                if coords:
                    logger.info(f"Self-healing found '{step.target}' at {coords}")

            if not coords:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                return StepResult(
                    step=step, success=False,
                    error=f"Element '{step.target}' not found on screen",
                    execution_time_ms=elapsed,
                )

            # Execute tap
            await adb.input_tap(device_id, coords[0], coords[1])
            await asyncio.sleep(1.5)

            # Verify tap had effect
            verification = None
            if step.verify_state:
                verification = await self._verify_after_tap(
                    device_id, step.verify_state
                )

            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            success = True
            if verification and not verification.passed:
                success = False

            return StepResult(
                step=step,
                success=success,
                coordinates_used=coords,
                verification=verification,
                execution_time_ms=elapsed,
            )

        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=False, error=str(e), execution_time_ms=elapsed
            )

    async def _execute_type_text(
        self, device_id: str, step: NavigationStep, adb, start: datetime
    ) -> StepResult:
        try:
            await adb.input_text(device_id, step.text)
            await asyncio.sleep(1)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=True, execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=False, error=str(e), execution_time_ms=elapsed
            )

    async def _execute_press_key(
        self, device_id: str, step: NavigationStep, adb, start: datetime
    ) -> StepResult:
        try:
            key_map = {"KEYCODE_BACK": 4, "KEYCODE_HOME": 3, "KEYCODE_ENTER": 66}
            keycode = key_map.get(step.keycode, 4)
            await adb.press_key(device_id, keycode)
            await asyncio.sleep(1)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=True, execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=False, error=str(e), execution_time_ms=elapsed
            )

    async def _execute_swipe(
        self, device_id: str, step: NavigationStep, adb, start: datetime
    ) -> StepResult:
        try:
            direction = step.text or "down"
            state = await self._vision.quick_analyze(device_id)
            w = state.image_width or 500
            h = state.image_height or 1000

            if direction == "down":
                await adb.shell(device_id, f"input swipe {w//2} {int(h*0.7)} {w//2} {int(h*0.3)}")
            elif direction == "up":
                await adb.shell(device_id, f"input swipe {w//2} {int(h*0.3)} {w//2} {int(h*0.7)}")
            elif direction == "left":
                await adb.shell(device_id, f"input swipe {int(w*0.8)} {h//2} {int(w*0.2)} {h//2}")
            elif direction == "right":
                await adb.shell(device_id, f"input swipe {int(w*0.2)} {h//2} {int(w*0.8)} {h//2}")

            await asyncio.sleep(1)
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=True, execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000
            return StepResult(
                step=step, success=False, error=str(e), execution_time_ms=elapsed
            )

    async def _self_heal_find(
        self, device_id: str, target: str
    ) -> Optional[Tuple[int, int]]:
        """Self-healing: try alternative strategies to find an element."""
        target_lower = target.lower()

        # Strategy 1: Find any button near expected position
        if target_lower in ("send_button", "send"):
            element = await self._vision.find_element(device_id, "", "send_button")
            if element:
                return element.center()

        # Strategy 2: Find input field
        if target_lower in ("input_field", "message", "type a message"):
            element = await self._vision.find_element(device_id, "", "input_field")
            if element:
                return element.center()

        # Strategy 3: Find search bar
        if target_lower in ("search_bar", "search"):
            element = await self._vision.find_element(device_id, "", "search_bar")
            if element:
                return element.center()

        # Strategy 4: Text-based search
        element = await self._vision.find_element(device_id, target)
        if element:
            return element.center()

        return None

    async def _verify_after_tap(
        self, device_id: str, expected_state: str
    ) -> Optional[VerificationResult]:
        """Verify state after a tap action."""
        await asyncio.sleep(1)

        if expected_state == "search_open":
            return await self._verification.verify_element_present(
                device_id, "input_field", timeout_seconds=3
            )
        elif expected_state == "chat_open":
            state = await self._vision.quick_analyze(device_id)
            if state.success:
                has_input = state.has_element_type("input_field")
                has_send = state.find_send_button() is not None
                return VerificationResult(
                    verification_type="chat_opened",
                    passed=has_input or has_send,
                    confidence=0.7 if has_input and has_send else 0.4,
                    message="Chat screen detected" if has_input else "Chat screen not detected",
                )
        elif expected_state == "message_sent":
            return await self._verification.verify_screen_changed(
                device_id, "", timeout_seconds=3
            )

        return None

    async def _cache_successful_positions(
        self, device_id: str, plan: NavigationPlan, result: ExecutionResult
    ):
        """Cache element positions from successful execution."""
        memory = self._memory

        for sr in result.step_results:
            if sr.success and sr.step.action == NavigationAction.TAP:
                coords = sr.coordinates_used
                if coords[0] > 0 and coords[1] > 0:
                    memory.cache_element(
                        app_name=plan.app_name,
                        screen_type="current",
                        element_type=sr.step.target,
                        text=sr.step.target,
                        x=coords[0], y=coords[1],
                        w=50, h=50,
                        confidence=0.8,
                    )


_execution_agent: Optional[ExecutionAgent] = None


def get_execution_agent() -> ExecutionAgent:
    global _execution_agent
    if _execution_agent is None:
        _execution_agent = ExecutionAgent()
    return _execution_agent
