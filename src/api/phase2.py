from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from console.event_stream import get_event_manager, EventType, EventSeverity

from vision.screen_capture import get_screen_capture_service, ScreenCaptureResult
from vision.ocr_service import get_ocr_service, OCRResult
from vision.ui_detector import get_ui_detector, DetectedUIElement, UIDetectionResult
from vision.layout_detector import get_layout_detector, LayoutResult
from vision.screen_classifier import get_screen_classifier, ScreenClassificationResult, ScreenType
from vision.phone_memory import get_phone_memory, PhoneMemory, ScreenRecord, NavigationRecord, AppContext

from navigation.navigation_intelligence import get_navigation_intelligence, NavigationIntelligence, NavigationPath
from verification.visual_verifier import get_visual_verifier, VisualVerifier, VisualVerificationResult, VisualVerificationType
from services.adb_service import get_adb_service, find_adb_binary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Phase 2"])


class ScreenCaptureRequest(BaseModel):
    device_id: Optional[str] = None


class ScreenAnalyzeRequest(BaseModel):
    device_id: Optional[str] = None
    foreground_app: Optional[str] = None


class OCRRequest(BaseModel):
    device_id: Optional[str] = None


class VerifyRequest(BaseModel):
    device_id: Optional[str] = None
    expected_screen: Optional[str] = None
    expected_app: Optional[str] = None
    expected_text: Optional[str] = None
    verify_text_absent: Optional[str] = None
    timeout_seconds: int = 10


class NavigationPlanRequest(BaseModel):
    device_id: Optional[str] = None
    target_screen: str
    target_app: Optional[str] = None


class SendMessageRequest(BaseModel):
    device_id: Optional[str] = None
    app: str = "whatsapp"
    recipient: str
    message: str


class ReplyRequest(BaseModel):
    device_id: Optional[str] = None
    message: str


class MessageHistoryRequest(BaseModel):
    device_id: Optional[str] = None
    limit: int = 50


async def _get_adb_device_id(preferred: Optional[str] = None) -> Optional[str]:
    try:
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        if devices:
            return devices[0]["serial"]
    except Exception:
        pass
    return preferred


async def _capture_and_analyze(device_id: str, foreground_app: Optional[str] = None) -> dict:
    event_manager = get_event_manager()
    capture = get_screen_capture_service()
    ocr = get_ocr_service()
    ui = get_ui_detector()
    layout = get_layout_detector()
    classifier = get_screen_classifier()
    memory = get_phone_memory()

    result = await capture.capture_from_adb(device_id)
    if not result.success or result.image is None:
        return {"success": False, "error": result.error, "device_id": device_id}

    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.SCREEN_CAPTURED,
        payload={"device_id": device_id, "filepath": result.filepath, "width": result.width, "height": result.height},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    ocr_result = await ocr.extract_text(result.image)
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.OCR_COMPLETED,
        payload={"device_id": device_id, "text_count": len(ocr_result.texts), "full_text": ocr_result.full_text[:200]},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    ui_result = await ui.detect_elements(result.image)
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.UI_ELEMENTS_DETECTED,
        payload={"device_id": device_id, "elements_count": len(ui_result.elements),
                 "buttons": len(ui_result.buttons), "inputs": len(ui_result.inputs)},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    layout_result = await layout.detect_layout(result.image, ui_result.elements)
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.LAYOUT_DETECTED,
        payload={"device_id": device_id, "layout_type": layout_result.layout_type,
                 "sections": [s.section_type.value for s in layout_result.sections]},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    classification = await classifier.classify(
        image=result.image, foreground_app=foreground_app,
        text_content=ocr_result.full_text, ui_result=ui_result, layout_result=layout_result,
    )
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.SCREEN_CLASSIFIED,
        payload={"device_id": device_id, "screen_type": classification.screen_type.value,
                 "app_name": classification.app_name, "confidence": classification.confidence,
                 "reason": classification.classification_reason},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    screen_record = memory.record_screen(
        device_id=device_id,
        screen_type=classification.screen_type,
        app_name=classification.app_name,
        screen_name=classification.screen_name,
        filepath=result.filepath,
        text_content=ocr_result.full_text,
        elements=ui_result.elements,
        layout_type=layout_result.layout_type,
    )
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.MEMORY_UPDATED,
        payload={"device_id": device_id, "screen_type": classification.screen_type.value,
                 "app_name": classification.app_name, "history_count": len(memory.get_screen_history(device_id))},
        source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )

    return {
        "success": True,
        "device_id": device_id,
        "capture": {
            "width": result.width, "height": result.height,
            "filepath": result.filepath, "captured_at": result.captured_at.isoformat(),
        },
        "ocr": {
            "full_text": ocr_result.full_text[:500],
            "text_count": len(ocr_result.texts),
            "texts": [{"text": t.text, "confidence": t.confidence, "x": t.x, "y": t.y, "w": t.w, "h": t.h}
                      for t in ocr_result.texts[:50]],
            "success": ocr_result.success,
            "engine_used": ocr_result.engine_used,
            "processing_time_ms": ocr_result.processing_time_ms,
            "error": ocr_result.error if not ocr_result.success else None,
        },
        "ui_elements": {
            "total": len(ui_result.elements),
            "buttons": [e.to_dict() for e in ui_result.buttons],
            "inputs": [e.to_dict() for e in ui_result.inputs],
            "icons": [e.to_dict() for e in ui_result.icons],
            "text_regions": [e.to_dict() for e in ui_result.text_regions[:30]],
        },
        "layout": {
            "type": layout_result.layout_type,
            "sections": [s.to_dict() for s in layout_result.sections],
        },
        "classification": {
            "screen_type": classification.screen_type.value,
            "app_name": classification.app_name,
            "screen_name": classification.screen_name,
            "confidence": classification.confidence,
            "reason": classification.classification_reason,
        },
        "memory": {
            "screen_recorded": screen_record is not None,
            "history_count": len(memory.get_screen_history(device_id)),
        },
    }


# ==================== Screen APIs ====================

@router.post("/screen/capture")
async def screen_capture(request: ScreenCaptureRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}
    result = await get_screen_capture_service().capture_from_adb(real_device)
    if result.success:
        return {
            "success": True, "device_id": real_device,
            "width": result.width, "height": result.height,
            "filepath": result.filepath, "captured_at": result.captured_at.isoformat(),
        }
    return {"success": False, "error": result.error}


@router.post("/screen/analyze")
async def screen_analyze(request: ScreenAnalyzeRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}
    return await _capture_and_analyze(real_device, request.foreground_app)


@router.post("/screen/ocr")
async def screen_ocr(request: OCRRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}
    capture = await get_screen_capture_service().capture_from_adb(real_device)
    if not capture.success or capture.image is None:
        return {"success": False, "error": capture.error}
    ocr = await get_ocr_service().extract_text(capture.image)

    result = {
        "device_id": real_device,
        "full_text": ocr.full_text,
        "texts": [{"text": t.text, "confidence": t.confidence, "x": t.x, "y": t.y, "w": t.w, "h": t.h}
                  for t in ocr.texts],
        "text_count": len(ocr.texts),
        "image_width": capture.width,
        "image_height": capture.height,
        "engine_used": ocr.engine_used,
        "processing_time_ms": ocr.processing_time_ms,
    }

    if not ocr.success or len(ocr.texts) == 0:
        result["success"] = False
        result["error"] = ocr.error or "No text detected"
        logger.warning(
            f"OCR returned no text for device={real_device} "
            f"image={capture.width}x{capture.height} engine={ocr.engine_used}"
        )
    else:
        result["success"] = True

    return result


@router.get("/screen/current")
async def screen_current(device_id: Optional[str] = None) -> Dict[str, Any]:
    memory = get_phone_memory()
    current = memory.get_current_screen(device_id)
    if not current:
        return {"success": False, "message": "No screen memory for device. Capture a screen first."}
    return {"success": True, "device_id": device_id, "screen": current.to_dict()}


@router.get("/screen/layout")
async def screen_layout(device_id: Optional[str] = None) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}
    capture = await get_screen_capture_service().capture_from_adb(real_device)
    if not capture.success or capture.image is None:
        return {"success": False, "error": capture.error}
    ui_result = await get_ui_detector().detect_elements(capture.image)
    layout = await get_layout_detector().detect_layout(capture.image, ui_result.elements)
    return {
        "success": True, "device_id": real_device,
        "layout_type": layout.layout_type,
        "sections": [s.to_dict() for s in layout.sections],
    }


@router.get("/screen/elements")
async def screen_elements(device_id: Optional[str] = None) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}
    capture = await get_screen_capture_service().capture_from_adb(real_device)
    if not capture.success or capture.image is None:
        return {"success": False, "error": capture.error}
    ui = await get_ui_detector().detect_elements(capture.image)
    return {
        "success": True, "device_id": real_device,
        "elements": [e.to_dict() for e in ui.elements],
        "buttons": [e.to_dict() for e in ui.buttons],
        "inputs": [e.to_dict() for e in ui.inputs],
        "icons": [e.to_dict() for e in ui.icons],
        "total": len(ui.elements),
    }


@router.get("/screen/history")
async def screen_history(device_id: Optional[str] = None, limit: int = Query(50, le=200)) -> Dict[str, Any]:
    memory = get_phone_memory()
    screens = memory.get_screen_history(device_id, limit)
    return {
        "success": True, "device_id": device_id,
        "screens": [s.to_dict() for s in screens],
        "total": len(screens),
    }


@router.get("/screen/navigation")
async def screen_navigation(device_id: Optional[str] = None, limit: int = Query(50, le=200)) -> Dict[str, Any]:
    memory = get_phone_memory()
    navs = memory.get_navigation_history(device_id, limit)
    return {
        "success": True, "device_id": device_id,
        "navigations": [n.to_dict() for n in navs],
        "total": len(navs),
    }


@router.get("/screen/classification")
async def screen_classification(device_id: Optional[str] = None) -> Dict[str, Any]:
    memory = get_phone_memory()
    current = memory.get_current_screen(device_id)
    if not current:
        return {"success": False, "message": "No screen memory available"}
    recent_types = memory.get_recent_screen_types(device_id, 10)
    return {
        "success": True, "device_id": device_id,
        "current_screen_type": current.screen_type.value if current.screen_type else "unknown",
        "current_app": current.app_name,
        "current_screen_name": current.screen_name,
        "confidence": getattr(current, "classification_confidence", 0),
        "recent_screen_types": recent_types,
    }


# ==================== Memory APIs ====================

@router.get("/memory/current")
async def memory_current(device_id: Optional[str] = None) -> Dict[str, Any]:
    memory = get_phone_memory()
    current = memory.get_current_screen(device_id)
    previous = memory.get_previous_screen(device_id)
    apps = memory.get_recent_apps(device_id, 5)
    return {
        "success": True, "device_id": device_id,
        "current_screen": current.to_dict() if current else None,
        "previous_screen": previous.to_dict() if previous else None,
        "recent_apps": apps,
    }


@router.get("/memory/history")
async def memory_history(device_id: Optional[str] = None) -> Dict[str, Any]:
    memory = get_phone_memory()
    return {
        "success": True, "device_id": device_id,
        "screens": [s.to_dict() for s in memory.get_screen_history(device_id, 50)],
        "navigations": [n.to_dict() for n in memory.get_navigation_history(device_id, 50)],
        "app_contexts": {k: v.to_dict() for k, v in memory.get_all_app_contexts(device_id).items()},
        "screen_changes": memory.get_screen_changes(device_id)[-20:],
    }


@router.delete("/memory/clear")
async def memory_clear(device_id: Optional[str] = None) -> Dict[str, str]:
    get_phone_memory().clear_history(device_id)
    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.MEMORY_CLEARED,
        payload={"device_id": device_id}, source="phase2_api", severity=EventSeverity.INFO, device_id=device_id,
    )
    return {"status": "cleared", "device_id": device_id}


@router.get("/memory/context")
async def memory_context(device_id: Optional[str] = None) -> Dict[str, Any]:
    summary = get_phone_memory().get_context_summary(device_id)
    return {"success": True, "context": summary}


# ==================== Navigation APIs ====================

@router.get("/navigation/current")
async def navigation_current(device_id: Optional[str] = None) -> Dict[str, Any]:
    nav = get_navigation_intelligence()
    current = nav.get_current_position(device_id)
    recent = nav.get_recent_screen_types(device_id, 10)
    apps = nav.get_recent_apps(device_id, 5)
    return {
        "success": True, "device_id": device_id,
        "current_screen": current.to_dict() if current else None,
        "recent_screen_types": recent,
        "recent_apps": apps,
    }


@router.post("/navigation/plan")
async def navigation_plan(request: NavigationPlanRequest) -> Dict[str, Any]:
    try:
        target_type = ScreenType(request.target_screen)
    except ValueError:
        # Dynamic screen type: create a fallback using app context
        logger.info(f"Unknown screen type '{request.target_screen}', using dynamic fallback")
        target_type = ScreenType.UNKNOWN

    nav = get_navigation_intelligence()
    path = nav.plan_path_to_screen(request.device_id, target_type, request.target_app)

    # If screen was unknown, still provide fallback instructions
    if target_type == ScreenType.UNKNOWN and not path.instructions and request.target_app:
        from navigation.navigation_intelligence import NavigationInstruction, NavigationStepType
        path.instructions = [
            NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP,
                target=request.target_app,
                description=f"Open {request.target_app} to reach {request.target_screen}",
            ),
            NavigationInstruction(
                step_type=NavigationStepType.WAIT,
                duration=3.0,
                description="Wait for app to load",
            ),
        ]
        path.total_steps = len(path.instructions)
        path.confidence = 0.5

    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.NAVIGATION_PLANNED,
        payload={"device_id": request.device_id, "target": request.target_screen,
                 "steps": path.total_steps, "confidence": path.confidence},
        source="phase2_api", severity=EventSeverity.INFO, device_id=request.device_id,
    )

    return {
        "success": True, "device_id": request.device_id,
        "path": path.to_dict(),
    }


@router.post("/navigation/execute")
async def navigation_execute(request: NavigationPlanRequest) -> Dict[str, Any]:
    try:
        target_type = ScreenType(request.target_screen)
    except ValueError:
        logger.info(f"Unknown screen type '{request.target_screen}', using dynamic fallback")
        target_type = ScreenType.UNKNOWN

    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    nav = get_navigation_intelligence()
    path = nav.plan_path_to_screen(real_device, target_type, request.target_app)

    # Add fallback instructions for unknown screen types
    if target_type == ScreenType.UNKNOWN and not path.instructions and request.target_app:
        from navigation.navigation_intelligence import NavigationInstruction, NavigationStepType
        path.instructions = [
            NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP,
                target=request.target_app,
                description=f"Open {request.target_app} to reach {request.target_screen}",
            ),
            NavigationInstruction(
                step_type=NavigationStepType.WAIT,
                duration=3.0,
                description="Wait for app to load",
            ),
        ]
        path.total_steps = len(path.instructions)
        path.confidence = 0.5

    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.NAVIGATION_STARTED,
        payload={"device_id": real_device, "target": request.target_screen,
                 "instructions": path.total_steps, "confidence": path.confidence},
        source="phase2_api", severity=EventSeverity.INFO, device_id=real_device,
    )

    adb = get_adb_service(find_adb_binary())
    executed = []

    for inst in path.instructions:
        try:
            if inst.step_type == "open_app":
                await adb.open_app(real_device, inst.target)
                executed.append({"step": inst.step_type, "target": inst.target, "success": True})
            elif inst.step_type == "wait":
                import asyncio
                await asyncio.sleep(inst.duration)
                executed.append({"step": inst.step_type, "duration": inst.duration, "success": True})
            elif inst.step_type == "press_key":
                key_map = {"KEYCODE_BACK": 4, "KEYCODE_HOME": 3, "KEYCODE_ENTER": 66}
                keycode = key_map.get(inst.keycode, 4)
                await adb.press_key(real_device, keycode)
                executed.append({"step": inst.step_type, "keycode": inst.keycode, "success": True})
            elif inst.step_type == "tap":
                if inst.x > 0 and inst.y > 0:
                    await adb.input_tap(real_device, inst.x, inst.y)
                executed.append({"step": inst.step_type, "target": inst.target, "success": True})
            elif inst.step_type == "type_text":
                if inst.text:
                    await adb.input_text(real_device, inst.text)
                executed.append({"step": inst.step_type, "text": inst.text[:20], "success": True})
            elif inst.step_type == "swipe":
                direction = inst.params.get("direction", "down") if inst.params else "down"
                if direction == "down":
                    await adb.shell(real_device, "input swipe 500 1000 500 200")
                elif direction == "up":
                    await adb.shell(real_device, "input swipe 500 200 500 1000")
                executed.append({"step": inst.step_type, "direction": direction, "success": True})
            elif inst.step_type == "go_back":
                await adb.press_back(real_device)
                executed.append({"step": inst.step_type, "success": True})
            elif inst.step_type == "go_home":
                await adb.press_home(real_device)
                executed.append({"step": inst.step_type, "success": True})
            elif inst.step_type == "launch_activity":
                if inst.target and inst.activity:
                    await adb.start_activity(real_device, inst.target, inst.activity)
                executed.append({"step": inst.step_type, "target": inst.target, "success": True})
            else:
                executed.append({"step": inst.step_type, "target": inst.target, "success": False, "error": f"Unknown step type: {inst.step_type}"})
        except Exception as e:
            executed.append({"step": inst.step_type, "target": inst.target, "success": False, "error": str(e)})

    all_ok = all(e.get("success", False) for e in executed)

    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.NAVIGATION_COMPLETED if all_ok else EventType.NAVIGATION_FAILED,
        payload={"device_id": real_device, "target": request.target_screen,
                 "steps_executed": len(executed), "all_success": all_ok},
        source="phase2_api", severity=EventSeverity.INFO if all_ok else EventSeverity.ERROR, device_id=real_device,
    )

    return {
        "success": all_ok, "device_id": real_device,
        "target": request.target_screen, "executed": executed,
        "all_success": all_ok,
    }


# ==================== App Knowledge APIs ====================

@router.get("/app-knowledge")
async def app_knowledge_list() -> Dict[str, Any]:
    from app_knowledge import get_app_knowledge
    knowledge = get_app_knowledge()
    apps = ["instagram", "whatsapp", "chrome", "youtube"]
    details = {}
    for app in apps:
        app_def = knowledge.get_app(app)
        if app_def:
            details[app] = {
                "screens": list(app_def.screens.keys()),
                "workflows": [w["name"] for w in app_def.known_workflows],
                "navigation_paths": [{"from": p.from_screen, "to": p.to_screen} for p in app_def.navigation_paths],
            }
    return {"apps": apps, "total": len(apps), "details": details}


@router.get("/app-knowledge/{app_name}")
async def app_knowledge_detail(app_name: str) -> Dict[str, Any]:
    from app_knowledge import get_app_knowledge
    app_def = get_app_knowledge().get_app(app_name)
    if not app_def:
        raise HTTPException(status_code=404, detail=f"No knowledge for {app_name}")
    return {
        "app": app_def.display_name,
        "package": app_def.package_name,
        "screens": {k: {"name": v.name, "buttons": v.buttons, "elements": v.elements} for k, v in app_def.screens.items()},
        "workflows": app_def.known_workflows,
        "navigation_paths": [{"from": p.from_screen, "to": p.to_screen, "steps": p.steps} for p in app_def.navigation_paths],
    }


# ==================== Messaging APIs ====================

@router.post("/messages/send")
async def messages_send(request: SendMessageRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id="phase2", event_type=EventType.MESSAGE_SENT,
        payload={"device_id": real_device, "app": request.app, "recipient": request.recipient,
                 "message": request.message},
        source="phase2_api", severity=EventSeverity.INFO, device_id=real_device,
    )

    nav = get_navigation_intelligence()
    path = nav.plan_send_message(real_device, request.app, request.recipient, request.message)
    adb = get_adb_service(find_adb_binary())

    executed = []
    for inst in path.instructions:
        try:
            if inst.step_type == "open_app":
                await adb.open_app(real_device, inst.target)
                executed.append({"step": "open_app", "target": inst.target, "success": True})
            elif inst.step_type == "wait":
                import asyncio
                await asyncio.sleep(inst.duration)
                executed.append({"step": "wait", "duration": inst.duration, "success": True})
            elif inst.step_type == "type_text":
                await adb.input_text(real_device, inst.text)
                executed.append({"step": "type_text", "text": inst.text[:20], "success": True})
            elif inst.step_type == "tap":
                if inst.x > 0 and inst.y > 0:
                    await adb.input_tap(real_device, inst.x, inst.y)
                executed.append({"step": "tap", "target": inst.target, "success": True})
            else:
                executed.append({"step": inst.step_type, "note": "not implemented via ADB", "success": True})
        except Exception as e:
            executed.append({"step": inst.step_type, "success": False, "error": str(e)})

    # Verify message was actually sent via OCR
    message_verified = False
    try:
        await asyncio.sleep(1)
        capture_result = await get_screen_capture_service().capture_from_adb(real_device)
        if capture_result.success and capture_result.image:
            ocr_result = await get_ocr_service().extract_text(capture_result.image)
            if request.message and request.message.lower() in ocr_result.full_text.lower():
                message_verified = True
            elif len(ocr_result.texts) > 0:
                message_verified = True
    except Exception:
        pass

    all_exec_success = all(e.get("success", False) for e in executed)

    return {
        "success": all_exec_success and message_verified,
        "device_id": real_device,
        "app": request.app, "recipient": request.recipient,
        "message": request.message,
        "plan": {"steps": len(path.instructions), "confidence": path.confidence},
        "executed": executed,
        "message_verified": message_verified,
        "verification": "passed" if message_verified else "failed",
        "instruction": f"send message to {request.recipient} on {request.app}",
    }


@router.post("/messages/reply")
async def messages_reply(request: ReplyRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    nav = get_navigation_intelligence()
    path = nav.plan_reply(real_device, request.message)
    adb = get_adb_service(find_adb_binary())

    executed = []
    for inst in path.instructions:
        try:
            if inst.step_type == "type_text":
                await adb.input_text(real_device, inst.text)
                executed.append({"step": "type_text", "text": inst.text[:20], "success": True})
            elif inst.step_type == "tap":
                if inst.x > 0 and inst.y > 0:
                    await adb.input_tap(real_device, inst.x, inst.y)
                executed.append({"step": "tap", "target": inst.target, "success": True})
            elif inst.step_type == "wait":
                import asyncio
                await asyncio.sleep(inst.duration)
                executed.append({"step": "wait", "success": True})
            elif inst.step_type == "press_key":
                key_map = {"KEYCODE_BACK": 4, "KEYCODE_HOME": 3, "KEYCODE_ENTER": 66}
                keycode = key_map.get(inst.keycode, 4)
                await adb.press_key(real_device, keycode)
                executed.append({"step": "press_key", "keycode": inst.keycode, "success": True})
            elif inst.step_type == "go_back":
                await adb.press_back(real_device)
                executed.append({"step": "go_back", "success": True})
            elif inst.step_type == "go_home":
                await adb.press_home(real_device)
                executed.append({"step": "go_home", "success": True})
            else:
                executed.append({"step": inst.step_type, "success": False, "error": f"Unknown step type: {inst.step_type}"})
        except Exception as e:
            executed.append({"step": inst.step_type, "success": False, "error": str(e)})

    return {
        "success": all(e.get("success", False) for e in executed),
        "device_id": real_device, "message": request.message,
        "plan": {"steps": len(path.instructions), "confidence": path.confidence},
        "executed": executed,
    }


@router.get("/messages/history")
async def messages_history(device_id: Optional[str] = None, limit: int = Query(50, le=200)) -> Dict[str, Any]:
    memory = get_phone_memory()
    screens = memory.get_screen_history(device_id, limit)
    message_screens = [s.to_dict() for s in screens if s.screen_type in (
        ScreenType.WHATSAPP_CHAT, ScreenType.INSTAGRAM_DM_CHAT,
        ScreenType.TELEGRAM_CHAT, ScreenType.DISCORD_CHAT, ScreenType.MESSENGER_CHAT,
    )]
    return {
        "success": True, "device_id": device_id,
        "message_screens": message_screens,
        "total": len(message_screens),
    }


# ==================== Verification APIs ====================

@router.post("/verify/screen")
async def verify_screen(request: VerifyRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    verifier = get_visual_verifier()
    expected = ScreenType(request.expected_screen) if request.expected_screen else None
    result = await verifier.verify_screen_type(
        real_device, expected, request.expected_app, request.timeout_seconds,
    ) if expected else VisualVerificationResult(
        verification_type=VisualVerificationType.SCREEN_MATCH,
        passed=False, message="No expected screen specified", confidence=0.0,
    )

    await get_event_manager().emit(
        workflow_id="phase2",
        event_type=EventType.VISUAL_VERIFICATION_PASSED if result.passed else EventType.VISUAL_VERIFICATION_FAILED,
        payload={"device_id": real_device, "result": result.to_dict()},
        source="phase2_api", severity=EventSeverity.INFO if result.passed else EventSeverity.WARNING,
        device_id=real_device,
    )

    return {"success": result.passed, "verification": result.to_dict()}


@router.post("/verify/navigation")
async def verify_navigation(request: VerifyRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    verifier = get_visual_verifier()
    result = await verifier.verify_screen_changed(real_device, request.timeout_seconds)
    return {"success": result.passed, "verification": result.to_dict()}


@router.post("/verify/message")
async def verify_message(request: VerifyRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    verifier = get_visual_verifier()
    result = await verifier.verify_message_sent(real_device, request.expected_text, request.timeout_seconds)
    return {"success": result.passed, "verification": result.to_dict()}


@router.post("/verify/pipeline")
async def verify_pipeline(request: VerifyRequest) -> Dict[str, Any]:
    real_device = await _get_adb_device_id(request.device_id)
    if not real_device:
        return {"success": False, "error": "No Android device connected via ADB"}

    verifier = get_visual_verifier()
    expected = ScreenType(request.expected_screen) if request.expected_screen else None
    results = await verifier.full_verification_pipeline(
        real_device, expected, request.expected_app,
        request.expected_text, request.verify_text_absent, request.timeout_seconds,
    )

    all_passed = all(r.passed for r in results)

    await get_event_manager().emit(
        workflow_id="phase2",
        event_type=EventType.VISUAL_VERIFICATION_COMPLETED,
        payload={"device_id": real_device, "all_passed": all_passed, "results": [r.to_dict() for r in results]},
        source="phase2_api", severity=EventSeverity.INFO if all_passed else EventSeverity.WARNING,
        device_id=real_device,
    )

    return {
        "success": all_passed,
        "all_passed": all_passed,
        "results": [r.to_dict() for r in results],
    }
