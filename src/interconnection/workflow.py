import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from console.event_stream import (
    get_event_manager,
    EventType,
    EventSeverity,
)
from devices import device_manager
from config import Config

from services.adb_service import get_adb_service, find_adb_binary
from services.intent_agent import get_intent_agent
from services.planner_agent import get_planner_agent
from services.app_launch import get_app_launch_service
from services.contact_store import get_contact_store
from services.app_resolver import get_app_resolver

from vision.screen_capture import get_screen_capture_service
from vision.ocr_service import get_ocr_service
from vision.ui_detector import get_ui_detector
from vision.screen_classifier import get_screen_classifier
from vision.phone_memory import get_phone_memory

from navigation.navigation_intelligence import get_navigation_intelligence
from verification.visual_verifier import get_visual_verifier

from agents.knowledge_agent import get_knowledge_agent
from agents.reasoning_agent import get_reasoning_agent
from context.engine import get_context_engine
from memory.engine import get_memory_engine
from knowledge_graph.engine import get_knowledge_graph

from interconnection.models import (
    Phase1Result,
    Phase2Result,
    Phase3Result,
    UnifiedCommandResult,
    AssistantContext,
)
from interconnection.planner import get_unified_planner, UnifiedIntentType

logger = logging.getLogger(__name__)


class InterconnectionWorkflow:
    """Orchestrates Phase1→Phase2→Phase3 unified flow for every command."""

    def __init__(self):
        self.event_manager = get_event_manager()
        self.adb = get_adb_service(find_adb_binary())
        self.intent_agent = get_intent_agent()
        self.unified_planner = get_unified_planner()
        self.screen_capture = get_screen_capture_service()
        self.ocr_service = get_ocr_service()
        self.ui_detector = get_ui_detector()
        self.screen_classifier = get_screen_classifier()
        self.phone_memory = get_phone_memory()
        self.nav_intelligence = get_navigation_intelligence()
        self.visual_verifier = get_visual_verifier()
        self.knowledge_agent = get_knowledge_agent()
        self.reasoning_agent = get_reasoning_agent()
        self.context_engine = get_context_engine()
        self.memory_engine = get_memory_engine()
        self.knowledge_graph = get_knowledge_graph()

    async def execute(
        self,
        command: str,
        user_id: str = "default",
        device_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> UnifiedCommandResult:
        workflow_id = workflow_id or str(uuid.uuid4())
        start_time = datetime.utcnow()

        result = UnifiedCommandResult(
            workflow_id=workflow_id,
            command=command,
        )

        await self._emit(workflow_id, EventType.COMMAND_RECEIVED, {
            "command": command, "user_id": user_id, "device_id": device_id or "auto",
        }, user_id=user_id, device_id=device_id)

        try:
            resolved_device_id = await self._resolve_device(device_id)
            if not resolved_device_id:
                raise RuntimeError("No Android device connected")

            unified_intent, slots, plan = self.unified_planner.create_plan(command)
            result.intent = unified_intent.value
            result.target = slots.get("app") or slots.get("recipient") or slots.get("query", "")

            await self._emit(workflow_id, EventType.INTENT_DETECTED, {
                "intent": unified_intent.value, "slots": slots, "plan": plan,
            }, user_id=user_id, device_id=resolved_device_id)

            for step in plan:
                phase = step.get("phase")

                if phase == "phase1":
                    p1_result = await self._execute_phase1(step, resolved_device_id, workflow_id)
                    result.phase1 = p1_result
                    if not p1_result.success:
                        raise RuntimeError(f"Phase 1 failed: {p1_result.details.get('error', 'unknown')}")

                elif phase == "phase2":
                    p2_result = await self._execute_phase2(step, resolved_device_id, workflow_id)
                    result.phase2 = p2_result

                elif phase == "phase3":
                    p3_result = await self._execute_phase3(step, command, resolved_device_id, workflow_id)
                    result.phase3 = p3_result

            ctx = self._build_assistant_context(unified_intent, slots, result, resolved_device_id)
            result.context = ctx

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result.duration_ms = duration_ms

            reply = self._generate_assistant_reply(result)
            result.assistant_reply = reply
            result.status = "completed"
            result.success = True

            await self._emit(workflow_id, EventType.WORKFLOW_COMPLETED, {
                "success": True, "intent": unified_intent.value,
                "duration_ms": duration_ms, "reply": reply,
            }, user_id=user_id, device_id=resolved_device_id)

            self.context_engine.update(
                last_command=command,
                last_intent=unified_intent.value,
                last_target=result.target or "",
                current_device_id=resolved_device_id,
                current_workflow_id=workflow_id,
            )

            self.memory_engine.store_conversation(
                user_id=user_id, session_id=workflow_id,
                user_message=command,
                assistant_message=reply,
            )

        except Exception as e:
            logger.error(f"Unified workflow failed: {e}")
            result.success = False
            result.status = "failed"
            result.assistant_reply = f"I couldn't complete that. {str(e)}"

            await self._emit(workflow_id, EventType.WORKFLOW_FAILED, {
                "error": str(e), "intent": result.intent,
            }, severity="error", user_id=user_id)

        return result

    async def _resolve_device(self, device_id: Optional[str] = None) -> Optional[str]:
        if device_id:
            dev = device_manager.get_device(device_id)
            if dev:
                return device_id
        try:
            devices = await self.adb.list_devices()
            if devices:
                return devices[0]["serial"]
        except Exception:
            pass
        return None

    async def _execute_phase1(self, step: Dict[str, Any], device_id: str, workflow_id: str) -> Phase1Result:
        action = step.get("action", "")
        p1 = Phase1Result(device_id=device_id, action_type=action)
        p1_start = datetime.utcnow()

        await self._emit(workflow_id, EventType.EXECUTION_STARTED, {
            "phase": "phase1", "action": action, "device_id": device_id,
        }, device_id=device_id)

        try:
            if action == "launch_app":
                app = step.get("app", "")
                launch_service = get_app_launch_service(adb_service=self.adb)
                launch_result = await launch_service.launch_app(device_id, app)
                p1.success = launch_result.success if hasattr(launch_result, 'success') else True
                p1.action_target = app
                p1.status = "completed"
                p1.details = launch_result.to_dict() if hasattr(launch_result, 'to_dict') else {}

            elif action == "send_message":
                recipient = step.get("recipient", "")
                message = step.get("message", "")
                app = step.get("app", "whatsapp")
                contact_store = get_contact_store()
                contact = contact_store.resolve(recipient)
                phone = contact.phone if contact else None
                resolved = contact.display_name if contact else recipient
                p1.action_target = resolved
                actions_executed = []

                if app == "whatsapp" and phone:
                    try:
                        wa_pkg = await self.adb.resolve_package_dynamic(device_id, "whatsapp") or "com.whatsapp"
                        await self.adb.shell(device_id, f'am start -a android.intent.action.SENDTO -d "smsto:{phone}" -n "{wa_pkg}/.Conversation"')
                        actions_executed.append("opened_whatsapp_deep_link")
                        await asyncio.sleep(2)
                        if message:
                            safe_msg = message.replace(" ", "%s").replace("'", "")
                            await self.adb.shell(device_id, f"input text '{safe_msg}'")
                            actions_executed.append("typed_message")
                            await asyncio.sleep(0.5)
                            await self.adb.press_key(device_id, 66)
                            actions_executed.append("pressed_send")
                            await asyncio.sleep(1)
                    except Exception as e:
                        actions_executed.append(f"deep_link_failed:{e}")
                else:
                    try:
                        await self.adb.open_app(device_id, app)
                        actions_executed.append(f"opened_{app}")
                        await asyncio.sleep(2)
                        if message:
                            safe_msg = message.replace(" ", "%s").replace("'", "")
                            await self.adb.shell(device_id, f"input text '{safe_msg}'")
                            actions_executed.append("typed_message")
                            await asyncio.sleep(0.5)
                            await self.adb.press_key(device_id, 66)
                            actions_executed.append("pressed_send")
                    except Exception as e:
                        actions_executed.append(f"app_open_failed:{e}")

                p1.success = True
                p1.status = "completed"
                p1.details = {"actions": actions_executed, "recipient": resolved, "phone": phone}

            elif action == "open_chat":
                recipient = step.get("recipient", "")
                app = step.get("app", "instagram")
                contact_store = get_contact_store()
                contact = contact_store.resolve(recipient)
                phone = contact.phone if contact else None
                resolved = contact.display_name if contact else recipient
                p1.action_target = resolved

                if app == "whatsapp" and phone:
                    try:
                        wa_pkg = await self.adb.resolve_package_dynamic(device_id, "whatsapp") or "com.whatsapp"
                        await self.adb.shell(device_id, f'am start -a android.intent.action.SENDTO -d "smsto:{phone}" -n "{wa_pkg}/.Conversation"')
                        p1.success = True
                    except Exception:
                        await self.adb.open_app(device_id, app)
                        p1.success = True
                else:
                    await self.adb.open_app(device_id, app)
                    p1.success = True
                p1.status = "completed"

            elif action == "reply":
                message = step.get("message", "")
                if message:
                    safe_msg = message.replace(" ", "%s").replace("'", "")
                    await self.adb.shell(device_id, f"input text '{safe_msg}'")
                    await asyncio.sleep(0.5)
                    await self.adb.press_key(device_id, 66)
                p1.success = True
                p1.status = "completed"

            elif action == "take_screenshot":
                png_data = await self.adb.screencap(device_id, "")
                filename = f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
                import os
                save_dir = os.path.join(os.path.dirname(__file__), "..", "data", "screenshots")
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(png_data)
                p1.success = True
                p1.status = "completed"
                p1.details = {"filepath": filepath}

            elif action == "check_battery":
                try:
                    output = await self.adb.shell(device_id, "dumpsys battery")
                    p1.success = True
                    p1.status = "completed"
                    p1.details = {"battery_info": output}
                except Exception as e:
                    p1.success = False
                    p1.status = "failed"
                    p1.details = {"error": f"Battery check failed: {str(e)}"}

            elif action == "get_foreground_app":
                try:
                    fg = await self.adb.get_foreground_app(device_id)
                    p1.success = True
                    p1.status = "completed"
                    p1.details = {"foreground_app": fg}
                except Exception as e:
                    p1.details = {"foreground_app": "unknown", "error": str(e)}
                    p1.success = True

            elif action == "open_settings":
                await self.adb.open_app(device_id, "settings")
                p1.success = True
                p1.status = "completed"

            elif action == "call_contact":
                recipient = step.get("recipient", "")
                contact_store = get_contact_store()
                contact = contact_store.resolve(recipient)
                phone = contact.phone if contact else None
                if phone:
                    await self.adb.shell(device_id, f'am start -a android.intent.action.DIAL -d "tel:{phone}"')
                p1.success = True
                p1.status = "completed"
                p1.action_target = recipient

            elif action == "navigate_home":
                await self.adb.shell(device_id, "input keyevent KEYCODE_HOME")
                await asyncio.sleep(1)
                p1.success = True
                p1.status = "completed"

            elif action == "go_back":
                await self.adb.shell(device_id, "input keyevent KEYCODE_BACK")
                await asyncio.sleep(0.5)
                p1.success = True
                p1.status = "completed"

            elif action == "scroll":
                direction = step.get("direction", "down")
                if direction == "down":
                    await self.adb.shell(device_id, "input swipe 500 1000 500 200")
                else:
                    await self.adb.shell(device_id, "input swipe 500 200 500 1000")
                await asyncio.sleep(1)
                p1.success = True
                p1.status = "completed"

            elif action == "navigate":
                screen = step.get("screen", "")
                app = step.get("app", "")
                if app:
                    await self.adb.open_app(device_id, app)
                    await asyncio.sleep(2)
                p1.success = True
                p1.status = "completed"
                p1.action_target = screen

            else:
                p1.success = True
                p1.status = "completed"
                p1.details = {"note": f"action {action} executed (phase1)"}

        except Exception as e:
            logger.error(f"Phase 1 action '{action}' failed: {e}")
            p1.success = False
            p1.status = "failed"
            p1.details = {"error": str(e), "action": action}

        p1.duration_ms = int((datetime.utcnow() - p1_start).total_seconds() * 1000)

        await self._emit(workflow_id, EventType.EXECUTION_COMPLETED if p1.success else EventType.EXECUTION_FAILED, {
            "phase": "phase1", "action": action, "success": p1.success,
            "duration_ms": p1.duration_ms,
        }, device_id=device_id, severity="error" if not p1.success else "info")

        return p1

    async def _execute_phase2(
        self,
        step: Dict[str, Any],
        device_id: str,
        workflow_id: str,
    ) -> Phase2Result:
        action = step.get("action", "capture_and_analyze")
        p2 = Phase2Result(device_id=device_id)
        p2_start = datetime.utcnow()

        await self._emit(workflow_id, EventType.SCREEN_CHANGED, {
            "phase": "phase2", "action": action, "device_id": device_id,
        }, device_id=device_id)

        try:
            capture = await self.screen_capture.capture_from_adb(device_id)
            if not capture.success or capture.image is None:
                p2.success = False
                p2.details = {"error": capture.error or "capture_failed"}
                p2.duration_ms = int((datetime.utcnow() - p2_start).total_seconds() * 1000)
                return p2

            ocr = await self.ocr_service.extract_text(capture.image)
            ui = await self.ui_detector.detect_elements(capture.image)
            classification = await self.screen_classifier.classify(
                image=capture.image,
                foreground_app=None,
                text_content=ocr.full_text,
                ui_result=ui,
            )

            p2.screen_type = classification.screen_type.value
            p2.app_name = classification.app_name or ""
            p2.screen_name = classification.screen_name or classification.screen_type.value
            p2.full_text = ocr.full_text[:500]
            p2.text_count = len(ocr.texts)
            p2.ui_elements = len(ui.elements)
            p2.classification_confidence = classification.confidence
            p2.classification_reason = classification.classification_reason or ""
            p2.filepath = capture.filepath or ""

            record = self.phone_memory.record_screen(
                device_id=device_id,
                screen_type=classification.screen_type,
                app_name=classification.app_name,
                screen_name=classification.screen_name,
                filepath=capture.filepath,
                text_content=ocr.full_text,
                elements=ui.elements,
            )
            p2.has_memory_record = record is not None

            p2.success = True
            p2.details = {
                "ocr_words": len(ocr.texts),
                "ui_buttons": len(ui.buttons),
                "ui_inputs": len(ui.inputs),
            }

            verification_ok = True
            if action == "verify_and_classify" or action == "verify_send_message":
                expected = step.get("expected", "")
                if expected == "app":
                    ver = await self.visual_verifier.verify_app_opened(device_id, step.get("app", ""))
                    verification_ok = ver.passed
                elif expected == "chat":
                    ver = await self.visual_verifier.verify_chat_opened(
                        device_id, step.get("recipient", ""), step.get("app", "")
                    )
                    verification_ok = ver.passed
                elif action == "verify_send_message":
                    message = step.get("message", "")
                    ver = await self.visual_verifier.verify_message_sent(device_id, message)
                    verification_ok = ver.passed

            if not verification_ok:
                p2.details["verification_warning"] = "visual verification had low confidence"

        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            p2.success = False
            p2.details = {"error": str(e)}

        p2.duration_ms = int((datetime.utcnow() - p2_start).total_seconds() * 1000)
        return p2

    async def _execute_phase3(
        self,
        step: Dict[str, Any],
        command: str,
        device_id: str,
        workflow_id: str,
    ) -> Phase3Result:
        action = step.get("action", "store_context")
        p3 = Phase3Result()
        p3_start = datetime.utcnow()

        await self._emit(workflow_id, EventType.CONTEXT_UPDATED, {
            "phase": "phase3", "action": action, "device_id": device_id,
        }, device_id=device_id)

        try:
            if action == "knowledge_search":
                is_file_query = any(w in command.lower() for w in ["find", "where", "locate", "search"]) and \
                    any(w in command.lower() for w in ["file", "note", "document", "pdf"])
                if is_file_query:
                    response = await self.knowledge_agent.find_file(command)
                else:
                    response = await self.knowledge_agent.answer(command)

                p3.knowledge_answer = response.answer
                p3.knowledge_confidence = response.confidence
                p3.sources = response.sources or []
                p3.documents_retrieved = len(response.sources) if response.sources else 0
                p3.suggestions = response.suggestions or []
                p3.reasoning = "knowledge_search_completed"

            elif action == "reason_about_screen":
                screen_ctx = self.phone_memory.get_context_summary(device_id) if hasattr(self.phone_memory, 'get_context_summary') else {}
                screen_text = screen_ctx.get("current_text", "") if isinstance(screen_ctx, dict) else ""
                app = screen_ctx.get("current_app", "") if isinstance(screen_ctx, dict) else ""

                p3.reasoning = f"Screen analysis: app={app}, text_content_length={len(screen_text)}"
                has_text = len(screen_text) > 0
                if has_text:
                    response = await self.knowledge_agent.answer(f"What is on this screen? Content: {screen_text[:500]}")
                    p3.knowledge_answer = response.answer
                else:
                    p3.knowledge_answer = f"You are viewing {app if app else 'the current screen'}."
                p3.knowledge_confidence = 0.8 if has_text else 0.5

            elif action == "store_context":
                context_type = step.get("context_type", "generic")

                ctx_update = {
                    "current_device_id": device_id,
                    "current_screen_type": context_type,
                    "last_command": command,
                    "last_intent": context_type,
                }

                app_name = step.get("app", "")
                if app_name:
                    ctx_update["current_app"] = app_name
                recipient = step.get("recipient", "")
                if recipient:
                    ctx_update["current_chat"] = recipient

                self.context_engine.update(**ctx_update)
                p3.context_updated = True
                p3.memory_stored = True

                if context_type in ("app_opened", "chat_opened", "message_sent", "reply_sent"):
                    p3.reasoning = f"Context stored: {context_type}"
                    p3.knowledge_answer = ""

            p3.success = True

        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            p3.success = False
            p3.details = {"error": str(e)}

        p3.duration_ms = int((datetime.utcnow() - p3_start).total_seconds() * 1000)
        return p3

    def _build_assistant_context(
        self,
        intent: UnifiedIntentType,
        slots: Dict[str, Any],
        result: UnifiedCommandResult,
        device_id: str,
    ) -> AssistantContext:
        ctx = AssistantContext()
        ctx.current_device_id = device_id
        ctx.last_command = result.command
        ctx.last_intent = intent.value
        ctx.last_target = result.target or ""
        ctx.current_workflow_id = result.workflow_id
        ctx.current_workflow_type = intent.value

        if result.phase2:
            ctx.current_app = result.phase2.app_name
            ctx.current_screen = result.phase2.screen_name
            ctx.current_screen_type = result.phase2.screen_type

        if result.phase3 and result.phase3.sources:
            ctx.current_documents = [s.get("file_name", "") for s in result.phase3.sources[:5]]

        if result.phase3 and result.phase3.knowledge_answer:
            ctx.current_knowledge_context = result.phase3.knowledge_answer[:200]

        context_snapshot = self.context_engine.get_current()
        if context_snapshot:
            if hasattr(context_snapshot, 'recent_screens'):
                ctx.recent_screens = list(context_snapshot.recent_screens)[-10:] if context_snapshot.recent_screens else []
            if hasattr(context_snapshot, 'metadata'):
                ctx.metadata = dict(context_snapshot.metadata)

        return ctx

    def _generate_assistant_reply(self, result: UnifiedCommandResult) -> str:
        intent = result.intent
        target = result.target

        if not result.success:
            return f"I couldn't complete that request. Please try again."

        if intent == "open_app":
            return f"{target.title()} is ready." if target else "App is open."
        if intent == "send_message":
            return f"Message sent to {target}."
        if intent == "open_chat":
            return f"{target} chat is open." if target else "Chat is open."
        if intent == "reply":
            return "Message sent."
        if intent == "take_screenshot":
            return "Screenshot captured."
        if intent == "check_battery":
            details = result.phase1.details if result.phase1 else {}
            battery = details.get("battery_info", "")
            if battery:
                return f"Your battery: {battery[:100]}"
            return "Battery check complete."
        if intent == "foreground_app":
            details = result.phase1.details if result.phase1 else {}
            fg = details.get("foreground_app", "")
            return f"The current app is {fg}." if fg else "Foreground app checked."
        if intent == "open_settings":
            return "Settings opened."
        if intent == "call_contact":
            return f"Calling {target}." if target else "Call initiated."
        if intent == "knowledge_query":
            p3 = result.phase3
            if p3 and p3.knowledge_answer:
                answer = p3.knowledge_answer
                if len(answer) > 200:
                    answer = answer[:200] + "..."
                return answer
            return "I found some information for you."
        if intent == "screen_aware":
            p3 = result.phase3
            if p3 and p3.knowledge_answer:
                return p3.knowledge_answer
            p2 = result.phase2
            if p2:
                return f"You are viewing {p2.app_name or 'the current screen'}."
            return "I can see your screen."
        if intent == "navigate_home":
            return "Navigated to home screen."
        if intent == "go_back":
            return "Went back."
        if intent == "scroll":
            return "Scrolled."
        if intent in ("navigate",):
            return f"Navigated to {target}." if target else "Navigation complete."

        return "Command completed."

    async def _emit(self, workflow_id, event_type, payload, source="interconnection", severity="info", user_id=None, device_id=None):
        try:
            sev = EventSeverity.INFO if severity == "info" else EventSeverity.ERROR
            await self.event_manager.emit(
                workflow_id=workflow_id or "unified",
                event_type=event_type,
                payload=payload,
                source=source,
                severity=sev,
                user_id=user_id,
                device_id=device_id,
            )
        except Exception:
            pass


def get_interconnection_workflow():
    return InterconnectionWorkflow()
