"""
APA-OS Device API - Pairing, registration, trust, permissions, AI readiness
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from services.pairing_service import get_pairing_service
from services.device_registration_service import get_registration_service
from services.auth_service import get_auth_service

router = APIRouter(prefix="/api/device", tags=["Device"])

# ==================== Request Models ====================

class RegisterDeviceRequest(BaseModel):
    manufacturer: str = Field(..., description="Device manufacturer")
    model: str = Field(..., description="Device model")
    android_version: Optional[str] = None
    battery: Optional[int] = None
    storage: Optional[str] = None
    ram: Optional[str] = None
    device_name: Optional[str] = None
    device_uuid: Optional[str] = None
    network: Optional[str] = None
    capabilities: Optional[List[str]] = None
    installed_apps_count: Optional[int] = None

class PermissionRequest(BaseModel):
    permission: str = Field(..., description="Permission name (e.g. 'screen_capture')")
    status: str = Field(..., description="Permission status ('granted' or 'denied')")

# ==================== Dependency ====================

def get_current_user(token: str = Query(...)) -> str:
    """Extract user_id from token using auth service"""
    service = get_auth_service()
    user_info = service.validate_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_info["user_id"]

# ==================== Endpoints ====================

@router.get("/pairing/status")
async def get_pairing_status(user_id: str = Depends(get_current_user)):
    """Check if user has any paired device"""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice, TrustedDevice

    db = get_db_session()
    try:
        paired_devices = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
        ).all()
        trusted_count = db.query(TrustedDevice).filter(
            TrustedDevice.user_id == user_id,
            TrustedDevice.revoked_at == None,
        ).count()

        return {
            "success": True,
            "paired": len(paired_devices) > 0,
            "trusted": trusted_count > 0,
            "device_count": len(paired_devices),
            "devices": [
                {
                    "id": d.id,
                    "name": d.device_name,
                    "model": d.model,
                    "manufacturer": d.manufacturer,
                    "android_version": d.android_version,
                    "battery": d.battery_level,
                    "is_online": d.is_online,
                    "connection_type": d.connection_type,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                }
                for d in paired_devices
            ],
        }
    finally:
        db.close()

@router.post("/register")
async def register_device(request: RegisterDeviceRequest, user_id: str = Depends(get_current_user)):
    """Register device with full specs"""
    service = get_registration_service()
    result = service.register_device(user_id, request.model_dump())
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "device_id": result.device_id,
        "message": result.message,
    }

@router.post("/permission")
async def set_permission(
    request: PermissionRequest,
    device_id: str = Body(...),
    user_id: str = Depends(get_current_user),
):
    """Store device permission status"""
    service = get_registration_service()
    success = service.update_permission(
        user_id=user_id,
        device_id=device_id,
        permission_name=request.permission,
        status=request.status
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update permission")
    return {"success": True, "message": f"Permission {request.permission} updated"}

@router.get("/current")
async def get_current_device(user_id: str = Depends(get_current_user)):
    """Get most recently seen device info for home dashboard"""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
        ).order_by(RegisteredDevice.last_seen.desc()).first()

        if not device:
            return {
                "success": True,
                "device": None,
                "message": "No device registered",
            }

        return {
            "success": True,
            "device": {
                "id": device.id,
                "name": device.device_name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "android_version": device.android_version,
                "battery": device.battery_level,
                "is_online": device.is_online,
                "connection_type": device.connection_type,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            },
        }
    finally:
        db.close()

@router.get("/readiness")
async def check_ai_readiness(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Calculate AI readiness score for device"""
    from services.ai_readiness_service import get_readiness_engine
    engine = get_readiness_engine()
    result = await engine.check_readiness(device_id)
    return {
        "success": True,
        "ready": result.ready,
        "score": result.score,
        "missing_capabilities": result.missing_capabilities,
        "message": result.message,
    }

@router.get("/twin")
async def get_device_twin(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Get digital twin for device"""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user_id,
        ).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        return {
            "success": True,
            "twin": {
                "id": device.id,
                "name": device.device_name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "android_version": device.android_version,
                "battery": device.battery_level,
                "storage": device.metadata_json.get("storage") if device.metadata_json else None,
                "ram": device.metadata_json.get("ram") if device.metadata_json else None,
                "health": "good" if device.is_online else "offline",
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            },
        }
    finally:
        db.close()
