"""
APA-OS V1 API - Clean, production-grade endpoints
Following the Master Product Specification
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/v1", tags=["APA-OS V1"])


# ==================== Request/Response Models ====================

class CommandRequest(BaseModel):
    """Unified command request."""
    command: str
    device_id: Optional[str] = None
    user_id: Optional[str] = "default"
    session_id: Optional[str] = None
    voice_input: bool = False


class CommandResponse(BaseModel):
    """Unified command response."""
    success: bool
    workflow_id: str
    intent: str
    target: Optional[str] = None
    message: str
    package_name: Optional[str] = None
    foreground_app: Optional[str] = None
    verification_passed: bool = False
    duration_ms: float = 0
    steps: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class DeviceStatusResponse(BaseModel):
    """Device status response."""
    connected: bool
    device_id: Optional[str] = None
    model_name: Optional[str] = None
    manufacturer: Optional[str] = None
    android_version: Optional[str] = None
    battery_level: Optional[int] = None
    foreground_app: Optional[str] = None
    screen_state: Optional[str] = None


class AppInfo(BaseModel):
    """App information."""
    package_name: str
    app_label: str
    is_system_app: bool = False


class AppsResponse(BaseModel):
    """Apps list response."""
    total: int
    apps: List[AppInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    components: Dict[str, Any]


# ==================== Helper Functions ====================

def _get_workflow_engine():
    from services.unified_workflow import get_unified_workflow
    return get_unified_workflow()


def _get_adb_service():
    from services.adb_service import get_adb_service, find_adb_binary
    return get_adb_service(find_adb_binary())


# ==================== Device Control (Phase 1) ====================

@router.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest) -> CommandResponse:
    """
    Execute any command through the unified workflow.
    
    Examples:
    - "Open Spotify"
    - "Open Telegram"
    - "Send hello to Guru"
    - "What's my battery level?"
    - "Take a screenshot"
    - "Search for AI Agents on YouTube"
    """
    engine = _get_workflow_engine()
    
    result = await engine.execute_command(
        command=request.command,
        user_id=request.user_id,
        device_id=request.device_id,
        session_id=request.session_id,
        voice_input=request.voice_input,
    )
    
    steps_dict = [
        {
            "step": s.step_number,
            "type": s.step_type,
            "description": s.description,
            "status": s.status,
            "result": s.result,
            "duration_ms": s.duration_ms,
        }
        for s in result.steps
    ]
    
    return CommandResponse(
        success=result.success,
        workflow_id=result.workflow_id,
        intent=result.intent,
        target=result.target,
        message=result.message,
        package_name=result.package_name,
        foreground_app=result.foreground_app,
        verification_passed=result.verification_passed,
        duration_ms=result.duration_ms,
        steps=steps_dict,
        metadata=result.metadata,
    )


@router.post("/open")
async def open_app(app_name: str) -> CommandResponse:
    """
    Quick endpoint to open any installed app.
    
    Examples:
    - /v1/open?app_name=spotify
    - /v1/open?app_name=telegram
    - /v1/open?app_name=calculator
    """
    engine = _get_workflow_engine()
    
    result = await engine.execute_command(
        command=f"Open {app_name}",
    )
    
    steps_dict = [
        {
            "step": s.step_number,
            "type": s.step_type,
            "description": s.description,
            "status": s.status,
            "result": s.result,
        }
        for s in result.steps
    ]
    
    return CommandResponse(
        success=result.success,
        workflow_id=result.workflow_id,
        intent=result.intent,
        target=result.target,
        message=result.message,
        package_name=result.package_name,
        foreground_app=result.foreground_app,
        verification_passed=result.verification_passed,
        duration_ms=result.duration_ms,
        steps=steps_dict,
    )


# ==================== App Discovery ====================

@router.get("/device/apps", response_model=AppsResponse)
async def get_installed_apps(device_id: Optional[str] = None) -> AppsResponse:
    """
    Get all installed apps on the connected device.
    
    Returns:
    [
        {"package_name": "com.spotify.music", "app_label": "Spotify"},
        {"package_name": "org.telegram.messenger", "app_label": "Telegram"},
        ...
    ]
    """
    engine = _get_workflow_engine()
    
    if not device_id:
        device_id = await engine.get_connected_device_id()
    
    if not device_id:
        raise HTTPException(status_code=404, detail="No Android device connected")
    
    apps = await engine.get_all_installed_apps(device_id)
    
    return AppsResponse(
        total=len(apps),
        apps=[
            AppInfo(
                package_name=app.get("package_name", ""),
                app_label=app.get("app_label", ""),
                is_system_app=app.get("is_system_app", False),
            )
            for app in apps
        ],
    )


@router.get("/device/apps/search")
async def search_apps(q: str = Query("", description="Search query")) -> Dict[str, Any]:
    """
    Search installed apps by name.
    
    Examples:
    - /v1/device/apps/search?q=spotify
    - /v1/device/apps/search?q=telegram
    """
    engine = _get_workflow_engine()
    device_id = await engine.get_connected_device_id()
    
    if not device_id:
        raise HTTPException(status_code=404, detail="No Android device connected")
    
    results = await engine.search_installed_apps(device_id, q)
    
    return {
        "query": q,
        "total": len(results),
        "results": results,
    }


@router.post("/device/apps/refresh")
async def refresh_apps() -> Dict[str, Any]:
    """Force refresh the app registry."""
    engine = _get_workflow_engine()
    device_id = await engine.get_connected_device_id()
    
    if not device_id:
        raise HTTPException(status_code=404, detail="No Android device connected")
    
    from services.app_resolver import get_app_resolver
    resolver = get_app_resolver()
    await resolver.refresh(device_id)
    
    return {
        "status": "completed",
        "apps_count": len(resolver.package_map),
    }


# ==================== Device Status ====================

@router.get("/device/status", response_model=DeviceStatusResponse)
async def get_device_status() -> DeviceStatusResponse:
    """Get current device status."""
    adb = _get_adb_service()
    devices = await adb.list_devices()
    
    if not devices:
        return DeviceStatusResponse(connected=False)
    
    device_id = devices[0]["serial"]
    
    return DeviceStatusResponse(
        connected=True,
        device_id=device_id,
        model_name=await adb.get_model_name(device_id),
        manufacturer=await adb.get_manufacturer(device_id),
        android_version=await adb.get_android_version(device_id),
        battery_level=await adb.get_battery_level(device_id),
        foreground_app=await adb.get_foreground_app(device_id),
        screen_state=await adb.get_screen_state(device_id),
    )


@router.get("/device/battery")
async def get_battery() -> Dict[str, Any]:
    """Get battery level."""
    adb = _get_adb_service()
    devices = await adb.list_devices()
    
    if not devices:
        return {"battery_level": None, "error": "No device connected"}
    
    device_id = devices[0]["serial"]
    battery = await adb.get_battery_level(device_id)
    
    return {"battery_level": battery, "device_id": device_id}


@router.get("/device/foreground")
async def get_foreground_app() -> Dict[str, Any]:
    """Get current foreground app."""
    adb = _get_adb_service()
    devices = await adb.list_devices()
    
    if not devices:
        return {"foreground_app": None, "error": "No device connected"}
    
    device_id = devices[0]["serial"]
    fg = await adb.get_foreground_app(device_id)
    
    return {"foreground_app": fg, "device_id": device_id}


# ==================== Health Check ====================

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """System health check."""
    import datetime
    health = {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "components": {},
    }
    
    # Check ADB
    try:
        adb = _get_adb_service()
        devices = await adb.list_devices()
        health["components"]["adb"] = {
            "available": True,
            "connected_devices": len(devices),
            "devices": [d["serial"] for d in devices],
        }
    except Exception as e:
        health["components"]["adb"] = {"available": False, "error": str(e)}
        health["status"] = "degraded"
    
    # Check OCR
    try:
        from vision.ocr_service import get_ocr_service
        ocr = get_ocr_service()
        health["components"]["ocr"] = ocr.get_engine_status()
    except Exception as e:
        health["components"]["ocr"] = {"error": str(e), "available": False}
    
    return HealthResponse(**health)
