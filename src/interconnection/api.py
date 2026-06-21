import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Body
from pydantic import BaseModel

from console.event_stream import get_event_manager, EventType, EventSeverity
from interconnection.assistant import get_assistant_layer, AssistantLayer
from interconnection.models import AssistantContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/unified", tags=["Unified Phase1→Phase2→Phase3"])


class UnifiedCommandRequest(BaseModel):
    command: str
    user_id: str = "default"
    device_id: Optional[str] = None


class AssistantCommandRequest(BaseModel):
    message: str
    user_id: str = "default"
    device_id: Optional[str] = None


# ==================== Unified Command API ====================


@router.post("/command")
async def unified_command(request: UnifiedCommandRequest) -> Dict[str, Any]:
    """Execute a command through the complete Phase1→Phase2→Phase3 pipeline."""
    assistant = get_assistant_layer()
    reply = await assistant.process_command(
        command=request.command,
        user_id=request.user_id,
        device_id=request.device_id,
    )
    return _format_reply(reply, request.command)


@router.post("/assistant")
async def assistant_command(request: AssistantCommandRequest) -> Dict[str, Any]:
    """Send a message to the unified assistant (top-level layer above all phases)."""
    assistant = get_assistant_layer()
    reply = await assistant.process_command(
        command=request.message,
        user_id=request.user_id,
        device_id=request.device_id,
    )
    return _format_reply(reply, request.message)


@router.get("/context")
async def get_unified_context() -> Dict[str, Any]:
    """Get the current global assistant context (device, screen, knowledge, etc.)."""
    assistant = get_assistant_layer()
    return assistant.get_context_summary()


@router.get("/status")
async def get_unified_status() -> Dict[str, Any]:
    """Get unified system status across all three phases."""
    assistant = get_assistant_layer()
    ctx = assistant.get_global_context()
    return {
        "status": "active",
        "phases": {
            "phase1": {
                "name": "Device Control",
                "status": "ready",
                "device_id": ctx.current_device_id or "none",
            },
            "phase2": {
                "name": "Phone Intelligence",
                "status": "ready",
                "current_app": ctx.current_app or "none",
                "current_screen": ctx.current_screen or "unknown",
            },
            "phase3": {
                "name": "Knowledge Intelligence",
                "status": "ready",
                "knowledge_context": bool(ctx.current_knowledge_context),
                "documents_loaded": len(ctx.current_documents),
            },
            "assistant": {
                "name": "Unified AI Assistant",
                "status": "active",
                "last_command": ctx.last_command or "none",
                "last_intent": ctx.last_intent or "none",
            },
        },
        "context": ctx.to_dict(),
    }


# ==================== WebSocket for Unified Streaming ====================


@router.websocket("/ws/{client_id}")
async def unified_websocket(websocket: WebSocket, client_id: str):
    """WebSocket that streams Phase1→Phase2→Phase3 execution in real-time."""
    await websocket.accept()
    assistant = get_assistant_layer()

    await websocket.send_json({
        "event": "connected",
        "client_id": client_id,
        "message": "Unified Phase1→Phase2→Phase3 assistant ready",
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"message": data}

            message = payload.get("message", data if isinstance(data, str) else "")
            user_id = payload.get("user_id", "default")
            device_id = payload.get("device_id")

            await websocket.send_json({
                "event": "command_received",
                "command": message,
                "timestamp": datetime.utcnow().isoformat(),
            })

            reply = await assistant.process_command(
                command=message,
                user_id=user_id,
                device_id=device_id,
            )

            await websocket.send_json({
                "event": "phase1_complete",
                "success": reply.phase1_result.success if reply.phase1_result else False,
                "action": reply.phase1_result.action_type if reply.phase1_result else "",
                "target": reply.phase1_result.action_target if reply.phase1_result else "",
                "duration_ms": reply.phase1_result.duration_ms if reply.phase1_result else 0,
                "details": reply.phase1_result.details if reply.phase1_result else {},
                "timestamp": datetime.utcnow().isoformat(),
            })

            if reply.phase2_result:
                await websocket.send_json({
                    "event": "phase2_complete",
                    "success": reply.phase2_result.success,
                    "screen_type": reply.phase2_result.screen_type,
                    "app_name": reply.phase2_result.app_name,
                    "screen_name": reply.phase2_result.screen_name,
                    "classification_confidence": reply.phase2_result.classification_confidence,
                    "duration_ms": reply.phase2_result.duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            if reply.phase3_result:
                await websocket.send_json({
                    "event": "phase3_complete",
                    "success": reply.phase3_result.success,
                    "context_updated": reply.phase3_result.context_updated,
                    "knowledge_answer": reply.phase3_result.knowledge_answer[:300] if reply.phase3_result.knowledge_answer else "",
                    "documents_retrieved": reply.phase3_result.documents_retrieved,
                    "duration_ms": reply.phase3_result.duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            await websocket.send_json({
                "event": "assistant_reply",
                "success": reply.success,
                "intent": reply.intent,
                "target": reply.target,
                "message": reply.message,
                "context": reply.assistant_context.to_dict() if reply.assistant_context else {},
                "duration_ms": reply.duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })

    except WebSocketDisconnect:
        logger.info(f"Unified WS client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Unified WS error for {client_id}: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ==================== Phase Status APIs ====================


@router.get("/phase1/status")
async def phase1_status() -> Dict[str, Any]:
    """Get Phase 1 (Device Control) status."""
    from devices import device_manager
    devices = []
    for device_id in ["laptop"]:
        dev = device_manager.get_device(device_id)
        if dev:
            devices.append({"id": device_id, "type": "windows", "status": "registered"})
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        adb = get_adb_service(find_adb_binary())
        android_devices = await adb.list_devices()
        for d in android_devices:
            devices.append({"id": d["serial"], "type": "android", "status": d.get("status", "connected")})
    except Exception:
        pass
    return {"phase": "phase1", "name": "Device Control", "devices": devices, "status": "ready"}


@router.get("/phase2/status")
async def phase2_status() -> Dict[str, Any]:
    """Get Phase 2 (Phone Intelligence) status."""
    try:
        from vision.phone_memory import get_phone_memory
        memory = get_phone_memory()
        devices_with_memory = []
        if hasattr(memory, '_screens'):
            devices_with_memory = list(memory._screens.keys())
        return {
            "phase": "phase2",
            "name": "Phone Intelligence",
            "devices_with_memory": devices_with_memory,
            "status": "ready",
        }
    except Exception as e:
        return {"phase": "phase2", "name": "Phone Intelligence", "status": "error", "error": str(e)}


@router.get("/phase3/status")
async def phase3_status() -> Dict[str, Any]:
    """Get Phase 3 (Knowledge Intelligence) status."""
    try:
        from knowledge.indexer import get_index_manager
        idx = get_index_manager()
        from knowledge.source_connectors import get_all_connectors
        connectors = get_all_connectors()
        return {
            "phase": "phase3",
            "name": "Knowledge Intelligence",
            "documents": idx.get_document_count(),
            "chunks": idx.get_chunk_count(),
            "sources": len(connectors),
            "status": "ready",
        }
    except Exception as e:
        return {"phase": "phase3", "name": "Knowledge Intelligence", "status": "error", "error": str(e)}


# ==================== Helpers ====================


def _format_reply(reply, command: str) -> Dict[str, Any]:
    return {
        "success": reply.success,
        "intent": reply.intent,
        "target": reply.target,
        "command": command,
        "assistant_reply": reply.message,
        "duration_ms": reply.duration_ms,
        "phases": {
            "phase1": {
                "success": reply.phase1_result.success if reply.phase1_result else False,
                "action": reply.phase1_result.action_type if reply.phase1_result else "",
                "target": reply.phase1_result.action_target if reply.phase1_result else "",
                "duration_ms": reply.phase1_result.duration_ms if reply.phase1_result else 0,
            },
            "phase2": {
                "success": reply.phase2_result.success if reply.phase2_result else False,
                "screen_type": reply.phase2_result.screen_type if reply.phase2_result else "",
                "app_name": reply.phase2_result.app_name if reply.phase2_result else "",
                "classification_confidence": reply.phase2_result.classification_confidence if reply.phase2_result else 0,
                "duration_ms": reply.phase2_result.duration_ms if reply.phase2_result else 0,
            },
            "phase3": {
                "success": reply.phase3_result.success if reply.phase3_result else False,
                "reasoning": (reply.phase3_result.reasoning[:100] if reply.phase3_result else ""),
                "knowledge_answer": (reply.phase3_result.knowledge_answer[:200] if reply.phase3_result else ""),
                "duration_ms": reply.phase3_result.duration_ms if reply.phase3_result else 0,
            },
        },
        "context": reply.assistant_context.to_dict() if reply.assistant_context else {},
    }
