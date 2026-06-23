"""
APA-OS Universal API

The single API layer that handles EVERYTHING.
No command lists. No hardcoded workflows.
User types naturally, system responds.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/apa", tags=["APA-OS Universal"])


# ==================== Request/Response Models ====================

class ProcessRequest(BaseModel):
    """Universal process request."""
    command: str
    user_id: str = "default"
    device_id: Optional[str] = None


class ProcessResponse(BaseModel):
    """Universal process response."""
    success: bool
    message: str
    intent: str
    target: Optional[str] = None
    workflow_id: str = ""
    duration_ms: float = 0
    execution_data: Optional[Dict[str, Any]] = None
    knowledge_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class DeviceAppsResponse(BaseModel):
    """Installed apps response."""
    total: int
    apps: List[Dict[str, Any]]


class DeviceStatusResponse(BaseModel):
    """Device status response."""
    connected: bool
    device_id: Optional[str] = None
    model_name: Optional[str] = None
    battery_level: Optional[int] = None
    foreground_app: Optional[str] = None
    screen_state: Optional[str] = None


class MemoryResponse(BaseModel):
    """Memory state response."""
    current_device: str
    current_app: str
    current_screen: str
    recent_commands: int
    recent_searches: List[str]
    recent_documents: List[str]
    recent_apps: List[str]
    total_workflows: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    components: Dict[str, Any]


class EventsResponse(BaseModel):
    """Events response."""
    total: int
    events: List[Dict[str, Any]]
    stats: Dict[str, int]


class LearningResponse(BaseModel):
    """Learning engine response."""
    total_interactions: int
    patterns: Dict[str, int]
    frequent_apps: List[Dict[str, Any]]
    frequent_contacts: List[Dict[str, Any]]
    suggestions: List[Dict[str, Any]]


class ConversationResponse(BaseModel):
    """Conversation response."""
    active_conversation: Optional[str]
    message_count: int
    messages: List[Dict[str, Any]]


class SystemStatusResponse(BaseModel):
    """Full system status response."""
    apa_os: str
    layers: Dict[str, Any]


# ==================== Helper Functions ====================

def _get_apa_os():
    from core.apa_os import get_apa_os
    return get_apa_os()


# ==================== Universal Endpoints ====================

@router.post("/process", response_model=ProcessResponse)
async def process_command(request: ProcessRequest) -> ProcessResponse:
    """
    Process ANY command naturally.
    
    Examples:
    - "Open Spotify"
    - "Send hello to Guru"
    - "What's my battery level?"
    - "Summarize my DBMS notes"
    - "Generate 20 interview questions on Python"
    - "Find my resume"
    - "Explain Normalization"
    - "Open YouTube and search AI Agents"
    - "Take a screenshot"
    - "Call Mom"
    - "Turn on WiFi"
    - "Scroll down"
    - "Go back"
    """
    apa_os = _get_apa_os()
    
    result = await apa_os.process(
        command=request.command,
        user_id=request.user_id,
        device_id=request.device_id,
    )
    
    execution_data = None
    if result.execution_result:
        execution_data = {
            "success": result.execution_result.success,
            "message": result.execution_result.message,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_type": s.step_type,
                    "success": s.success,
                    "message": s.message,
                }
                for s in result.execution_result.steps
            ],
            "verification_passed": result.execution_result.verification_passed,
            "foreground_app": result.execution_result.foreground_app,
        }
    
    knowledge_data = None
    if result.knowledge_result:
        knowledge_data = {
            "success": result.knowledge_result.success,
            "operation": result.knowledge_result.operation,
            "answer": result.knowledge_result.answer,
            "sources": result.knowledge_result.sources,
        }
    
    return ProcessResponse(
        success=result.success,
        message=result.message,
        intent=result.intent,
        target=result.target,
        workflow_id=result.workflow_id,
        duration_ms=result.duration_ms,
        execution_data=execution_data,
        knowledge_data=knowledge_data,
        metadata=result.metadata,
    )


@router.get("/intent")
async def understand_intent(command: str = Query(..., description="Command to understand")) -> Dict[str, Any]:
    """
    Understand intent without executing.
    
    Returns the parsed intent, entities, and which phases are needed.
    """
    apa_os = _get_apa_os()
    
    result = await apa_os.intent_engine.understand(command)
    
    return {
        "intent": result.intent.value,
        "confidence": result.confidence,
        "entities": [
            {"type": e.entity_type, "value": e.value, "confidence": e.confidence}
            for e in result.entities
        ],
        "slots": result.slots,
        "requires_phase1": result.requires_phase1,
        "requires_phase2": result.requires_phase2,
        "requires_phase3": result.requires_phase3,
        "compound_intents": result.compound_intents,
    }


@router.get("/workflow")
async def generate_workflow(command: str = Query(..., description="Command to generate workflow for")) -> Dict[str, Any]:
    """
    Generate workflow without executing.
    
    Returns the planned steps.
    """
    apa_os = _get_apa_os()
    
    intent_result = await apa_os.intent_engine.understand(command)
    workflow = apa_os.workflow_generator.generate(intent_result)
    
    return {
        "workflow_id": workflow.workflow_id,
        "intent": workflow.intent.value,
        "description": workflow.description,
        "requires_phase1": workflow.requires_phase1,
        "requires_phase2": workflow.requires_phase2,
        "requires_phase3": workflow.requires_phase3,
        "steps": [
            {
                "step_id": s.step_id,
                "step_type": s.step_type,
                "description": s.description,
                "phase": s.phase,
                "action": s.action,
                "params": s.params,
            }
            for s in workflow.steps
        ],
    }


# ==================== Device Endpoints ====================

@router.get("/device/apps", response_model=DeviceAppsResponse)
async def get_installed_apps() -> DeviceAppsResponse:
    """Get all installed apps on the connected device."""
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        from services.app_resolver import get_app_resolver
        
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        
        if not devices:
            return DeviceAppsResponse(total=0, apps=[])
        
        device_id = devices[0]["serial"]
        resolver = get_app_resolver()
        await resolver.ensure_registry(device_id)
        apps = resolver.list_apps()
        
        return DeviceAppsResponse(total=len(apps), apps=apps)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/apps/search")
async def search_apps(q: str = Query("", description="Search query")) -> Dict[str, Any]:
    """Search installed apps."""
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        from services.app_resolver import get_app_resolver
        
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        
        if not devices:
            return {"query": q, "total": 0, "results": []}
        
        device_id = devices[0]["serial"]
        resolver = get_app_resolver()
        await resolver.ensure_registry(device_id)
        results = resolver.search(q)
        
        return {"query": q, "total": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device/status", response_model=DeviceStatusResponse)
async def get_device_status() -> DeviceStatusResponse:
    """Get device status."""
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        
        if not devices:
            return DeviceStatusResponse(connected=False)
        
        device_id = devices[0]["serial"]
        
        return DeviceStatusResponse(
            connected=True,
            device_id=device_id,
            model_name=await adb.get_model_name(device_id),
            battery_level=await adb.get_battery_level(device_id),
            foreground_app=await adb.get_foreground_app(device_id),
            screen_state=await adb.get_screen_state(device_id),
        )
    except Exception as e:
        return DeviceStatusResponse(connected=False)


@router.get("/device/battery")
async def get_battery() -> Dict[str, Any]:
    """Get battery level."""
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        
        if not devices:
            return {"battery_level": None, "error": "No device connected"}
        
        device_id = devices[0]["serial"]
        battery = await adb.get_battery_level(device_id)
        
        return {"battery_level": battery, "device_id": device_id}
    except Exception as e:
        return {"battery_level": None, "error": str(e)}


@router.get("/device/foreground")
async def get_foreground_app() -> Dict[str, Any]:
    """Get current foreground app."""
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        
        if not devices:
            return {"foreground_app": None, "error": "No device connected"}
        
        device_id = devices[0]["serial"]
        fg = await adb.get_foreground_app(device_id)
        
        return {"foreground_app": fg, "device_id": device_id}
    except Exception as e:
        return {"foreground_app": None, "error": str(e)}


# ==================== Memory Endpoints ====================

@router.get("/memory", response_model=MemoryResponse)
async def get_memory() -> MemoryResponse:
    """Get current memory state."""
    apa_os = _get_apa_os()
    state = apa_os.memory.get_state()
    
    return MemoryResponse(
        current_device=state.current_device_id or "none",
        current_app=state.current_app or "none",
        current_screen=state.current_screen or "none",
        recent_commands=len(state.recent_commands),
        recent_searches=state.recent_searches[-5:],
        recent_documents=state.recent_documents[-5:],
        recent_apps=state.recent_apps[-5:],
        total_workflows=len(state.workflow_history),
    )


@router.delete("/memory")
async def clear_memory() -> Dict[str, str]:
    """Clear memory."""
    apa_os = _get_apa_os()
    apa_os.memory.clear()
    return {"status": "cleared"}


# ==================== Health Check ====================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """System health check."""
    components = {}
    
    # Check ADB
    try:
        from services.adb_service import get_adb_service, find_adb_binary
        adb = get_adb_service(find_adb_binary())
        devices = await adb.list_devices()
        components["adb"] = {
            "available": True,
            "connected_devices": len(devices),
        }
    except Exception as e:
        components["adb"] = {"available": False, "error": str(e)}
    
    # Check OCR
    try:
        from vision.ocr_service import get_ocr_service
        ocr = get_ocr_service()
        components["ocr"] = ocr.get_engine_status()
    except Exception as e:
        components["ocr"] = {"available": False, "error": str(e)}
    
    # Check Knowledge
    try:
        from knowledge.search_engine import get_search_engine
        components["knowledge"] = {"available": True}
    except Exception as e:
        components["knowledge"] = {"available": False, "error": str(e)}
    
    status = "healthy"
    if not components.get("adb", {}).get("available"):
        status = "degraded"
    
    return HealthResponse(status=status, components=components)


# ==================== Events Endpoints ====================

@router.get("/events", response_model=EventsResponse)
async def get_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, description="Number of events"),
) -> EventsResponse:
    """Get event history."""
    apa_os = _get_apa_os()
    
    from core.event_bus import EventType
    filter_type = None
    if event_type:
        try:
            filter_type = EventType(event_type)
        except ValueError:
            pass
    
    events = apa_os.events.get_history(event_type=filter_type, limit=limit)
    stats = apa_os.events.get_stats()
    
    return EventsResponse(
        total=len(events),
        events=[
            {
                "id": e.id,
                "type": e.event_type.value,
                "source": e.source,
                "timestamp": e.timestamp,
                "success": e.success,
                "duration_ms": e.duration_ms,
                "data": e.data,
            }
            for e in events
        ],
        stats=stats,
    )


@router.delete("/events")
async def clear_events() -> Dict[str, str]:
    """Clear event history."""
    apa_os = _get_apa_os()
    apa_os.events.clear_history()
    return {"status": "cleared"}


# ==================== Learning Endpoints ====================

@router.get("/learning", response_model=LearningResponse)
async def get_learning() -> LearningResponse:
    """Get learning engine data."""
    apa_os = _get_apa_os()
    
    frequent_apps = [
        {"name": p.key, "count": p.count, "last_used": p.last_used}
        for p in apa_os.learning.get_frequent_apps(10)
    ]
    
    frequent_contacts = [
        {"name": p.key, "count": p.count, "last_used": p.last_used}
        for p in apa_os.learning.get_frequent_contacts(10)
    ]
    
    suggestions = await apa_os.learning.suggest_automations()
    
    return LearningResponse(
        total_interactions=len(apa_os.learning._interaction_log),
        patterns={
            k: len(v) for k, v in apa_os.learning.get_all_patterns().items()
        },
        frequent_apps=frequent_apps,
        frequent_contacts=frequent_contacts,
        suggestions=[
            {
                "title": s.title,
                "description": s.description,
                "confidence": s.confidence,
                "reason": s.reason,
                "category": s.category,
            }
            for s in suggestions
        ],
    )


# ==================== Conversation Endpoints ====================

@router.get("/conversation", response_model=ConversationResponse)
async def get_conversation() -> ConversationResponse:
    """Get current conversation."""
    apa_os = _get_apa_os()
    
    conv = apa_os.conversation.get_active_conversation()
    if not conv:
        return ConversationResponse(
            active_conversation=None,
            message_count=0,
            messages=[],
        )
    
    return ConversationResponse(
        active_conversation=conv.id,
        message_count=len(conv.messages),
        messages=[
            {
                "role": m.role,
                "content": m.content[:500],
                "timestamp": m.timestamp,
                "intent": m.intent,
            }
            for m in conv.messages[-20:]
        ],
    )


@router.delete("/conversation")
async def clear_conversation() -> Dict[str, str]:
    """Clear conversation."""
    apa_os = _get_apa_os()
    apa_os.conversation.clear_conversation()
    return {"status": "cleared"}


# ==================== System Status Endpoints ====================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """Get full system status."""
    apa_os = _get_apa_os()
    return SystemStatusResponse(**apa_os.get_status())
