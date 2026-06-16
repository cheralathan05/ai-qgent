"""
Production REST APIs
Complete API surface for APA-OS Backend
"""

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import asyncio

from database.models import (
    Workflow, WorkflowStatus, ApprovalStatus, AuditEvent, EventSnapshot
)
from console.event_stream import EventType, EventSeverity, get_event_manager, EventQueueSubscriber
from audit.audit_manager import get_audit_manager
from devices import device_manager
from services.workflow_engine import get_workflow_engine
from services.voice_service import get_voice_service
from services.adb_service import get_adb_service
from services.redis_service import get_redis_service
from api.life_direction import router as life_direction_router

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
    device_id: Optional[str] = "laptop"


async def get_session():
    """Get database session"""
    from database.connection import get_db_session
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


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

    workflow_id = await create_workflow(
        user_id=request.user_id,
        command=request.command,
        intent="pending",
        device_id=request.device_id,
    )

    orchestrator = get_workflow_engine(session=session)
    result = await orchestrator.execute_command(
        user_id=request.user_id,
        command=request.command,
        device_id=request.device_id,
        workflow_id=workflow_id,
        voice_input=request.voice_input,
    )

    return {"workflow_id": workflow_id, **result}


@app.get("/devices", tags=["Devices"])
async def list_devices() -> Dict[str, Any]:
    """List registered devices"""
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
