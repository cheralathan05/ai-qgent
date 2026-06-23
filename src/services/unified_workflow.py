"""
APA-OS Unified Workflow Engine
Phase 1 (Device Control) + Phase 2 (Phone Intelligence) + Phase 3 (Knowledge)
Single entry point for all user commands.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowPhase(str, Enum):
    """Which phase(s) the workflow touches."""
    PHASE1 = "phase1_device_control"
    PHASE2 = "phase2_phone_intelligence"
    PHASE3 = "phase3_knowledge"
    PHASE1_2 = "phase1_2_combined"
    PHASE1_3 = "phase1_3_combined"
    ALL = "all_phases"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """Single workflow step."""
    step_number: int
    step_type: str
    description: str
    phase: WorkflowPhase
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"
    duration_ms: float = 0


@dataclass
class WorkflowResult:
    """Complete workflow result."""
    workflow_id: str
    success: bool
    status: WorkflowStatus
    intent: str
    target: Optional[str]
    message: str
    steps: List[WorkflowStep]
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    verification_passed: bool = False
    foreground_app: Optional[str] = None
    package_name: Optional[str] = None


class UnifiedWorkflowEngine:
    """
    Unified workflow engine that routes commands through the appropriate
    combination of Phase 1, Phase 2, and Phase 3.
    
    Flow:
    Voice/Text -> Intent Agent -> Entity Extraction -> App Resolver
    -> Package Resolver -> ADB Launch -> Verification -> Response
    """

    def __init__(self):
        self._adb_service = None
        self._intent_agent = None
        self._app_resolver = None
        self._app_launch = None
        self._event_manager = None
        self._context_engine = None
        self._memory_engine = None

    @property
    def adb(self):
        if self._adb_service is None:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb_service = get_adb_service(find_adb_binary())
        return self._adb_service

    @property
    def intent_agent(self):
        if self._intent_agent is None:
            from services.intent_agent import get_intent_agent
            self._intent_agent = get_intent_agent()
        return self._intent_agent

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

    @property
    def event_manager(self):
        if self._event_manager is None:
            from console.event_stream import get_event_manager
            self._event_manager = get_event_manager()
        return self._event_manager

    @property
    def context_engine(self):
        if self._context_engine is None:
            from context.engine import get_context_engine
            self._context_engine = get_context_engine()
        return self._context_engine

    @property
    def memory_engine(self):
        if self._memory_engine is None:
            from memory.engine import get_memory_engine
            self._memory_engine = get_memory_engine()
        return self._memory_engine

    async def get_connected_device_id(self) -> Optional[str]:
        """Get the first connected Android device serial."""
        try:
            devices = await self.adb.list_devices()
            if devices:
                return devices[0]["serial"]
        except Exception as e:
            logger.warning(f"Failed to get connected device: {e}")
        return None

    async def get_all_installed_apps(self, device_id: str) -> List[Dict[str, Any]]:
        """Discover all installed apps on the device."""
        await self.app_resolver.ensure_registry(device_id)
        return self.app_resolver.list_apps()

    async def search_installed_apps(self, device_id: str, query: str) -> List[Dict[str, Any]]:
        """Search installed apps by name."""
        await self.app_resolver.ensure_registry(device_id)
        return self.app_resolver.search(query)

    async def execute_command(
        self,
        command: str,
        user_id: str = "default",
        device_id: Optional[str] = None,
        session_id: Optional[str] = None,
        voice_input: bool = False,
    ) -> WorkflowResult:
        """
        Execute a user command through the unified workflow pipeline.
        
        Pipeline:
        1. Intent Detection
        2. Entity Extraction
        3. App Resolution (dynamic)
        4. ADB Launch
        5. Verification
        6. Response
        """
        workflow_id = f"wf_{int(datetime.utcnow().timestamp())}"
        start_time = datetime.utcnow()
        steps: List[WorkflowStep] = []

        # Resolve device
        if not device_id:
            device_id = await self.get_connected_device_id()
        if not device_id:
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                status=WorkflowStatus.FAILED,
                intent="unknown",
                target=None,
                message="No Android device connected",
                steps=steps,
                duration_ms=0,
            )

        # Ensure app registry is built
        await self.app_resolver.ensure_registry(device_id)

        # Stage 1: Intent Detection
        step1 = WorkflowStep(
            step_number=1,
            step_type="intent_detection",
            description="Detecting command intent",
            phase=WorkflowPhase.ALL,
        )
        steps.append(step1)

        try:
            intent_result = await self.intent_agent.detect_intent(command)
            intent = intent_result.intent.value
            slots = intent_result.slots
            confidence = intent_result.confidence

            step1.result = {
                "intent": intent,
                "confidence": confidence,
                "slots": slots,
            }
            step1.status = "completed"
            step1.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        except Exception as e:
            step1.status = "failed"
            step1.result = {"error": str(e)}
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                status=WorkflowStatus.FAILED,
                intent="unknown",
                target=None,
                message=f"Intent detection failed: {e}",
                steps=steps,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

        # Stage 2: Route based on intent
        target_app = slots.get("app")
        
        # Determine which phases to execute
        phase = self._determine_phase(intent, slots)

        # Stage 3: App Resolution (if needed)
        package_name = None
        if target_app and intent in ("open_app", "close_app", "send_message", "open_chat", "search", "open_camera", "open_settings"):
            step3 = WorkflowStep(
                step_number=len(steps) + 1,
                step_type="app_resolution",
                description=f"Resolving app: {target_app}",
                phase=WorkflowPhase.PHASE1,
            )
            steps.append(step3)

            try:
                package_name = self.app_resolver.resolve(target_app)
                if not package_name:
                    # Try fallback mapping
                    from services.app_launch import AppLaunchService
                    launch_svc = AppLaunchService(adb_service=self.adb, resolver=self.app_resolver)
                    package_name = launch_svc._resolve_package_fallback(target_app)

                if package_name:
                    step3.result = {
                        "app_name": target_app,
                        "package_name": package_name,
                    }
                    step3.status = "completed"
                else:
                    step3.status = "failed"
                    step3.result = {"error": f"App '{target_app}' not found on device"}
                    return WorkflowResult(
                        workflow_id=workflow_id,
                        success=False,
                        status=WorkflowStatus.FAILED,
                        intent=intent,
                        target=target_app,
                        message=f"App '{target_app}' is not installed on your device",
                        steps=steps,
                        duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    )
            except Exception as e:
                step3.status = "failed"
                step3.result = {"error": str(e)}
                return WorkflowResult(
                    workflow_id=workflow_id,
                    success=False,
                    status=WorkflowStatus.FAILED,
                    intent=intent,
                    target=target_app,
                    message=f"Failed to resolve app: {e}",
                    steps=steps,
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

        # Stage 4: Execute Action
        step4 = WorkflowStep(
            step_number=len(steps) + 1,
            step_type="execute_action",
            description=f"Executing: {intent}",
            phase=phase,
        )
        steps.append(step4)

        exec_start = datetime.utcnow()
        try:
            exec_result = await self._execute_action(
                intent=intent,
                slots=slots,
                device_id=device_id,
                package_name=package_name,
                workflow_id=workflow_id,
            )
            step4.result = exec_result
            step4.status = "completed" if exec_result.get("success") else "failed"
            step4.duration_ms = (datetime.utcnow() - exec_start).total_seconds() * 1000
        except Exception as e:
            step4.status = "failed"
            step4.result = {"error": str(e)}
            return WorkflowResult(
                workflow_id=workflow_id,
                success=False,
                status=WorkflowStatus.FAILED,
                intent=intent,
                target=target_app,
                message=f"Execution failed: {e}",
                steps=steps,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

        # Stage 5: Verification
        step5 = WorkflowStep(
            step_number=len(steps) + 1,
            step_type="verification",
            description="Verifying action success",
            phase=WorkflowPhase.PHASE2,
        )
        steps.append(step5)

        verification_passed = False
        foreground_app = None
        
        try:
            if intent in ("open_app", "open_camera", "open_settings") and package_name:
                # Verify foreground app matches target
                foreground_app = await self.adb.get_foreground_app(device_id)
                verification_passed = (
                    foreground_app is not None and
                    (foreground_app == package_name or package_name in foreground_app)
                )
                step5.result = {
                    "expected": package_name,
                    "actual": foreground_app,
                    "passed": verification_passed,
                }
            elif intent == "battery_status":
                verification_passed = step4.result.get("battery_level") is not None
                step5.result = {"passed": verification_passed}
            elif intent == "take_screenshot":
                verification_passed = step4.result.get("path") is not None
                step5.result = {"passed": verification_passed}
            elif intent == "send_message":
                verification_passed = step4.result.get("message_verified", False)
                step5.result = {"passed": verification_passed}
            else:
                verification_passed = step4.result.get("success", False)
                step5.result = {"passed": verification_passed}

            step5.status = "completed"
        except Exception as e:
            step5.status = "failed"
            step5.result = {"error": str(e), "passed": False}

        # Update context
        try:
            self.context_engine.update(
                current_device_id=device_id,
                current_app=package_name or target_app or "",
                last_command=command,
                last_intent=intent,
                last_target=target_app,
            )
        except Exception:
            pass

        # Build response
        total_duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        message = self._build_response_message(intent, target_app, step4.result, verification_passed)

        return WorkflowResult(
            workflow_id=workflow_id,
            success=verification_passed or step4.status == "completed",
            status=WorkflowStatus.COMPLETED if verification_passed else WorkflowStatus.FAILED,
            intent=intent,
            target=target_app,
            message=message,
            steps=steps,
            duration_ms=total_duration,
            verification_passed=verification_passed,
            foreground_app=foreground_app,
            package_name=package_name,
            metadata={
                "confidence": confidence,
                "slots": slots,
                "device_id": device_id,
                "voice_input": voice_input,
            },
        )

    def _determine_phase(self, intent: str, slots: Dict[str, Any]) -> WorkflowPhase:
        """Determine which phases are needed for this intent."""
        if intent in ("open_app", "close_app", "open_settings", "open_folder",
                      "battery_status", "take_screenshot", "foreground_app"):
            return WorkflowPhase.PHASE1_2
        elif intent in ("send_message", "open_chat", "call_contact"):
            return WorkflowPhase.PHASE1_2
        elif intent in ("search", "web_search"):
            return WorkflowPhase.PHASE1_2
        return WorkflowPhase.ALL

    async def _execute_action(
        self,
        intent: str,
        slots: Dict[str, Any],
        device_id: str,
        package_name: Optional[str],
        workflow_id: str,
    ) -> Dict[str, Any]:
        """Execute the action based on intent."""
        
        if intent == "open_app":
            app_name = slots.get("app")
            result = await self.app_launch.launch_app(device_id, app_name)
            return result.to_dict()

        elif intent == "close_app":
            app_name = slots.get("app")
            result = await self.app_launch.force_stop_app(device_id, app_name)
            return result

        elif intent == "battery_status":
            battery = await self.adb.get_battery_level(device_id)
            return {"success": True, "battery_level": battery}

        elif intent == "foreground_app":
            fg = await self.adb.get_foreground_app(device_id)
            return {"success": True, "foreground_app": fg}

        elif intent == "take_screenshot":
            png_data = await self.adb.take_screenshot(device_id)
            import os
            save_dir = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")
            os.makedirs(save_dir, exist_ok=True)
            filename = f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(png_data)
            return {"success": True, "path": filepath}

        elif intent == "send_message":
            return await self._execute_send_message(
                slots=slots,
                device_id=device_id,
                workflow_id=workflow_id,
            )

        elif intent == "open_chat":
            return await self._execute_open_chat(
                slots=slots,
                device_id=device_id,
            )

        elif intent == "call_contact":
            return await self._execute_call(slots, device_id)

        elif intent in ("search", "web_search"):
            return await self._execute_search(
                slots=slots,
                device_id=device_id,
            )

        elif intent == "open_camera":
            app_name = slots.get("app", "camera")
            result = await self.app_launch.launch_app(device_id, app_name)
            return result.to_dict()

        elif intent == "open_settings":
            result = await self.app_launch.launch_app(device_id, "settings")
            return result.to_dict()

        elif intent == "open_folder":
            result = await self.app_launch.launch_app(device_id, "files")
            return result.to_dict()

        return {"success": False, "error": f"Unknown intent: {intent}"}

    async def _execute_send_message(
        self,
        slots: Dict[str, Any],
        device_id: str,
        workflow_id: str,
    ) -> Dict[str, Any]:
        """Execute send message action."""
        recipient = slots.get("recipient")
        message = slots.get("message")
        app = slots.get("app", "whatsapp")

        if not recipient:
            return {"success": False, "error": "No recipient specified"}

        try:
            from services.contact_store import get_contact_store
            contact_store = get_contact_store()
            contact = contact_store.resolve(recipient)
            phone = contact.phone if contact else None
            resolved_name = contact.display_name if contact else recipient

            if app == "whatsapp" and phone:
                # Use deep link for WhatsApp
                wa_pkg = await self.adb.resolve_package_dynamic(device_id, "whatsapp")
                wa_pkg = wa_pkg or "com.whatsapp"
                intent_url = f"smsto:{phone}"
                await self.adb.shell(
                    device_id,
                    f'am start -a android.intent.action.SENDTO -d "{intent_url}" -n "{wa_pkg}/.Conversation"'
                )
                await asyncio.sleep(2)

                if message:
                    await self.adb.input_text(device_id, message)
                    await asyncio.sleep(0.5)
                    await self.adb.press_key(device_id, 66)  # Enter
                    await asyncio.sleep(1)

                return {"success": True, "recipient": resolved_name, "app": app}

            # Fallback: open app
            result = await self.app_launch.launch_app(device_id, app)
            return result.to_dict()

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_open_chat(
        self,
        slots: Dict[str, Any],
        device_id: str,
    ) -> Dict[str, Any]:
        """Execute open chat action."""
        recipient = slots.get("recipient")
        app = slots.get("app", "instagram")

        result = await self.app_launch.launch_app(device_id, app)
        return result.to_dict()

    async def _execute_call(
        self,
        slots: Dict[str, Any],
        device_id: str,
    ) -> Dict[str, Any]:
        """Execute call action."""
        recipient = slots.get("recipient")
        if not recipient:
            return {"success": False, "error": "No recipient specified"}

        try:
            from services.contact_store import get_contact_store
            contact = get_contact_store().resolve(recipient)
            phone = contact.phone if contact else None

            if phone:
                await self.adb.shell(
                    device_id,
                    f'am start -a android.intent.action.DIAL -d "tel:{phone}"'
                )
                return {"success": True, "recipient": recipient, "phone": phone}

            return await self.app_launch.launch_app(device_id, "phone")
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_search(
        self,
        slots: Dict[str, Any],
        device_id: str,
    ) -> Dict[str, Any]:
        """Execute search action."""
        query = slots.get("query")
        app = slots.get("app")

        if not query:
            return {"success": False, "error": "No search query specified"}

        if app and "youtube" in app.lower():
            return await self._search_youtube(device_id, query)

        # Default: web search via Chrome
        import urllib.parse
        enc = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={enc}"
        await self.adb.open_url(device_id, url)
        return {"success": True, "query": query, "method": "url"}

    async def _search_youtube(
        self,
        device_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """Search YouTube."""
        try:
            await self.app_launch.launch_app(device_id, "youtube")
            await asyncio.sleep(4)

            foreground = await self.adb.get_foreground_app(device_id)
            youtube_pkg = "com.google.android.youtube"

            if not foreground or youtube_pkg not in foreground:
                return {"success": False, "error": "YouTube did not open"}

            # Press search key
            await self.adb.press_key(device_id, 84)
            await asyncio.sleep(1.5)

            # Type query
            await self.adb.input_text(device_id, query)
            await asyncio.sleep(0.5)

            # Press enter
            await self.adb.press_key(device_id, 66)
            await asyncio.sleep(2)

            return {"success": True, "query": query, "method": "native_search"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_response_message(
        self,
        intent: str,
        target: Optional[str],
        exec_result: Dict[str, Any],
        verified: bool,
    ) -> str:
        """Build a user-friendly response message."""
        if not exec_result.get("success"):
            return exec_result.get("error") or "Command failed"

        if intent == "open_app" and target:
            pretty = target.replace("_", " ").title()
            if verified:
                return f"{pretty} is ready."
            return f"{pretty} was launched but verification is pending."

        if intent == "battery_status":
            battery = exec_result.get("battery_level")
            if battery is not None:
                return f"Your battery is at {battery}%."
            return "Battery level retrieved."

        if intent == "foreground_app":
            fg = exec_result.get("foreground_app")
            if fg:
                return f"The current app is {fg}."
            return "Current app detected."

        if intent == "take_screenshot":
            return "Screenshot captured."

        if intent == "send_message":
            recipient = exec_result.get("recipient", "your contact")
            return f"Message sent to {recipient}."

        if intent in ("search", "web_search"):
            query = exec_result.get("query", "")
            if query:
                return f"Search results for '{query}' are ready."
            return "Search completed."

        return "Command completed successfully."


# Singleton
_unified_workflow = None


def get_unified_workflow() -> UnifiedWorkflowEngine:
    global _unified_workflow
    if _unified_workflow is None:
        _unified_workflow = UnifiedWorkflowEngine()
    return _unified_workflow
