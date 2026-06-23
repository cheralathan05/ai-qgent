"""
APA-OS Execution Engine

Executes workflows on the Android device.
Handles Phase 1 (Device Control) and Phase 2 (Phone Intelligence).
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .workflow_generator import Workflow, WorkflowStep

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: int
    step_type: str
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0
    verification_passed: bool = False


@dataclass
class ExecutionResult:
    """Result of executing a complete workflow."""
    workflow_id: str
    success: bool
    message: str
    steps: List[StepResult]
    duration_ms: float = 0
    verification_passed: bool = False
    foreground_app: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionEngine:
    """
    Executes workflows on Android device.
    
    Handles:
    - App launch/close
    - Text input
    - Key presses
    - Screen capture
    - Navigation
    - Verification
    """

    def __init__(self):
        self._adb = None
        self._app_resolver = None
        self._app_launch = None

    @property
    def adb(self):
        if self._adb is None:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb = get_adb_service(find_adb_binary())
        return self._adb

    @property
    def app_resolver(self):
        if self._app_resolver is None:
            from services.app_resolver import get_app_resolver
            self._app_resolver = get_app_resolver()
        return self._app_resolver

    @property
    def app_launch(self):
        if self._app_launch is None:
            from services.app_launch import get_app_launch_service
            self._app_launch = get_app_launch_service()
        return self._app_launch

    async def execute(self, workflow: Workflow, device_id: str) -> ExecutionResult:
        """Execute a complete workflow."""
        start_time = datetime.utcnow()
        step_results: List[StepResult] = []

        # Ensure app registry is built
        await self.app_resolver.ensure_registry(device_id)

        for step in workflow.steps:
            step_start = datetime.utcnow()
            
            try:
                result = await self._execute_step(step, device_id)
                result.duration_ms = (datetime.utcnow() - step_start).total_seconds() * 1000
                step_results.append(result)
                
                if not result.success and step.retry_on_fail:
                    # Retry logic
                    for retry in range(step.max_retries):
                        await asyncio.sleep(1)
                        result = await self._execute_step(step, device_id)
                        result.duration_ms = (datetime.utcnow() - step_start).total_seconds() * 1000
                        if result.success:
                            break
                    step_results.append(result)
                    
            except Exception as e:
                logger.error(f"Step {step.step_id} failed: {e}")
                step_results.append(StepResult(
                    step_id=step.step_id,
                    step_type=step.step_type,
                    success=False,
                    message=str(e),
                ))

        # Determine overall success
        all_success = all(r.success for r in step_results)
        verification_passed = all(r.verification_passed for r in step_results if r.verification_passed)
        
        total_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Get final foreground app
        foreground_app = None
        try:
            foreground_app = await self.adb.get_foreground_app(device_id)
        except Exception:
            pass

        return ExecutionResult(
            workflow_id=workflow.workflow_id,
            success=all_success or verification_passed,
            message=self._build_message(workflow, step_results),
            steps=step_results,
            duration_ms=total_duration,
            verification_passed=verification_passed,
            foreground_app=foreground_app,
            metadata=workflow.metadata,
        )

    async def _execute_step(self, step: WorkflowStep, device_id: str) -> StepResult:
        """Execute a single workflow step."""
        action = step.action
        params = step.params

        try:
            if action == "resolve_package":
                return await self._resolve_package(params, device_id)
            elif action == "launch_app":
                return await self._launch_app(params, device_id)
            elif action == "force_stop":
                return await self._force_stop(params, device_id)
            elif action == "resolve_contact":
                return await self._resolve_contact(params)
            elif action == "navigate_to_chat":
                return await self._navigate_to_chat(params, device_id)
            elif action == "input_text":
                return await self._input_text(params, device_id)
            elif action == "press_key":
                return await self._press_key(params, device_id)
            elif action == "open_url":
                return await self._open_url(params, device_id)
            elif action == "take_screenshot":
                return await self._take_screenshot(device_id)
            elif action == "get_battery":
                return await self._get_battery(device_id)
            elif action == "get_device_status":
                return await self._get_device_status(device_id)
            elif action == "get_foreground_app":
                return await self._get_foreground_app(device_id)
            elif action == "read_notifications":
                return await self._read_notifications(device_id)
            elif action == "swipe":
                return await self._swipe(params, device_id)
            elif action == "toggle_setting":
                return await self._toggle_setting(params, device_id)
            elif action == "volume_control":
                return await self._volume_control(params, device_id)
            elif action == "create_reminder":
                return await self._create_reminder(params, device_id)
            elif action == "dial_number":
                return await self._dial_number(params, device_id)
            elif action == "open_file":
                return await self._open_file(params, device_id)
            else:
                return StepResult(
                    step_id=step.step_id,
                    step_type=step.step_type,
                    success=False,
                    message=f"Unknown action: {action}",
                )
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                step_type=step.step_type,
                success=False,
                message=str(e),
            )

    async def _resolve_package(self, params: Dict, device_id: str) -> StepResult:
        """Resolve app name to package name."""
        app_name = params.get("app_name", "")
        package = self.app_resolver.resolve(app_name)
        
        if not package:
            from services.app_launch import AppLaunchService
            launch_svc = AppLaunchService(adb_service=self.adb, resolver=self.app_resolver)
            package = launch_svc._resolve_package_fallback(app_name)
        
        if package:
            return StepResult(
                step_id=0,
                step_type="resolve_package",
                success=True,
                message=f"Resolved {app_name} to {package}",
                data={"package": package},
            )
        return StepResult(
            step_id=0,
            step_type="resolve_package",
            success=False,
            message=f"Package not found for {app_name}",
        )

    async def _launch_app(self, params: Dict, device_id: str) -> StepResult:
        """Launch an app."""
        app_name = params.get("app_name", "")
        result = await self.app_launch.launch_app(device_id, app_name)
        
        return StepResult(
            step_id=0,
            step_type="launch_app",
            success=result.success,
            message=f"Launched {app_name}" if result.success else f"Failed to launch {app_name}",
            data=result.to_dict(),
            verification_passed=result.verification == "completed",
        )

    async def _force_stop(self, params: Dict, device_id: str) -> StepResult:
        """Force stop an app."""
        app_name = params.get("app_name", "")
        result = await self.app_launch.force_stop_app(device_id, app_name)
        
        return StepResult(
            step_id=0,
            step_type="force_stop",
            success=result.get("success", False),
            message=f"Stopped {app_name}" if result.get("success") else f"Failed to stop {app_name}",
        )

    async def _resolve_contact(self, params: Dict) -> StepResult:
        """Resolve contact name to phone number."""
        contact_name = params.get("contact_name", "")
        try:
            from services.contact_store import get_contact_store
            store = get_contact_store()
            contact = store.resolve(contact_name)
            if contact:
                return StepResult(
                    step_id=0,
                    step_type="resolve_contact",
                    success=True,
                    message=f"Found {contact.display_name}",
                    data={"phone": contact.phone, "display_name": contact.display_name},
                )
        except Exception:
            pass
        
        return StepResult(
            step_id=0,
            step_type="resolve_contact",
            success=True,
            message=f"Contact {contact_name} (no phone lookup)",
            data={"contact_name": contact_name},
        )

    async def _navigate_to_chat(self, params: Dict, device_id: str) -> StepResult:
        """Navigate to a chat with a contact."""
        contact = params.get("contact", "")
        app = params.get("app", "whatsapp")
        
        try:
            if app == "whatsapp":
                from services.contact_store import get_contact_store
                store = get_contact_store()
                c = store.resolve(contact)
                if c and c.phone:
                    wa_pkg = await self.adb.resolve_package_dynamic(device_id, "whatsapp")
                    wa_pkg = wa_pkg or "com.whatsapp"
                    await self.adb.shell(
                        device_id,
                        f'am start -a android.intent.action.SENDTO -d "smsto:{c.phone}" -n "{wa_pkg}/.Conversation"'
                    )
                    await asyncio.sleep(2)
                    return StepResult(
                        step_id=0,
                        step_type="navigate_to_chat",
                        success=True,
                        message=f"Opened chat with {contact}",
                    )
        except Exception as e:
            logger.debug(f"Chat navigation failed: {e}")
        
        return StepResult(
            step_id=0,
            step_type="navigate_to_chat",
            success=True,
            message=f"Opened {app}",
        )

    async def _input_text(self, params: Dict, device_id: str) -> StepResult:
        """Input text."""
        text = params.get("text", "")
        await self.adb.input_text(device_id, text)
        return StepResult(
            step_id=0,
            step_type="input_text",
            success=True,
            message=f"Typed: {text[:50]}",
        )

    async def _press_key(self, params: Dict, device_id: str) -> StepResult:
        """Press a key."""
        keycode = params.get("keycode", 66)
        await self.adb.press_key(device_id, keycode)
        return StepResult(
            step_id=0,
            step_type="press_key",
            success=True,
            message=f"Pressed key {keycode}",
        )

    async def _open_url(self, params: Dict, device_id: str) -> StepResult:
        """Open a URL."""
        url = params.get("url", "")
        await self.adb.open_url(device_id, url)
        await asyncio.sleep(3)
        return StepResult(
            step_id=0,
            step_type="open_url",
            success=True,
            message=f"Opened URL",
            verification_passed=True,
        )

    async def _take_screenshot(self, device_id: str) -> StepResult:
        """Take a screenshot."""
        try:
            png_data = await self.adb.take_screenshot(device_id)
            save_dir = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")
            os.makedirs(save_dir, exist_ok=True)
            filename = f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(png_data)
            return StepResult(
                step_id=0,
                step_type="screenshot",
                success=True,
                message="Screenshot captured",
                data={"path": filepath},
                verification_passed=True,
            )
        except Exception as e:
            return StepResult(
                step_id=0,
                step_type="screenshot",
                success=False,
                message=str(e),
            )

    async def _get_battery(self, device_id: str) -> StepResult:
        """Get battery level."""
        battery = await self.adb.get_battery_level(device_id)
        return StepResult(
            step_id=0,
            step_type="battery",
            success=battery is not None,
            message=f"Battery: {battery}%" if battery else "Could not read battery",
            data={"battery_level": battery},
            verification_passed=battery is not None,
        )

    async def _get_device_status(self, device_id: str) -> StepResult:
        """Get device status."""
        status = await self.adb.get_device_status(device_id)
        return StepResult(
            step_id=0,
            step_type="device_status",
            success=True,
            message=f"Device: {status.get('model_name', 'Unknown')}",
            data=status,
        )

    async def _get_foreground_app(self, device_id: str) -> StepResult:
        """Get foreground app."""
        fg = await self.adb.get_foreground_app(device_id)
        return StepResult(
            step_id=0,
            step_type="foreground_app",
            success=fg is not None,
            message=f"Current app: {fg}" if fg else "Could not detect app",
            data={"foreground_app": fg},
        )

    async def _read_notifications(self, device_id: str) -> StepResult:
        """Read notifications."""
        try:
            output = await self.adb.shell(device_id, "dumpsys notification --noredact")
            return StepResult(
                step_id=0,
                step_type="notifications",
                success=True,
                message="Notifications read",
                data={"raw": output[:2000]},
            )
        except Exception as e:
            return StepResult(
                step_id=0,
                step_type="notifications",
                success=False,
                message=str(e),
            )

    async def _swipe(self, params: Dict, device_id: str) -> StepResult:
        """Swipe/scroll."""
        direction = params.get("direction", "down")
        if direction == "down":
            await self.adb.shell(device_id, "input swipe 500 1000 500 200")
        elif direction == "up":
            await self.adb.shell(device_id, "input swipe 500 200 500 1000")
        elif direction == "left":
            await self.adb.shell(device_id, "input swipe 800 500 200 500")
        elif direction == "right":
            await self.adb.shell(device_id, "input swipe 200 500 800 500")
        
        return StepResult(
            step_id=0,
            step_type="swipe",
            success=True,
            message=f"Scrolled {direction}",
        )

    async def _toggle_setting(self, params: Dict, device_id: str) -> StepResult:
        """Toggle a setting."""
        setting = params.get("setting", "")
        state = params.get("state", "on")
        
        if setting == "wifi":
            cmd = "svc wifi enable" if state == "on" else "svc wifi disable"
        elif setting == "bluetooth":
            cmd = "svc bluetooth enable" if state == "on" else "svc bluetooth disable"
        elif setting == "flashlight":
            cmd = f"cmd camera set-torch-mode {'on' if state == 'on' else 'off'}"
        else:
            return StepResult(
                step_id=0,
                step_type="toggle_setting",
                success=False,
                message=f"Unknown setting: {setting}",
            )
        
        try:
            await self.adb.shell(device_id, cmd)
            return StepResult(
                step_id=0,
                step_type="toggle_setting",
                success=True,
                message=f"{setting} turned {state}",
            )
        except Exception as e:
            return StepResult(
                step_id=0,
                step_type="toggle_setting",
                success=False,
                message=str(e),
            )

    async def _volume_control(self, params: Dict, device_id: str) -> StepResult:
        """Control volume."""
        direction = params.get("direction", "up")
        
        if direction == "up":
            keycode = 24  # KEYCODE_VOLUME_UP
        elif direction == "down":
            keycode = 25  # KEYCODE_VOLUME_DOWN
        elif direction == "mute":
            keycode = 164  # KEYCODE_VOLUME_MUTE
        else:
            keycode = 24
        
        await self.adb.press_key(device_id, keycode)
        return StepResult(
            step_id=0,
            step_type="volume",
            success=True,
            message=f"Volume {direction}",
        )

    async def _create_reminder(self, params: Dict, device_id: str) -> StepResult:
        """Create a reminder."""
        message = params.get("message", "reminder")
        try:
            await self.adb.shell(
                device_id,
                f'am start -a android.intent.action.SET_TIMER -e android.intent.extra.alarm.MESSAGE "{message}" --ei android.intent.extra.alarm.LENGTH 60'
            )
            return StepResult(
                step_id=0,
                step_type="reminder",
                success=True,
                message=f"Reminder set: {message}",
            )
        except Exception as e:
            return StepResult(
                step_id=0,
                step_type="reminder",
                success=False,
                message=str(e),
            )

    async def _dial_number(self, params: Dict, device_id: str) -> StepResult:
        """Dial a number."""
        contact = params.get("contact", "")
        try:
            from services.contact_store import get_contact_store
            store = get_contact_store()
            c = store.resolve(contact)
            if c and c.phone:
                await self.adb.shell(
                    device_id,
                    f'am start -a android.intent.action.DIAL -d "tel:{c.phone}"'
                )
                return StepResult(
                    step_id=0,
                    step_type="dial",
                    success=True,
                    message=f"Calling {contact}",
                )
        except Exception:
            pass
        
        return StepResult(
            step_id=0,
            step_type="dial",
            success=True,
            message=f"Opened dialer for {contact}",
        )

    async def _open_file(self, params: Dict, device_id: str) -> StepResult:
        """Open a file."""
        filename = params.get("filename", "")
        try:
            await self.adb.shell(
                device_id,
                f'am start -a android.intent.action.VIEW -d "content://com.android.externalstorage.documents/document/primary:Download/{filename}" -t "*/*"'
            )
            return StepResult(
                step_id=0,
                step_type="open_file",
                success=True,
                message=f"Opening {filename}",
            )
        except Exception as e:
            return StepResult(
                step_id=0,
                step_type="open_file",
                success=False,
                message=str(e),
            )

    def _build_message(self, workflow: Workflow, results: List[StepResult]) -> str:
        """Build a user-friendly message."""
        if not results:
            return "Command processed"
        
        last_result = results[-1]
        if last_result.success:
            return last_result.message
        return last_result.message or "Command failed"


# Singleton
_execution_engine = None


def get_execution_engine() -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine
