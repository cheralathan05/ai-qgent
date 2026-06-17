"""
Production REST APIs
Complete API surface for APA-OS Backend
"""

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi import UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os
import json
import asyncio
import tempfile

from database.models import (
    Workflow, WorkflowStatus, ApprovalStatus, AuditEvent, EventSnapshot,
    CommandRecord, ExecutionRecord, WorkflowState, DeviceAction
)
from console.event_stream import EventType, EventSeverity, get_event_manager, EventQueueSubscriber
from audit.audit_manager import get_audit_manager
from devices import device_manager, AndroidDevice, DeviceStatus, WindowsDevice
from services.workflow_engine import get_workflow_engine
from services.intent_agent import get_intent_agent
from services.planner_agent import get_planner_agent
from services.voice_service import get_voice_service
from services.device_selector import get_device_selector
from services.conversation_manager import get_conversation_manager
from services.adb_service import get_adb_service
from services.device_agent import get_device_agent
from services.redis_service import get_redis_service
from config import Config
from api.life_direction import router as life_direction_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="APA-OS Backend",
    description="Advanced Personalized AI Assistant Operating System",
    version="1.0.0"
)

app.include_router(life_direction_router)


# Response Models
class WorkflowResponse(dict):
    """Workflow API response"""
    pass


class AuditLogResponse(dict):
    """Audit log response"""
    pass


class CreateWorkflowRequest(BaseModel):
    user_id: str
    command: str
    device_id: Optional[str] = None
    session_id: Optional[str] = None


class CommandRequest(BaseModel):
    command: str
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ExecuteRequest(BaseModel):
    workflow_id: str


async def get_session():
    """Get database session"""
    from database.connection import get_db_session
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def _extract_target(intent_result) -> Optional[str]:
    return intent_result.slots.get("app") or intent_result.slots.get("target")


DEFAULT_USER_ID = "phase1-user"


def _resolve_device_selection(
    command: str,
    *,
    preferred_device_id: Optional[str] = None,
    session_device_id: Optional[str] = None,
):
    """Pick the best available execution target with Android-first routing."""
    return get_device_selector().select_device(
        command,
        preferred_device_id=preferred_device_id,
        session_device_id=session_device_id,
    )


def _build_simple_response(result: Dict[str, Any], command: str, transcript: Optional[str] = None) -> Dict[str, Any]:
    """Format a user-facing response for the phase 1 command flow."""
    target = result.get("target")
    success = bool(result.get("success"))

    if success and target:
        message = f"✓ {str(target).title()} Opened Successfully"
    elif success:
        message = "✓ Command Completed Successfully"
    else:
        message = result.get("error") or "Command failed"

    payload = {
        "success": success,
        "intent": result.get("intent"),
        "target": target,
        "status": result.get("status", "completed" if success else "failed"),
        "message": message,
        "workflow_id": result.get("workflow_id"),
        "command": command,
    }

    if transcript is not None:
        payload["transcript"] = transcript

    return payload


async def _execute_user_command(
    *,
    session,
    command: str,
    user_id: Optional[str] = None,
    device_id: Optional[str] = None,
    voice_input: bool = False,
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the shared command pipeline with sensible phase 1 defaults."""
    orchestrator = get_workflow_engine(session=session)
    resolved_user_id = user_id or DEFAULT_USER_ID
    resolved_device_id = device_id or "laptop"

    return await orchestrator.execute_command(
        user_id=resolved_user_id,
        command=command,
        device_id=resolved_device_id,
        workflow_id=workflow_id,
        voice_input=voice_input,
    )


async def _refresh_android_devices() -> None:
    """Discover connected Android devices and register them in memory and the database."""
    device_agent = get_device_agent(get_adb_service(Config.get_adb_config().adb_path, Config.get_adb_config().default_timeout))
    await device_agent.discover_devices()


async def _ensure_laptop_device() -> None:
    """Register the local Windows device if it is missing."""
    if device_manager.get_device("laptop") is None:
        device_manager.register_device(
            WindowsDevice(
                device_id="laptop",
                windows_user=os.getenv("USERNAME", "local"),
            )
        )


async def bootstrap_phase1_environment() -> None:
    """Ensure the phase 1 device registry is ready for execution."""
    await _ensure_laptop_device()
    await _refresh_android_devices()


async def _create_workflow_record(
    *,
    session,
    user_id: str,
    command: str,
    intent: str,
    device_id: str,
    plan_json: Optional[List[Dict[str, Any]]],
) -> Workflow:
    workflow = Workflow(
        user_id=user_id,
        command=command,
        intent=intent,
        status=WorkflowStatus.PENDING,
        device_id=device_id,
        plan_json=plan_json,
    )
    session.add(workflow)
    session.commit()
    session.refresh(workflow)

    session.add(CommandRecord(workflow_id=workflow.id, command_text=command))
    session.add(WorkflowState(
        workflow_id=workflow.id,
        state_name="command_received",
        status="pending",
        current_step=0,
        state_data={"command": command, "intent": intent, "device_id": device_id},
    ))
    session.commit()
    return workflow


async def _record_execution(
    *,
    session,
    workflow: Workflow,
    execution_result: Dict[str, Any],
) -> str:
    execution = ExecutionRecord(
        workflow_id=workflow.id,
        status="completed" if execution_result.get("success") else "failed",
        result=execution_result,
        started_at=workflow.start_time,
        ended_at=datetime.utcnow(),
    )
    session.add(execution)
    session.add(WorkflowState(
        workflow_id=workflow.id,
        state_name="execution_finished",
        status="completed" if execution_result.get("success") else "failed",
        current_step=len(execution_result.get("results", []) or []),
        state_data=execution_result,
    ))

    for index, result in enumerate(execution_result.get("results", []) or [], start=1):
        session.add(DeviceAction(
            workflow_id=workflow.id,
            device_id=workflow.device_id or "laptop",
            action_type=result.get("type") or f"step_{index}",
            action_data=result,
            status=result.get("status", "success"),
            result=result,
            completed_at=datetime.utcnow(),
        ))

    session.commit()
    session.refresh(execution)
    return execution.id


# ==================== Workflow APIs ====================

@app.get("/workflows", tags=["Workflows"])
async def list_workflows(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    session=Depends(get_session)
) -> Dict[str, Any]:
    """
    List workflows
    
    Query Parameters:
    - user_id: Filter by user
    - status: Filter by status (pending, executing, completed, failed)
    - limit: Max results
    - offset: Pagination offset
    """
    query = session.query(Workflow)
    
    if user_id:
        query = query.filter(Workflow.user_id == user_id)
    if status:
        query = query.filter(Workflow.status == status)
    
    total = query.count()
    workflows = query.order_by(Workflow.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "workflows": [
            {
                "id": w.id,
                "user_id": w.user_id,
                "command": w.command,
                "intent": w.intent,
                "status": w.status.value,
                "start_time": w.start_time.isoformat() if w.start_time else None,
                "end_time": w.end_time.isoformat() if w.end_time else None,
                "duration_ms": w.duration_ms,
            }
            for w in workflows
        ]
    }


@app.get("/workflows/{workflow_id}", tags=["Workflows"])
async def get_workflow(
    workflow_id: str,
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Get detailed workflow information"""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": workflow.id,
        "user_id": workflow.user_id,
        "command": workflow.command,
        "intent": workflow.intent,
        "status": workflow.status.value,
        "plan": workflow.plan_json,
        "result": workflow.result,
        "error": workflow.error,
        "device_id": workflow.device_id,
        "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
        "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
        "duration_ms": workflow.duration_ms,
        "requires_approval": workflow.requires_approval,
        "approval_status": workflow.approval_status.value if workflow.approval_status else None,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


@app.post("/workflows/{workflow_id}/cancel", tags=["Workflows"])
async def cancel_workflow(
    workflow_id: str,
    session=Depends(get_session)
) -> Dict[str, str]:
    """Cancel a workflow"""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel {workflow.status.value} workflow")
    
    workflow.status = WorkflowStatus.CANCELLED
    session.commit()
    
    return {"status": "cancelled", "workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/retry", tags=["Workflows"])
async def retry_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
) -> Dict[str, str]:
    """Retry a failed workflow"""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status != WorkflowStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed workflows can be retried")
    
    # Create new workflow with same command
    from database.connection import create_workflow
    
    new_workflow_id = await create_workflow(
        user_id=workflow.user_id,
        command=workflow.command,
        intent=workflow.intent,
        device_id=workflow.device_id,
    )
    
    # Schedule execution
    background_tasks.add_task(execute_workflow_background, new_workflow_id)
    
    return {"status": "retrying", "new_workflow_id": new_workflow_id, "original_workflow_id": workflow_id}


@app.post("/workflows/{workflow_id}/replay", tags=["Workflows"])
async def replay_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
) -> Dict[str, str]:
    """Replay a completed/failed workflow with same steps"""
    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    from database.connection import create_workflow
    
    new_workflow_id = await create_workflow(
        user_id=workflow.user_id,
        command=workflow.command,
        intent=workflow.intent,
        device_id=workflow.device_id,
        plan_json=workflow.plan_json,  # Use same plan
    )
    
    background_tasks.add_task(execute_workflow_background, new_workflow_id)
    
    return {"status": "replaying", "new_workflow_id": new_workflow_id, "original_workflow_id": workflow_id}


# ==================== Approval APIs ====================

@app.get("/approvals", tags=["Approvals"])
async def list_approvals(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    session=Depends(get_session)
) -> Dict[str, Any]:
    """List pending approvals"""
    from database.models import ApprovalAction
    
    query = session.query(ApprovalAction)
    
    if status:
        query = query.filter(ApprovalAction.decision == status)
    else:
        query = query.filter(ApprovalAction.decision == None)
    
    approvals = query.order_by(ApprovalAction.requested_at.desc()).limit(limit).all()
    
    return {
        "total": len(approvals),
        "approvals": [
            {
                "id": a.id,
                "workflow_id": a.workflow_id,
                "type": a.approval_type,
                "payload": a.payload,
                "preview": a.preview,
                "explanation": a.explanation,
                "requested_at": a.requested_at.isoformat(),
                "status": a.decision.value if a.decision else "pending",
            }
            for a in approvals
        ]
    }


@app.post("/approvals/{approval_id}/approve", tags=["Approvals"])
async def approve_action(
    approval_id: str,
    decided_by: str,
    reason: Optional[str] = None,
    session=Depends(get_session)
) -> Dict[str, str]:
    """Approve an action"""
    from database.models import ApprovalAction
    
    approval = session.query(ApprovalAction).filter(ApprovalAction.id == approval_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    approval.decision = ApprovalStatus.APPROVED
    approval.decided_by = decided_by
    approval.decision_reason = reason
    approval.decision_at = datetime.utcnow()
    
    session.commit()
    
    # Emit event
    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id=approval.workflow_id,
        event_type=EventType.APPROVAL_GRANTED,
        payload={"approval_id": approval_id, "decided_by": decided_by},
        source="api",
        severity=EventSeverity.INFO,
    )
    
    return {"status": "approved", "approval_id": approval_id}


@app.post("/approvals/{approval_id}/reject", tags=["Approvals"])
async def reject_action(
    approval_id: str,
    decided_by: str,
    reason: str,
    session=Depends(get_session)
) -> Dict[str, str]:
    """Reject an action"""
    from database.models import ApprovalAction
    
    approval = session.query(ApprovalAction).filter(ApprovalAction.id == approval_id).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    approval.decision = ApprovalStatus.REJECTED
    approval.decided_by = decided_by
    approval.decision_reason = reason
    approval.decision_at = datetime.utcnow()
    
    session.commit()
    
    # Emit event
    event_manager = get_event_manager()
    await event_manager.emit(
        workflow_id=approval.workflow_id,
        event_type=EventType.APPROVAL_REJECTED,
        payload={"approval_id": approval_id, "decided_by": decided_by, "reason": reason},
        source="api",
        severity=EventSeverity.WARNING,
    )
    
    return {"status": "rejected", "approval_id": approval_id}


# ==================== Audit APIs ====================

@app.get("/audit", tags=["Audit"])
async def get_audit_log(
    user_id: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Get audit log with optional filters"""
    query = session.query(AuditEvent)
    
    if user_id:
        query = query.filter(AuditEvent.user_id == user_id)
    if workflow_id:
        query = query.filter(AuditEvent.workflow_id == workflow_id)
    if action_type:
        query = query.filter(AuditEvent.action_type == action_type)
    
    total = query.count()
    events = query.order_by(AuditEvent.timestamp.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "action_type": e.action_type,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "result": e.result,
                "timestamp": e.timestamp.isoformat(),
                "details": e.action_details,
            }
            for e in events
        ]
    }


# ==================== Event Stream APIs ====================

@app.get("/events/{workflow_id}", tags=["Events"])
async def get_workflow_events(
    workflow_id: str,
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Get all events for a workflow"""
    events = session.query(EventSnapshot).filter(
        EventSnapshot.workflow_id == workflow_id
    ).order_by(EventSnapshot.timestamp.asc()).all()
    
    return {
        "workflow_id": workflow_id,
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "payload": e.payload,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
    }


@app.get("/events/stream/{workflow_id}", tags=["Events"])
async def stream_workflow_events(workflow_id: str):
    """Stream events as Server-Sent Events (SSE)"""
    async def event_generator():
        event_manager = get_event_manager()
        subscriber = EventQueueSubscriber(workflow_id=workflow_id)
        event_manager.subscribe(subscriber)

        try:
            while True:
                event = await subscriber.queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            event_manager.unsubscribe(subscriber)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


# ==================== Device APIs ====================

class VoiceWorkflowRequest(CreateWorkflowRequest):
    voice_input: Optional[bool] = False


@app.post("/workflows", tags=["Workflows"])
async def create_workflow(
    request: VoiceWorkflowRequest,
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Create and execute a workflow"""
    from database.connection import create_workflow

    await _refresh_android_devices()

    conversation_manager = get_conversation_manager()
    conversation_result = conversation_manager.process_input(
        user_id=request.user_id,
        text=request.command,
        session_id=request.session_id,
    )

    if not conversation_result.should_execute:
        return {
            "workflow_id": None,
            "success": True,
            "status": "completed",
            "message": conversation_result.assistant_text,
            "assistant_text": conversation_result.assistant_text,
            "conversation_mode": True,
            "session": conversation_result.session.to_dict(),
            "device_selection": None,
        }

    selection = _resolve_device_selection(
        conversation_result.command_text,
        preferred_device_id=request.device_id,
        session_device_id=conversation_result.session.current_device_id,
    )

    if not selection.available:
        assistant_text = conversation_manager.build_error_reply(error="", selection_available=False)
        conversation_manager.finalize_session(
            session=conversation_result.session,
            command=conversation_result.command_text,
            intent="unknown",
            target=None,
            device_id=None,
            device_type="android",
            device_label="phone",
            assistant_text=assistant_text,
        )
        return {
            "workflow_id": None,
            "success": False,
            "status": "failed",
            "message": assistant_text,
            "assistant_text": assistant_text,
            "conversation_mode": True,
            "session": conversation_result.session.to_dict(),
            "device_selection": selection.to_dict(),
        }

    workflow_id = await create_workflow(
        user_id=request.user_id,
        command=conversation_result.command_text,
        intent="pending",
        device_id=selection.device_id or request.device_id or "laptop",
    )

    result = await _execute_user_command(
        session=session,
        command=conversation_result.command_text,
        user_id=request.user_id,
        device_id=selection.device_id,
        voice_input=request.voice_input,
        workflow_id=workflow_id,
    )

    workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
    if workflow is not None:
        execution_id = await _record_execution(
            session=session,
            workflow=workflow,
            execution_result=result,
        )
    else:
        execution_id = None

    response = {"workflow_id": workflow_id, **result}
    if execution_id is not None:
        response["execution_id"] = execution_id
    response["device_selection"] = selection.to_dict()
    response["assistant_text"] = conversation_manager.build_completion_reply(
        command=conversation_result.command_text,
        device_label=selection.display_name,
        selection_available=selection.available,
        result=result,
        continuation=conversation_result.continuation,
    )
    response["session"] = conversation_manager.finalize_session(
        session=conversation_result.session,
        command=conversation_result.command_text,
        intent="unknown",
        target=None,
        device_id=selection.device_id,
        device_type=selection.device_type,
        device_label=selection.display_name,
        assistant_text=response["assistant_text"],
    ).to_dict()
    return response


@app.post("/command", tags=["Commands"])
async def execute_command(
    request: CommandRequest,
    session=Depends(get_session),
) -> Dict[str, Any]:
    """Parse a command, build a workflow, execute it, and return the result."""
    await bootstrap_phase1_environment()

    conversation_manager = get_conversation_manager()
    conversation_result = conversation_manager.process_input(
        user_id=request.user_id or DEFAULT_USER_ID,
        text=request.command,
        session_id=request.session_id,
    )

    if not conversation_result.should_execute:
        return {
            "success": True,
            "status": "completed",
            "message": conversation_result.assistant_text,
            "assistant_text": conversation_result.assistant_text,
            "conversation_mode": True,
            "session": conversation_result.session.to_dict(),
            "device_selection": None,
        }

    intent_agent = get_intent_agent()
    planner_agent = get_planner_agent()

    intent_result = await intent_agent.detect_intent(conversation_result.command_text)
    plan_steps = planner_agent.plan(intent_result)
    target = _extract_target(intent_result)
    resolved_user_id = request.user_id or DEFAULT_USER_ID
    selection = _resolve_device_selection(
        conversation_result.command_text,
        preferred_device_id=request.device_id,
        session_device_id=conversation_result.session.current_device_id,
    )

    if not selection.available:
        assistant_text = conversation_manager.build_error_reply(error="", selection_available=False)
        conversation_manager.finalize_session(
            session=conversation_result.session,
            command=conversation_result.command_text,
            intent=intent_result.intent.value,
            target=target,
            device_id=None,
            device_type="android",
            device_label="phone",
            assistant_text=assistant_text,
        )
        return {
            "success": False,
            "status": "failed",
            "message": assistant_text,
            "assistant_text": assistant_text,
            "conversation_mode": True,
            "session": conversation_result.session.to_dict(),
            "device_selection": selection.to_dict(),
        }

    workflow = await _create_workflow_record(
        session=session,
        user_id=resolved_user_id,
        command=conversation_result.command_text,
        intent=intent_result.intent.value,
        device_id=selection.device_id or request.device_id or "laptop",
        plan_json=plan_steps,
    )

    result = await _execute_user_command(
        session=session,
        command=conversation_result.command_text,
        user_id=resolved_user_id,
        device_id=selection.device_id,
        workflow_id=workflow.id,
    )

    execution_id = await _record_execution(
        session=session,
        workflow=workflow,
        execution_result=result,
    )

    response = _build_simple_response(result, conversation_result.command_text)
    response.update({
        "workflow_id": workflow.id,
        "intent": intent_result.intent.value,
        "target": target,
        "execution_id": execution_id,
        "result": result,
        "device_selection": selection.to_dict(),
        "assistant_text": conversation_manager.build_completion_reply(
            command=conversation_result.command_text,
            device_label=selection.display_name,
            selection_available=selection.available,
            result=result,
            continuation=conversation_result.continuation,
        ),
    })
    response["session"] = conversation_manager.finalize_session(
        session=conversation_result.session,
        command=conversation_result.command_text,
        intent=intent_result.intent.value,
        target=target,
        device_id=selection.device_id,
        device_type=selection.device_type,
        device_label=selection.display_name,
        assistant_text=response["assistant_text"],
    ).to_dict()
    return response


@app.post("/execute", tags=["Commands"])
async def execute_workflow_command(
    request: ExecuteRequest,
    session=Depends(get_session),
) -> Dict[str, Any]:
    workflow = session.query(Workflow).filter(Workflow.id == request.workflow_id).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    result = await _execute_user_command(
        session=session,
        command=workflow.command,
        user_id=workflow.user_id,
        device_id=workflow.device_id,
        voice_input=False,
        workflow_id=workflow.id,
    )

    execution_id = await _record_execution(
        session=session,
        workflow=workflow,
        execution_result=result,
    )

    return {
        "success": bool(result.get("success")),
        "execution_id": execution_id,
        "status": "completed" if result.get("success") else "failed",
    }


@app.post("/voice", tags=["Commands"])
async def execute_voice_command(
    audio_file: UploadFile = File(...),
    device_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    session=Depends(get_session),
) -> Dict[str, Any]:
    """Transcribe audio, create a workflow, and execute the resulting command."""
    temp_path = None

    try:
        await bootstrap_phase1_environment()

        suffix = os.path.splitext(audio_file.filename or "audio.wav")[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            temp_file.write(await audio_file.read())

        transcript = await get_voice_service().transcribe_audio(temp_path)
        if not transcript:
            raise HTTPException(status_code=400, detail="Unable to transcribe audio")

        conversation_manager = get_conversation_manager()
        conversation_result = conversation_manager.process_input(
            user_id=user_id or DEFAULT_USER_ID,
            text=transcript,
            session_id=session_id,
        )

        if not conversation_result.should_execute:
            return {
                "success": True,
                "status": "completed",
                "message": conversation_result.assistant_text,
                "assistant_text": conversation_result.assistant_text,
                "transcript": transcript,
                "conversation_mode": True,
                "session": conversation_result.session.to_dict(),
                "device_selection": None,
            }

        intent_agent = get_intent_agent()
        planner_agent = get_planner_agent()
        intent_result = await intent_agent.detect_intent(conversation_result.command_text)
        plan_steps = planner_agent.plan(intent_result)
        target = _extract_target(intent_result)
        resolved_user_id = user_id or DEFAULT_USER_ID
        selection = _resolve_device_selection(
            conversation_result.command_text,
            preferred_device_id=device_id,
            session_device_id=conversation_result.session.current_device_id,
        )

        if not selection.available:
            assistant_text = conversation_manager.build_error_reply(error="", selection_available=False)
            conversation_manager.finalize_session(
                session=conversation_result.session,
                command=conversation_result.command_text,
                intent=intent_result.intent.value,
                target=target,
                device_id=None,
                device_type="android",
                device_label="phone",
                assistant_text=assistant_text,
            )
            return {
                "success": False,
                "status": "failed",
                "message": assistant_text,
                "assistant_text": assistant_text,
                "transcript": transcript,
                "conversation_mode": True,
                "session": conversation_result.session.to_dict(),
                "device_selection": selection.to_dict(),
            }

        workflow = await _create_workflow_record(
            session=session,
            user_id=resolved_user_id,
            command=conversation_result.command_text,
            intent=intent_result.intent.value,
            device_id=selection.device_id or device_id or "laptop",
            plan_json=plan_steps,
        )

        result = await _execute_user_command(
            session=session,
            command=conversation_result.command_text,
            user_id=resolved_user_id,
            device_id=selection.device_id,
            voice_input=True,
            workflow_id=workflow.id,
        )

        execution_id = await _record_execution(
            session=session,
            workflow=workflow,
            execution_result=result,
        )

        response = _build_simple_response(result, conversation_result.command_text, transcript=transcript)
        response.update({
            "workflow_id": workflow.id,
            "execution_id": execution_id,
            "result": result,
            "device_selection": selection.to_dict(),
            "assistant_text": conversation_manager.build_completion_reply(
                command=conversation_result.command_text,
                device_label=selection.display_name,
                selection_available=selection.available,
                result=result,
                continuation=conversation_result.continuation,
            ),
        })
        response["session"] = conversation_manager.finalize_session(
            session=conversation_result.session,
            command=conversation_result.command_text,
            intent=intent_result.intent.value,
            target=target,
            device_id=selection.device_id,
            device_type=selection.device_type,
            device_label=selection.display_name,
            assistant_text=response["assistant_text"],
        ).to_dict()
        return response

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@app.on_event("startup")
async def _startup_bootstrap_phase1() -> None:
    await bootstrap_phase1_environment()


@app.get("/device/list", tags=["Devices"])
@app.get("/devices", tags=["Devices"])
async def list_devices() -> Dict[str, Any]:
    """List registered devices"""
    await bootstrap_phase1_environment()
    devices = device_manager.list_devices()
    device_infos = [await device.get_info() for device in devices]

    return {
        "total": len(device_infos),
        "devices": [device_info.to_dict() for device_info in device_infos],
    }


@app.get("/devices/{device_id}", tags=["Devices"])
async def get_device_info(device_id: str) -> Dict[str, Any]:
    """Get device information"""
    from device_intelligence.device_detector import get_device_intelligence
    
    device = device_manager.get_device(device_id)
    if device is not None:
        try:
            device_info = await device.get_info()
            return device_info.to_dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    from device_intelligence.device_detector import get_device_intelligence
    device_intel = get_device_intelligence()
    
    if not device_intel:
        raise HTTPException(status_code=503, detail="Device intelligence not initialized")
    
    try:
        device_info = await device_intel.get_device_info(device_id)
        return device_info.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/device/status", tags=["Devices"])
async def get_device_status() -> Dict[str, Any]:
    """Return current Android device status using adb."""
    await bootstrap_phase1_environment()

    for device in device_manager.list_devices():
        if isinstance(device, AndroidDevice):
            return await get_device_agent().get_device_status(device.device_id)

    adb = get_adb_service(
        Config.get_adb_config().adb_path,
        Config.get_adb_config().default_timeout,
    )
    devices = await adb.list_devices()
    device_id = next((device.get("serial") for device in devices if device.get("serial")), None)

    if device_id is None:
        raise HTTPException(status_code=503, detail="No Android device connected")

    return await adb.get_device_status(device_id)


# ==================== Metrics APIs ====================

@app.get("/metrics", tags=["Metrics"])
async def get_metrics(
    metric_type: Optional[str] = Query(None),
    limit: int = Query(100),
    session=Depends(get_session)
) -> Dict[str, Any]:
    """Get system metrics"""
    from database.models import SystemMetrics
    
    query = session.query(SystemMetrics)
    
    if metric_type:
        query = query.filter(SystemMetrics.metric_type == metric_type)
    
    metrics = query.order_by(SystemMetrics.recorded_at.desc()).limit(limit).all()
    
    return {
        "total": len(metrics),
        "metrics": [
            {
                "id": m.id,
                "type": m.metric_type,
                "name": m.metric_name,
                "value": m.value,
                "unit": m.unit,
                "recorded_at": m.recorded_at.isoformat(),
            }
            for m in metrics
        ]
    }


# Health check
@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Include life direction API routes
app.include_router(life_direction_router)


# Background task helper
async def execute_workflow_background(workflow_id: str):
    """Execute workflow in background"""
    from database.connection import get_workflow

    workflow = get_workflow(workflow_id)
    if workflow is None:
        return

    orchestrator = get_workflow_engine()
    try:
        await orchestrator.execute_command(
            user_id=workflow.user_id,
            command=workflow.command,
            device_id=workflow.device_id or "laptop",
            workflow_id=workflow.id,
        )
    except Exception as exc:
        logger.error(f"Background workflow {workflow_id} failed: {exc}")
