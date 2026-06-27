"""
APA-OS V2 API - Complete REST API for Auth, Device, Trust, Permissions, Agents, Automation, Notifications
"""

from fastapi import APIRouter, HTTPException, Query, Depends, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["APA-OS V2"])


# ==================== Request/Response Models ====================

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str
    device_info: Optional[Dict[str, Any]] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class VerifyResetTokenRequest(BaseModel):
    token: str

class USBPairRequest(BaseModel):
    serial: str

class WirelessPairRequest(BaseModel):
    device_ip: str
    port: int
    pair_code: str

class QRScanRequest(BaseModel):
    session_id: str
    device_serial: str
    device_info: Dict[str, Any]

class QRConfirmRequest(BaseModel):
    session_id: str
    trust_code: str

class TrustRequest(BaseModel):
    device_id: str
    trust_level: str = "always_trusted"
    duration_days: int = 365

class PermissionRequest(BaseModel):
    device_id: str
    permissions: List[str]

class AgentStartRequest(BaseModel):
    device_id: str
    agent_types: Optional[List[str]] = None

class AgentCommandRequest(BaseModel):
    agent_type: str
    action: str
    params: Dict[str, Any] = {}
    device_id: str = ""

class AutomationRuleRequest(BaseModel):
    name: str
    description: str = ""
    trigger_type: str
    trigger_config: Dict[str, Any]
    actions: List[Dict[str, Any]]
    conditions: List[Dict[str, Any]] = []
    device_id: Optional[str] = None

class NotificationSendRequest(BaseModel):
    title: str
    body: str
    notification_type: str = "info"
    category: str = None
    device_id: str = None

class ExecuteCommandRequest(BaseModel):
    command: str
    device_id: Optional[str] = None


# ==================== Auth APIs ====================

@router.post("/auth/signup")
async def signup(request: SignupRequest):
    """Create new user account"""
    from services.auth_service import get_auth_service
    result = get_auth_service().signup(
        name=request.name,
        email=request.email,
        password=request.password,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "user_id": result.user_id,
        "token": result.token,
        "refresh_token": result.refresh_token,
        "session_id": result.session_id,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
    }


@router.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate user"""
    from services.auth_service import get_auth_service
    result = get_auth_service().login(
        email=request.email,
        password=request.password,
        device_info=request.device_info,
    )
    if not result.success:
        raise HTTPException(status_code=401, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "user_id": result.user_id,
        "token": result.token,
        "refresh_token": result.refresh_token,
        "session_id": result.session_id,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
    }


@router.post("/auth/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh access token"""
    from services.auth_service import get_auth_service
    result = get_auth_service().refresh_tokens(request.refresh_token)
    if not result.success:
        raise HTTPException(status_code=401, detail=result.message)
    return {
        "success": True,
        "token": result.token,
        "refresh_token": result.refresh_token,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
    }


@router.post("/auth/logout")
async def logout(session_id: str):
    """Logout and revoke session"""
    from services.auth_service import get_auth_service
    result = get_auth_service().logout(session_id)
    return {"success": result.success, "message": result.message}


@router.post("/auth/verify-email")
async def verify_email(token: str):
    """Verify email address"""
    from services.auth_service import get_auth_service
    result = get_auth_service().verify_email(token)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "message": result.message}


@router.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Request password reset"""
    from services.auth_service import get_auth_service
    result = get_auth_service().forgot_password(request.email)
    return {"success": True, "message": result.message, "token": result.token}


@router.get("/auth/reset-password/verify")
async def verify_reset_token(token: str = Query(...)):
    """Verify a password reset token"""
    from services.auth_service import get_auth_service
    result = get_auth_service().verify_reset_token(token)
    return {"success": result.success, "message": result.message}


@router.post("/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password with token"""
    from services.auth_service import get_auth_service
    result = get_auth_service().reset_password(request.token, request.new_password)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "message": result.message}


@router.get("/auth/me")
async def get_current_user(token: str = Query(...)):
    """Get current user info from token"""
    from services.auth_service import get_auth_service
    user_info = get_auth_service().validate_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"success": True, "user": user_info}


# ==================== Device Pairing APIs ====================

@router.get("/devices/usb/discover")
async def discover_usb_devices():
    """Discover USB-connected devices"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    devices = await engine.discover_usb_devices()
    return {"success": True, "devices": devices, "count": len(devices)}


@router.post("/devices/usb/pair")
async def pair_usb(request: USBPairRequest):
    """Pair device via USB"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    result = await engine.pair_usb(user_id="current_user", serial=request.serial)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "device_id": result.device_id,
        "device_info": result.device_info.to_dict() if result.device_info else None,
    }


@router.post("/devices/wireless/pair")
async def pair_wireless(request: WirelessPairRequest):
    """Pair device via Wireless ADB"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    result = await engine.pair_wireless(
        user_id="current_user",
        device_ip=request.device_ip,
        port=request.port,
        pair_code=request.pair_code,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "device_id": result.device_id,
        "device_info": result.device_info.to_dict() if result.device_info else None,
    }


@router.post("/devices/qr/create")
async def create_qr_session():
    """Create QR pairing session"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    result = engine.create_qr_session(user_id="current_user")
    return {
        "success": True,
        "session_id": result.session_id,
        "pair_code": result.pair_code,
        "qr_data": result.device_info.metadata if result.device_info else {},
    }


@router.post("/devices/qr/scan")
async def qr_scan(request: QRScanRequest):
    """Handle QR scan from mobile"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    result = await engine.handle_qr_scan(
        session_id=request.session_id,
        device_serial=request.device_serial,
        device_info_dict=request.device_info,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "trust_code": result.trust_code,
        "device_info": result.device_info.to_dict() if result.device_info else None,
    }


@router.post("/devices/qr/confirm")
async def qr_confirm(request: QRConfirmRequest):
    """Confirm QR pairing with trust code"""
    from services.device_pairing import get_pairing_engine
    engine = get_pairing_engine()
    result = await engine.confirm_qr_pair(
        session_id=request.session_id,
        trust_code=request.trust_code,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "device_id": result.device_id,
    }


# ==================== Device APIs ====================

@router.get("/devices")
async def list_devices():
    """List all registered devices"""
    db = _get_db()
    try:
        from database.auth_models import RegisteredDevice
        devices = db.query(RegisteredDevice).all()
        return {
            "success": True,
            "devices": [
                {
                    "id": d.id,
                    "name": d.device_name,
                    "type": d.device_type,
                    "model": d.model,
                    "manufacturer": d.manufacturer,
                    "android_version": d.android_version,
                    "serial": d.serial,
                    "battery_level": d.battery_level,
                    "is_online": d.is_online,
                    "connection_type": d.connection_type,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "agent_installed": d.agent_installed,
                }
                for d in devices
            ],
        }
    finally:
        db.close()


@router.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get device details"""
    db = _get_db()
    try:
        from database.auth_models import RegisteredDevice
        device = db.query(RegisteredDevice).filter(RegisteredDevice.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return {
            "success": True,
            "device": {
                "id": device.id,
                "name": device.device_name,
                "type": device.device_type,
                "model": device.model,
                "manufacturer": device.manufacturer,
                "android_version": device.android_version,
                "serial": device.serial,
                "battery_level": device.battery_level,
                "screen_width": device.screen_width,
                "screen_height": device.screen_height,
                "is_online": device.is_online,
                "connection_type": device.connection_type,
                "connection_ip": device.connection_ip,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "agent_installed": device.agent_installed,
                "agent_version": device.agent_version,
            },
        }
    finally:
        db.close()


# ==================== Trust APIs ====================

@router.post("/trust/verify")
async def verify_trust(device_id: str, user_id: str = "current_user"):
    """Verify device trust"""
    from services.trust_engine import get_trust_engine
    engine = get_trust_engine()
    result = engine.verify_trust(device_id, user_id)
    return {
        "success": result.success,
        "message": result.message,
        "trust_level": result.trust_level,
    }


@router.post("/trust/grant")
async def grant_trust(request: TrustRequest):
    """Trust a device"""
    from services.trust_engine import get_trust_engine
    engine = get_trust_engine()
    result = engine.trust_device(
        device_id=request.device_id,
        user_id="current_user",
        trust_level=request.trust_level,
        duration_days=request.duration_days,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message,
        "trust_level": result.trust_level,
        "trust_token": result.trust_token,
        "certificate": result.certificate,
    }


@router.post("/trust/revoke")
async def revoke_trust(device_id: str):
    """Revoke device trust"""
    from services.trust_engine import get_trust_engine
    engine = get_trust_engine()
    result = engine.revoke_trust(device_id, "current_user")
    return {"success": result.success, "message": result.message}


@router.get("/trust/devices")
async def get_trusted_devices():
    """Get all trusted devices"""
    from services.trust_engine import get_trust_engine
    engine = get_trust_engine()
    devices = engine.get_trusted_devices("current_user")
    return {"success": True, "devices": devices}


# ==================== Permission APIs ====================

@router.get("/permissions")
async def check_permissions(device_id: str):
    """Check device permissions"""
    from services.permission_engine import get_permission_engine
    engine = get_permission_engine()
    result = engine.check_permissions(device_id)
    return {
        "success": result.success,
        "all_granted": result.all_granted,
        "required_granted": result.required_granted,
        "missing_required": result.missing_required,
        "missing_optional": result.missing_optional,
        "permissions": [
            {"name": p.name, "status": p.status, "required": p.required, "description": p.description}
            for p in result.permissions
        ],
    }


@router.post("/permissions/request")
async def request_permissions(request: PermissionRequest):
    """Request permissions for device"""
    from services.permission_engine import get_permission_engine
    engine = get_permission_engine()
    result = engine.request_permissions(
        device_id=request.device_id,
        user_id="current_user",
        permissions=request.permissions,
    )
    return {"success": result.success, "message": result.message}


@router.get("/permissions/summary")
async def permission_summary(device_id: str):
    """Get permission summary"""
    from services.permission_engine import get_permission_engine
    engine = get_permission_engine()
    return engine.get_permission_summary(device_id)


# ==================== AI Readiness APIs ====================

@router.get("/readiness/{device_id}")
async def check_readiness(device_id: str):
    """Run AI readiness check on device"""
    from services.ai_readiness import get_readiness_engine
    engine = get_readiness_engine()
    result = await engine.check_readiness(device_id)
    return {
        "success": True,
        "ready": result.ready,
        "score": result.score,
        "message": result.message,
        "ready_count": result.ready_count,
        "total_count": result.total_count,
        "missing": result.missing_capabilities,
        "capabilities": [
            {"name": c.name, "status": c.status, "score": c.score, "message": c.message}
            for c in result.capabilities
        ],
    }


# ==================== Agent Runtime APIs ====================

@router.post("/agents/start")
async def start_agents(request: AgentStartRequest):
    """Start agents on device"""
    from services.agent_runtime import get_agent_runtime
    runtime = get_agent_runtime()
    started = await runtime.start_agents_for_device(
        device_id=request.device_id,
        user_id="current_user",
        agent_types=request.agent_types,
    )
    return {"success": True, "started_agents": started}


@router.post("/agents/stop")
async def stop_agents(device_id: str):
    """Stop all agents on device"""
    from services.agent_runtime import get_agent_runtime
    runtime = get_agent_runtime()
    await runtime.stop_agents_for_device(device_id)
    return {"success": True, "message": "Agents stopped"}


@router.post("/agents/execute")
async def execute_agent_command(request: AgentCommandRequest):
    """Execute command on agent"""
    from services.agent_runtime import get_agent_runtime, AgentCommand
    runtime = get_agent_runtime()
    command = AgentCommand(
        agent_type=request.agent_type,
        action=request.action,
        params=request.params,
        device_id=request.device_id,
        user_id="current_user",
    )
    result = await runtime.execute_on_agent(command)
    return {
        "success": result.success,
        "agent_type": result.agent_type,
        "result": result.result,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


@router.get("/agents/status")
async def get_agents_status():
    """Get all agents status"""
    from services.agent_runtime import get_agent_runtime
    runtime = get_agent_runtime()
    statuses = runtime.get_all_status()
    return {
        "success": True,
        "agents": [
            {
                "type": s.agent_type,
                "name": s.agent_name,
                "status": s.status,
                "device_id": s.device_id,
            }
            for s in statuses
        ],
    }


@router.get("/agents/device/{device_id}")
async def get_device_agents(device_id: str):
    """Get agents on specific device"""
    from services.agent_runtime import get_agent_runtime
    runtime = get_agent_runtime()
    statuses = runtime.get_device_agents(device_id)
    return {
        "success": True,
        "device_id": device_id,
        "agents": [
            {"type": s.agent_type, "name": s.agent_name, "status": s.status}
            for s in statuses
        ],
    }


# ==================== Automation APIs ====================

@router.post("/automation/rules")
async def create_automation_rule(request: AutomationRuleRequest):
    """Create automation rule"""
    from services.automation_engine import get_automation_engine
    engine = get_automation_engine()
    result = engine.create_rule(
        user_id="current_user",
        name=request.name,
        description=request.description,
        trigger_type=request.trigger_type,
        trigger_config=request.trigger_config,
        actions=request.actions,
        conditions=request.conditions,
        device_id=request.device_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/automation/rules")
async def list_automation_rules():
    """List all automation rules"""
    from services.automation_engine import get_automation_engine
    engine = get_automation_engine()
    rules = engine.get_rules("current_user")
    return {"success": True, "rules": rules, "count": len(rules)}


@router.put("/automation/rules/{rule_id}")
async def update_automation_rule(rule_id: str, updates: Dict[str, Any]):
    """Update automation rule"""
    from services.automation_engine import get_automation_engine
    engine = get_automation_engine()
    result = engine.update_rule(rule_id, "current_user", updates)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/automation/rules/{rule_id}")
async def delete_automation_rule(rule_id: str):
    """Delete automation rule"""
    from services.automation_engine import get_automation_engine
    engine = get_automation_engine()
    result = engine.delete_rule(rule_id, "current_user")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/automation/execute/{rule_id}")
async def execute_automation_rule(rule_id: str, device_id: Optional[str] = None):
    """Execute an automation rule"""
    from services.automation_engine import get_automation_engine
    engine = get_automation_engine()
    result = await engine.execute_rule(rule_id, "current_user", device_id)
    return result


# ==================== Notification APIs ====================

@router.get("/notifications")
async def list_notifications(
    limit: int = Query(50, le=100),
    unread_only: bool = Query(False),
    category: Optional[str] = None,
):
    """Get notifications"""
    from services.notification_service import get_notification_service
    service = get_notification_service()
    notifs = service.get_notifications("current_user", limit, unread_only, category)
    unread_count = service.get_unread_count("current_user")
    return {
        "success": True,
        "notifications": notifs,
        "unread_count": unread_count,
        "total": len(notifs),
    }


@router.post("/notifications/send")
async def send_notification(request: NotificationSendRequest):
    """Send notification"""
    from services.notification_service import get_notification_service
    service = get_notification_service()
    notif_id = service.create_notification(
        user_id="current_user",
        title=request.title,
        body=request.body,
        notification_type=request.notification_type,
        category=request.category,
        device_id=request.device_id,
    )
    return {"success": True, "notification_id": notif_id}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark notification as read"""
    from services.notification_service import get_notification_service
    service = get_notification_service()
    success = service.mark_read(notification_id, "current_user")
    return {"success": success}


@router.put("/notifications/read-all")
async def mark_all_notifications_read():
    """Mark all notifications as read"""
    from services.notification_service import get_notification_service
    service = get_notification_service()
    count = service.mark_all_read("current_user")
    return {"success": True, "marked_count": count}


# ==================== Dashboard APIs ====================

@router.get("/dashboard")
async def get_dashboard():
    """Get complete dashboard data"""
    db = _get_db()
    try:
        from database.auth_models import (
            RegisteredDevice, TrustedDevice, DeviceAgent,
            AutomationRule, NotificationRecord
        )

        devices = db.query(RegisteredDevice).count()
        trusted = db.query(TrustedDevice).filter(TrustedDevice.revoked_at == None).count()
        agents = db.query(DeviceAgent).filter(DeviceAgent.status == "running").count()
        automations = db.query(AutomationRule).filter(AutomationRule.is_active == True).count()
        unread_notifs = db.query(NotificationRecord).filter(
            NotificationRecord.user_id == "current_user",
            NotificationRecord.is_read == False,
        ).count()

        return {
            "success": True,
            "dashboard": {
                "devices": {"total": devices},
                "trusted_devices": {"total": trusted},
                "active_agents": {"total": agents},
                "active_automations": {"total": automations},
                "notifications": {"unread": unread_notifs},
            },
        }
    finally:
        db.close()


@router.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "auth": True,
            "devices": True,
            "trust": True,
            "permissions": True,
            "agents": True,
            "automation": True,
            "notifications": True,
        },
    }


# ==================== Helper ====================

def _get_db():
    from database.connection import get_db_session
    return get_db_session()
