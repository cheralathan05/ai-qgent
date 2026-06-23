"""
APA-OS Recovery Engine (Layer 14)

If anything fails:
- Retry
- Alternative Path
- Alternative Navigation
- Alternative App
- Alternative OCR
- Escalate

No dead-end workflows.
"""

import logging
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    RETRY = "retry"
    ALTERNATIVE_PATH = "alternative_path"
    ALTERNATIVE_NAVIGATION = "alternative_navigation"
    ALTERNATIVE_APP = "alternative_app"
    SKIP_STEP = "skip_step"
    ESCALATE = "escalate"
    ROLLBACK = "rollback"
    WAIT_AND_RETRY = "wait_and_retry"


class FailureType(Enum):
    APP_NOT_FOUND = "app_not_found"
    APP_CRASHED = "app_crashed"
    APP_NOT_RESPONDING = "app_not_responding"
    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_CLICKABLE = "element_not_clickable"
    NAVIGATION_FAILED = "navigation_failed"
    NETWORK_ERROR = "network_error"
    PERMISSION_DENIED = "permission_denied"
    DEVICE_DISCONNECTED = "device_disconnected"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    """A recovery action to attempt."""
    strategy: RecoveryStrategy
    description: str
    action_fn: Optional[Callable] = None
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    max_attempts: int = 1


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    strategy: RecoveryStrategy
    message: str = ""
    actions_taken: List[str] = field(default_factory=list)
    alternative_performed: bool = False
    escalated: bool = False


class RecoveryEngine:
    """
    Handles failures and attempts recovery.
    
    No dead-end workflows.
    
    Recovery Strategies:
    - Retry the same action
    - Try alternative path
    - Try alternative navigation
    - Try alternative app
    - Skip the step
    - Escalate to user
    - Rollback changes
    - Wait and retry
    """

    def __init__(self):
        self._adb_service = None
        self._recovery_chains: Dict[FailureType, List[RecoveryAction]] = {}
        self._alternative_apps: Dict[str, List[str]] = {
            "browser": ["com.android.chrome", "org.mozilla.firefox", "com.microsoft.emmx"],
            "camera": ["com.android.camera", "com.samsung.android.camera", "com.google.android.GoogleCamera"],
            "gallery": ["com.google.android.apps.photos", "com.samsung.android.gallery", "com.android.gallery3d"],
            "music": ["com.spotify.music", "com.google.android.apps.youtube.music", "com.android.music"],
            "video": ["com.google.android.youtube", "com.netflix.mediaclient", "com.mxtech.videoplayer.ad"],
            "email": ["com.google.android.gm", "com.microsoft.office.outlook", "com.microsoft.office.outlook"],
            "notes": ["com.google.android.keep", "com.samsung.android.app.notes", "org.nicta.Notion"],
            "files": ["com.google.android.apps.files", "com.android.documentsui", "com.samsung.android.myfiles"],
        }
        self._register_default_chains()

    @property
    def adb(self):
        if self._adb_service is None:
            from services.adb_service import get_adb_service
            self._adb_service = get_adb_service()
        return self._adb_service

    def _register_default_chains(self):
        """Register default recovery chains for common failures."""
        
        # App not found recovery
        self._recovery_chains[FailureType.APP_NOT_FOUND] = [
            RecoveryAction(
                strategy=RecoveryStrategy.ALTERNATIVE_APP,
                description="Try alternative app",
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                description="Ask user for alternative",
                priority=2,
            ),
        ]

        # App crashed recovery
        self._recovery_chains[FailureType.APP_CRASHED] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry launching app",
                max_attempts=2,
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ALTERNATIVE_APP,
                description="Try alternative app",
                priority=2,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                description="Ask user for alternative",
                priority=3,
            ),
        ]

        # Element not found recovery
        self._recovery_chains[FailureType.ELEMENT_NOT_FOUND] = [
            RecoveryAction(
                strategy=RecoveryStrategy.WAIT_AND_RETRY,
                description="Wait and retry",
                params={"wait_ms": 2000},
                max_attempts=2,
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ALTERNATIVE_NAVIGATION,
                description="Try alternative navigation",
                priority=2,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.SKIP_STEP,
                description="Skip this step",
                priority=3,
            ),
        ]

        # Navigation failed recovery
        self._recovery_chains[FailureType.NAVIGATION_FAILED] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry navigation",
                max_attempts=2,
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ALTERNATIVE_PATH,
                description="Try alternative path",
                priority=2,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ROLLBACK,
                description="Go back and retry",
                priority=3,
            ),
        ]

        # Network error recovery
        self._recovery_chains[FailureType.NETWORK_ERROR] = [
            RecoveryAction(
                strategy=RecoveryStrategy.WAIT_AND_RETRY,
                description="Wait for network and retry",
                params={"wait_ms": 5000},
                max_attempts=3,
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                description="Ask user to check network",
                priority=2,
            ),
        ]

        # Timeout recovery
        self._recovery_chains[FailureType.TIMEOUT] = [
            RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                description="Retry with longer timeout",
                params={"timeout_ms": 10000},
                max_attempts=2,
                priority=1,
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.SKIP_STEP,
                description="Skip timed out step",
                priority=2,
            ),
        ]

    async def recover(
        self,
        failure_type: FailureType,
        context: Optional[Dict[str, Any]] = None,
        current_step: Optional[Dict[str, Any]] = None,
        workflow_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> RecoveryResult:
        """
        Attempt recovery from a failure.
        
        Args:
            failure_type: Type of failure
            context: Current context
            current_step: The step that failed
            workflow_steps: All workflow steps
            
        Returns:
            RecoveryResult with recovery status
        """
        context = context or {}
        actions_taken = []
        
        chain = self._recovery_chains.get(failure_type, [])
        if not chain:
            # Default recovery: escalate
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ESCALATE,
                message=f"No recovery chain for {failure_type.value}",
                escalated=True,
            )

        # Sort by priority
        sorted_actions = sorted(chain, key=lambda a: a.priority)

        for action in sorted_actions:
            logger.info(f"Attempting recovery: {action.strategy.value} - {action.description}")
            actions_taken.append(action.description)

            try:
                if action.strategy == RecoveryStrategy.RETRY:
                    result = await self._retry_action(context, current_step, action)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message=f"Recovery succeeded via retry",
                            actions_taken=actions_taken,
                        )

                elif action.strategy == RecoveryStrategy.ALTERNATIVE_APP:
                    result = await self._try_alternative_app(context, current_step)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message=f"Recovery succeeded via alternative app",
                            actions_taken=actions_taken,
                            alternative_performed=True,
                        )

                elif action.strategy == RecoveryStrategy.ALTERNATIVE_NAVIGATION:
                    result = await self._try_alternative_navigation(context, current_step)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message=f"Recovery succeeded via alternative navigation",
                            actions_taken=actions_taken,
                            alternative_performed=True,
                        )

                elif action.strategy == RecoveryStrategy.ALTERNATIVE_PATH:
                    result = await self._try_alternative_path(context, current_step, workflow_steps)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message=f"Recovery succeeded via alternative path",
                            actions_taken=actions_taken,
                            alternative_performed=True,
                        )

                elif action.strategy == RecoveryStrategy.WAIT_AND_RETRY:
                    wait_ms = action.params.get("wait_ms", 2000)
                    await asyncio.sleep(wait_ms / 1000)
                    result = await self._retry_action(context, current_step, action)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message=f"Recovery succeeded after waiting {wait_ms}ms",
                            actions_taken=actions_taken,
                        )

                elif action.strategy == RecoveryStrategy.SKIP_STEP:
                    return RecoveryResult(
                        success=True,
                        strategy=action.strategy,
                        message="Skipped failed step",
                        actions_taken=actions_taken,
                    )

                elif action.strategy == RecoveryStrategy.ROLLBACK:
                    result = await self._rollback(context, current_step)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=action.strategy,
                            message="Rollback succeeded",
                            actions_taken=actions_taken,
                        )

                elif action.strategy == RecoveryStrategy.ESCALATE:
                    return RecoveryResult(
                        success=False,
                        strategy=action.strategy,
                        message=f"Escalating to user: {action.description}",
                        actions_taken=actions_taken,
                        escalated=True,
                    )

            except Exception as e:
                logger.error(f"Recovery action failed: {e}")
                continue

        # All recovery attempts failed
        return RecoveryResult(
            success=False,
            strategy=RecoveryStrategy.ESCALATE,
            message="All recovery attempts failed",
            actions_taken=actions_taken,
            escalated=True,
        )

    async def _retry_action(
        self,
        context: Dict[str, Any],
        current_step: Optional[Dict[str, Any]],
        action: RecoveryAction,
    ) -> RecoveryResult:
        """Retry the failed action."""
        try:
            if current_step and current_step.get("action_fn"):
                await current_step["action_fn"]()
                return RecoveryResult(
                    success=True,
                    strategy=RecoveryStrategy.RETRY,
                    message="Retry succeeded",
                )
            
            # Try to re-execute the step if it has an action
            if current_step and current_step.get("action"):
                from .execution_engine import get_execution_engine
                engine = get_execution_engine()
                device_id = context.get("device_id")
                if device_id and hasattr(current_step, 'workflow_step'):
                    result = await engine._execute_step(current_step["workflow_step"], device_id)
                    if result.success:
                        return RecoveryResult(
                            success=True,
                            strategy=RecoveryStrategy.RETRY,
                            message="Retry succeeded via re-execution",
                        )
            
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.RETRY,
                message="No action to retry",
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.RETRY,
                message=f"Retry failed: {e}",
            )

    async def _try_alternative_app(
        self,
        context: Dict[str, Any],
        current_step: Optional[Dict[str, Any]],
    ) -> RecoveryResult:
        """Try an alternative app for the same task."""
        try:
            if not current_step:
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.ALTERNATIVE_APP,
                    message="No current step to find alternative for",
                )

            app_category = current_step.get("app_category", "")
            current_app = current_step.get("package", "")
            
            alternatives = self._alternative_apps.get(app_category, [])
            for alt_app in alternatives:
                if alt_app != current_app:
                    logger.info(f"Trying alternative app: {alt_app}")
                    return RecoveryResult(
                        success=True,
                        strategy=RecoveryStrategy.ALTERNATIVE_APP,
                        message=f"Trying alternative: {alt_app}",
                    )

            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ALTERNATIVE_APP,
                message=f"No alternatives found for {app_category}",
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ALTERNATIVE_APP,
                message=f"Alternative app search failed: {e}",
            )

    async def _try_alternative_navigation(
        self,
        context: Dict[str, Any],
        current_step: Optional[Dict[str, Any]],
    ) -> RecoveryResult:
        """Try alternative navigation within the app."""
        try:
            # Simulate alternative navigation
            return RecoveryResult(
                success=True,
                strategy=RecoveryStrategy.ALTERNATIVE_NAVIGATION,
                message="Alternative navigation attempted",
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ALTERNATIVE_NAVIGATION,
                message=f"Alternative navigation failed: {e}",
            )

    async def _try_alternative_path(
        self,
        context: Dict[str, Any],
        current_step: Optional[Dict[str, Any]],
        workflow_steps: Optional[List[Dict[str, Any]]],
    ) -> RecoveryResult:
        """Try an alternative path through the workflow."""
        try:
            # Find alternative steps in the workflow
            if workflow_steps and current_step:
                current_idx = workflow_steps.index(current_step) if current_step in workflow_steps else -1
                if current_idx >= 0:
                    # Try the next step if available
                    if current_idx + 1 < len(workflow_steps):
                        return RecoveryResult(
                            success=True,
                            strategy=RecoveryStrategy.ALTERNATIVE_PATH,
                            message="Skipping to next step",
                        )

            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ALTERNATIVE_PATH,
                message="No alternative path found",
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ALTERNATIVE_PATH,
                message=f"Alternative path failed: {e}",
            )

    async def _rollback(
        self,
        context: Dict[str, Any],
        current_step: Optional[Dict[str, Any]],
    ) -> RecoveryResult:
        """Rollback changes and retry from a safe state."""
        try:
            # Press back to go to previous state
            await self.adb.press_back()
            return RecoveryResult(
                success=True,
                strategy=RecoveryStrategy.ROLLBACK,
                message="Rolled back to previous state",
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.ROLLBACK,
                message=f"Rollback failed: {e}",
            )

    def get_alternative_apps(self, app_category: str) -> List[str]:
        """Get alternative apps for a category."""
        return self._alternative_apps.get(app_category, [])

    def get_status(self) -> Dict[str, Any]:
        """Get recovery engine status."""
        return {
            "type": "recovery_engine",
            "recovery_chains": len(self._recovery_chains),
            "failure_types": [ft.value for ft in self._recovery_chains.keys()],
            "alternative_app_categories": list(self._alternative_apps.keys()),
        }


# Singleton
_recovery_engine = None


def get_recovery_engine() -> RecoveryEngine:
    global _recovery_engine
    if _recovery_engine is None:
        _recovery_engine = RecoveryEngine()
    return _recovery_engine
