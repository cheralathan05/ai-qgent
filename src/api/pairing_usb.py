"""
APA-OS USB Pairing API
Complete production endpoints for USB device discovery, pairing, verification, trust, and registration
"""

import asyncio
import json
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pairing", tags=["USB Pairing"])


# ==================== Request Models ====================

class ConnectRequest(BaseModel):
    serial: str

class TrustRequest(BaseModel):
    device_id: str
    trust_level: str = "always_trusted"

class PermissionUpdateRequest(BaseModel):
    device_id: str
    permissions: Dict[str, str]

class DisconnectRequest(BaseModel):
    device_id: str


# ==================== Auth Dependency ====================

async def get_current_user(token: str = Query(...)) -> str:
    """Extract user_id from token"""
    from services.auth_service import get_auth_service
    service = get_auth_service()
    user_info = service.validate_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_info["user_id"]


# ==================== Helper Functions ====================

def _emit_event(event_type: str, data: dict):
    """Emit WebSocket event"""
    try:
        from services.websocket_service import get_websocket_manager
        mgr = get_websocket_manager()
        import asyncio
        asyncio.ensure_future(mgr.broadcast({
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        pass

def _create_audit_log(user_id: str, action: str, resource_type: str, resource_id: str, details: dict, result: str = "success", error_message: str = None):
    """Create audit log entry"""
    try:
        from database.connection import get_db_session
        from database.auth_models import SystemAuditLog
        db = get_db_session()
        try:
            audit = SystemAuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                result=result,
                error_message=error_message,
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Audit log failed: {e}")


# ==================== Endpoints ====================

@router.get("/status")
async def get_pairing_status(user_id: str = Depends(get_current_user)):
    """Get current pairing session status, trusted devices, connected USB devices"""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice, TrustedDevice, PairingWorkflow, DeviceTwin

    db = get_db_session()
    try:
        # Check for active pairing workflow
        active_workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.workflow_state.in_(["idle", "discovering", "connecting", "verifying", "trusting", "permissions", "registering", "twin_creating"]),
        ).order_by(PairingWorkflow.started_at.desc()).first()

        # Check trusted devices
        trusted_devices = db.query(TrustedDevice).filter(
            TrustedDevice.user_id == user_id,
            TrustedDevice.revoked_at == None,
        ).all()
        trusted_count = len(trusted_devices)

        # Check registered devices
        devices = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
        ).order_by(RegisteredDevice.last_seen.desc()).all()

        # Check device twins
        twins = {}
        for d in devices:
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == d.id
            ).first()
            if twin:
                twins[d.id] = {
                    "readiness_score": twin.readiness_score,
                    "ai_ready": twin.ai_ready,
                    "health_score": twin.health_score,
                    "trust_score": twin.trust_score,
                    "sync_state": twin.sync_state,
                }

        # Check USB connected devices via ADB
        usb_devices = []
        try:
            from services.adb_service import get_adb_service, find_adb_binary
            adb = get_adb_service(find_adb_binary())
            raw_devices = await adb.list_devices()
            for dev in raw_devices:
                if dev.get("state") == "device":
                    usb_devices.append({
                        "serial": dev.get("serial", ""),
                        "state": dev.get("state", ""),
                    })
        except Exception:
            pass

        return {
            "success": True,
            "user_id": user_id,
            "workflow_state": active_workflow.workflow_state if active_workflow else "idle",
            "has_active_session": active_workflow is not None,
            "active_session": {
                "id": active_workflow.id,
                "state": active_workflow.workflow_state,
                "serial": active_workflow.serial,
                "manufacturer": active_workflow.manufacturer,
                "model": active_workflow.model,
                "device_id": active_workflow.device_id,
                "error_message": active_workflow.error_message,
            } if active_workflow else None,
            "paired": len(devices) > 0,
            "trusted": trusted_count > 0,
            "trusted_count": trusted_count,
            "device_count": len(devices),
            "usb_connected_count": len(usb_devices),
            "usb_devices": usb_devices,
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
                    "serial": d.serial,
                    "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    "twin": twins.get(d.id),
                }
                for d in devices
            ],
        }
    finally:
        db.close()


@router.post("/usb/discover")
async def usb_discover(user_id: str = Depends(get_current_user)):
    """Discover USB-connected Android devices with full info from real ADB"""
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, USBSession, RegisteredDevice

    engine = get_discovery_engine()
    devices = await engine.discover()

    if not devices:
        return {
            "success": True,
            "devices_found": 0,
            "devices": [],
            "message": "No USB devices found. Connect an Android device with USB debugging enabled.",
        }

    db = get_db_session()
    try:
        # Create or update pairing workflow
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.workflow_state.in_(["idle", "discovering"]),
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if not workflow:
            import uuid
            workflow = PairingWorkflow(
                id=f"pwf_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                workflow_state="discovering",
                pairing_type="usb",
            )
            db.add(workflow)
            db.flush()
        else:
            workflow.workflow_state = "discovering"
            workflow.updated_at = datetime.utcnow()

        device_list = []
        for dev in devices:
            # Check if device already registered
            existing = db.query(RegisteredDevice).filter(
                RegisteredDevice.user_id == user_id,
                RegisteredDevice.serial == dev.serial,
            ).first()

            device_list.append({
                **dev.to_dict(),
                "already_registered": existing is not None,
                "device_id": existing.id if existing else None,
            })

            # Upsert USB session
            usb_session = db.query(USBSession).filter(
                USBSession.user_id == user_id,
                USBSession.serial == dev.serial,
            ).first()
            if usb_session:
                usb_session.status = "connected"
                usb_session.manufacturer = dev.manufacturer
                usb_session.model = dev.model
                usb_session.last_heartbeat = datetime.utcnow()
                usb_session.updated_at = datetime.utcnow()
            else:
                usb_session = USBSession(
                    user_id=user_id,
                    serial=dev.serial,
                    status="connected",
                    manufacturer=dev.manufacturer,
                    model=dev.model,
                    adb_authorized=dev.adb_authorized,
                )
                db.add(usb_session)

        workflow.serial = devices[0].serial if devices else None
        workflow.manufacturer = devices[0].manufacturer if devices else None
        workflow.model = devices[0].model if devices else None
        workflow.android_version = devices[0].android_version if devices else None
        workflow.discovered_at = datetime.utcnow()
        db.commit()

    finally:
        db.close()

    _emit_event("DEVICE_FOUND", {
        "count": len(devices),
        "devices": [{"serial": d.serial, "model": d.model, "manufacturer": d.manufacturer} for d in devices],
    })

    _create_audit_log(user_id, "usb_discover", "usb_session", devices[0].serial if devices else "none",
                      {"count": len(devices)})

    return {
        "success": True,
        "devices_found": len(device_list),
        "devices": device_list,
    }


@router.post("/usb/connect")
async def usb_connect(request: ConnectRequest, user_id: str = Depends(get_current_user)):
    """Connect to a discovered USB device, create pairing session"""
    from services.adb_service import get_adb_service, find_adb_binary
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, USBSession, RegisteredDevice

    serial = request.serial
    if not serial:
        raise HTTPException(status_code=400, detail="Serial number required")

    # Verify device is connected via ADB
    adb = get_adb_service(find_adb_binary())
    try:
        devices = await adb.list_devices()
        connected_serials = [d.get("serial") for d in devices if d.get("state") == "device"]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ADB error: {str(e)}")

    if serial not in connected_serials:
        raise HTTPException(status_code=400, detail=f"Device {serial} not connected via USB")

    # Extract full device info
    engine = get_discovery_engine(adb)
    info = await engine._extract_full_info(serial)
    info.adb_authorized = True

    db = get_db_session()
    try:
        # Update or create pairing workflow
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.workflow_state.in_(["idle", "discovering"]),
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if not workflow:
            import uuid
            workflow = PairingWorkflow(
                id=f"pwf_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                workflow_state="connecting",
                pairing_type="usb",
                serial=serial,
                manufacturer=info.manufacturer,
                model=info.model,
                android_version=info.android_version,
                adb_authorized=True,
                usb_authorized=True,
                connected_at=datetime.utcnow(),
            )
            db.add(workflow)
        else:
            workflow.workflow_state = "connecting"
            workflow.serial = serial
            workflow.manufacturer = info.manufacturer
            workflow.model = info.model
            workflow.android_version = info.android_version
            workflow.adb_authorized = True
            workflow.usb_authorized = True
            workflow.connected_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()

        # Update USB session
        usb_session = db.query(USBSession).filter(
            USBSession.user_id == user_id,
            USBSession.serial == serial,
        ).first()
        if usb_session:
            usb_session.status = "pairing"
            usb_session.adb_authorized = True
            usb_session.updated_at = datetime.utcnow()

        db.commit()
        workflow_id = workflow.id

    finally:
        db.close()

    _emit_event("PAIRING_STARTED", {
        "serial": serial,
        "manufacturer": info.manufacturer,
        "model": info.model,
        "workflow_id": workflow_id,
    })

    _create_audit_log(user_id, "usb_connect", "usb_session", serial, {
        "manufacturer": info.manufacturer,
        "model": info.model,
    })

    return {
        "success": True,
        "message": "USB device connected",
        "serial": serial,
        "workflow_id": workflow_id,
        "device_info": info.to_dict(),
    }


@router.post("/usb/verify")
async def usb_verify(request: ConnectRequest, user_id: str = Depends(get_current_user)):
    """Verify device identity using hardware fingerprint"""
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow

    serial = request.serial
    if not serial:
        raise HTTPException(status_code=400, detail="Serial number required")

    engine = get_discovery_engine()
    try:
        verification = await engine.verify_device(serial)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device verification failed: {str(e)}")

    fingerprint = verification.get("fingerprint", "")
    fingerprint_data = verification.get("fingerprint_data", {})

    db = get_db_session()
    try:
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.serial == serial,
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if workflow:
            workflow.workflow_state = "verifying"
            workflow.device_fingerprint = fingerprint
            workflow.verified_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()

    _emit_event("DEVICE_VERIFIED", {
        "serial": serial,
        "fingerprint": fingerprint[:16] + "...",
    })

    _create_audit_log(user_id, "usb_verify", "device", serial, {
        "fingerprint": fingerprint[:16] + "...",
    })

    return {
        "success": True,
        "message": "Device verified successfully",
        "serial": serial,
        "fingerprint": fingerprint,
        "fingerprint_data": {
            "android_id": fingerprint_data.get("android_id", "")[:8] + "...",
            "manufacturer": fingerprint_data.get("manufacturer", ""),
            "model": fingerprint_data.get("model", ""),
            "installed_packages_count": fingerprint_data.get("installed_packages_count", "0"),
        },
        "device_identity_confirmed": True,
    }


@router.post("/device/trust")
async def trust_device(request: TrustRequest, user_id: str = Depends(get_current_user)):
    """Trust a device - stores trusted relationship, creates trust token"""
    from services.trust_engine import get_trust_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, DeviceTwin

    device_id = request.device_id
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")

    trust_engine = get_trust_engine()
    result = trust_engine.trust_device(
        device_id=device_id,
        user_id=user_id,
        trust_level=request.trust_level,
        duration_days=365,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    db = get_db_session()
    try:
        # Update pairing workflow
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.device_id == device_id,
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if not workflow:
            workflow = db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.workflow_state.in_(["verifying", "connecting"]),
            ).order_by(PairingWorkflow.started_at.desc()).first()

        if workflow:
            workflow.workflow_state = "trusting"
            workflow.device_id = device_id
            workflow.trusted_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()

        # Update device twin trust score
        twin = db.query(DeviceTwin).filter(
            DeviceTwin.device_id == device_id
        ).first()
        if twin:
            twin.trust_score = 1.0
            twin.updated_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()

    _emit_event("DEVICE_TRUSTED", {
        "device_id": device_id,
        "trust_level": request.trust_level,
        "trust_token": result.trust_token[:16] + "...",
    })

    _create_audit_log(user_id, "trust_device", "device", device_id, {
        "trust_level": request.trust_level,
    })

    return {
        "success": True,
        "message": result.message,
        "device_id": device_id,
        "trust_level": result.trust_level,
        "trust_token": result.trust_token,
        "certificate": result.certificate,
    }


@router.post("/device/permissions")
async def sync_permissions(request: PermissionUpdateRequest, user_id: str = Depends(get_current_user)):
    """Synchronize device permissions from Flutter Agent"""
    from services.permission_engine import get_permission_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, DeviceTwin

    device_id = request.device_id
    permissions = request.permissions

    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID required")

    engine = get_permission_engine()

    # Store each permission status
    for perm_name, status in permissions.items():
        engine.update_permission_status(device_id, perm_name, status)

    db = get_db_session()
    try:
        # Update pairing workflow
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.device_id == device_id,
        ).order_by(PairingWorkflow.started_at.desc()).first()
        if workflow:
            workflow.workflow_state = "permissions"
            workflow.permissions_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()

        # Update device twin permissions
        twin = db.query(DeviceTwin).filter(
            DeviceTwin.device_id == device_id
        ).first()
        if twin:
            twin.permissions = permissions
            twin.updated_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()

    _emit_event("PERMISSIONS_UPDATED", {
        "device_id": device_id,
        "permissions": permissions,
    })

    return {
        "success": True,
        "message": f"Permissions synchronized: {len(permissions)} permissions",
        "device_id": device_id,
        "permissions": permissions,
    }


@router.post("/device/register")
async def register_device_endpoint(request: ConnectRequest, user_id: str = Depends(get_current_user)):
    """Register device with complete hardware and software profile"""
    from services.device_registration_service import get_registration_service
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow

    serial = request.serial
    if not serial:
        raise HTTPException(status_code=400, detail="Serial number required")

    # Get full device info
    engine = get_discovery_engine()
    try:
        info = await engine._extract_full_info(serial)
        verification = await engine.verify_device(serial)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device info extraction failed: {str(e)}")

    # Build registration data
    reg_data = {
        "device_name": info.device_name or info.model or "Android Device",
        "manufacturer": info.manufacturer,
        "model": info.model,
        "android_version": info.android_version,
        "battery": info.battery_percentage,
        "serial": serial,
        "ram": f"{info.ram_total_kb // 1024} MB" if info.ram_total_kb else "",
        "capabilities": ["adb", "screenshot", "navigation", "notification"],
        "installed_apps_count": int(verification.get("fingerprint_data", {}).get("installed_packages_count", "0")),
        "connection_type": "usb",
    }

    reg_service = get_registration_service()
    result = reg_service.register_device(user_id, reg_data)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    device_id = result.device_id

    db = get_db_session()
    try:
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.workflow_state.in_(["permissions", "trusting", "verifying", "connecting"]),
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if workflow:
            workflow.workflow_state = "registering"
            workflow.device_id = device_id
            workflow.registered_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

    _emit_event("DEVICE_REGISTERED", {
        "device_id": device_id,
        "serial": serial,
        "manufacturer": info.manufacturer,
        "model": info.model,
    })

    _create_audit_log(user_id, "register_device", "device", device_id, {
        "serial": serial,
        "manufacturer": info.manufacturer,
        "model": info.model,
    })

    return {
        "success": True,
        "message": "Device registered successfully",
        "device_id": device_id,
        "device_name": reg_data["device_name"],
        "manufacturer": info.manufacturer,
        "model": info.model,
    }


@router.get("/device/twin")
async def get_device_twin(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Get device digital twin"""
    from services.device_twin_service import get_twin_service
    twin = get_twin_service().get_twin(device_id, user_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Device twin not found")
    return {
        "success": True,
        "twin": twin,
    }


@router.get("/device/current")
async def get_current_device(user_id: str = Depends(get_current_user)):
    """Get most recent device with live status"""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice, DeviceHeartbeat, DeviceTwin

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
        ).order_by(RegisteredDevice.last_seen.desc()).first()

        if not device:
            return {"success": True, "device": None, "message": "No device registered"}

        # Get latest heartbeat
        heartbeat = db.query(DeviceHeartbeat).filter(
            DeviceHeartbeat.device_id == device.id,
        ).order_by(DeviceHeartbeat.recorded_at.desc()).first()

        # Get twin
        twin = db.query(DeviceTwin).filter(
            DeviceTwin.device_id == device.id
        ).first()

        return {
            "success": True,
            "device": {
                "id": device.id,
                "name": device.device_name,
                "manufacturer": device.manufacturer,
                "model": device.model,
                "android_version": device.android_version,
                "battery": heartbeat.battery_level if heartbeat else device.battery_level,
                "charging": heartbeat.battery_charging if heartbeat else False,
                "is_online": device.is_online,
                "connection_type": device.connection_type,
                "serial": device.serial,
                "screen_width": device.screen_width,
                "screen_height": device.screen_height,
                "foreground_app": heartbeat.foreground_app if heartbeat else None,
                "foreground_package": heartbeat.foreground_package if heartbeat else None,
                "screen_state": heartbeat.screen_state if heartbeat else None,
                "lock_state": heartbeat.lock_state if heartbeat else None,
                "network_type": heartbeat.network_type if heartbeat else None,
                "network_strength": heartbeat.network_strength if heartbeat else None,
                "memory_usage_mb": heartbeat.memory_usage_mb if heartbeat else None,
                "cpu_usage_percent": heartbeat.cpu_usage_percent if heartbeat else None,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "twin": {
                    "readiness_score": twin.readiness_score if twin else None,
                    "ai_ready": twin.ai_ready if twin else False,
                    "health_score": twin.health_score if twin else None,
                    "trust_score": twin.trust_score if twin else None,
                    "sync_state": twin.sync_state if twin else "none",
                } if twin else None,
            },
        }
    finally:
        db.close()


@router.post("/device/twin/create")
async def create_device_twin(request: ConnectRequest, user_id: str = Depends(get_current_user)):
    """Create digital twin for a registered device with capability scan"""
    from services.device_twin_service import get_twin_service, DeviceTwinData
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, RegisteredDevice, DevicePermission, DeviceCapability, CapabilityStatus

    serial = request.serial
    if not serial:
        raise HTTPException(status_code=400, detail="Serial required")

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
            RegisteredDevice.serial == serial,
        ).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not registered")

        device_id = device.id
    finally:
        db.close()

    # Get full device info for twin creation
    engine = get_discovery_engine()
    try:
        info = await engine._extract_full_info(serial)
        verification = await engine.verify_device(serial)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device info extraction failed: {str(e)}")

    # Load permissions from database
    db = get_db_session()
    try:
        perms = db.query(DevicePermission).filter(
            DevicePermission.device_id == device_id,
        ).all()
        permissions = {p.permission_name: p.status.value if hasattr(p.status, 'value') else str(p.status) for p in perms}

        # Check capabilities
        caps_result = db.query(DeviceCapability).filter(
            DeviceCapability.device_id == device_id,
        ).all()
    finally:
        db.close()

    # Determine capabilities from device info
    capabilities = ["adb", "screenshot"]
    if info.accessibility_service:
        capabilities.append("accessibility")
    if info.screen_width > 0:
        capabilities.append("navigation")

    twin_data = DeviceTwinData(
        manufacturer=info.manufacturer,
        model=info.model,
        brand=info.brand,
        android_version=info.android_version,
        sdk_version=info.sdk_version,
        build_number=info.build_number,
        cpu_abi=info.cpu_abi,
        ram_total_gb=round(info.ram_total_kb / (1024 * 1024), 2) if info.ram_total_kb else 0,
        screen_width=info.screen_width,
        screen_height=info.screen_height,
        installed_apps_count=int(verification.get("fingerprint_data", {}).get("installed_packages_count", "0")),
        capabilities=capabilities,
        permissions=permissions,
        security_patch=verification.get("fingerprint_data", {}).get("security_patch", ""),
    )

    twin_service = get_twin_service()
    twin = twin_service.create_or_update_twin(device_id, user_id, twin_data)

    db = get_db_session()
    try:
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.device_id == device_id,
        ).order_by(PairingWorkflow.started_at.desc()).first()
        if workflow:
            workflow.workflow_state = "twin_creating"
            workflow.twin_created_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

    _emit_event("DEVICE_READY", {
        "device_id": device_id,
        "twin_id": twin.get("id", "") if twin else "",
        "readiness_score": twin.get("readiness_score", 0) if twin else 0,
    })

    _create_audit_log(user_id, "create_device_twin", "device_twin", device_id, {
        "capabilities": capabilities,
        "readiness_score": twin.get("readiness_score", 0) if twin else 0,
    })

    return {
        "success": True,
        "message": "Device twin created",
        "device_id": device_id,
        "twin": twin,
    }


@router.get("/device/capabilities")
async def get_device_capabilities(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Get all capabilities for a device with readiness scan"""
    from services.ai_readiness import get_readiness_engine
    from database.connection import get_db_session
    from database.auth_models import DeviceCapability, CapabilityStatus, DeviceTwin

    try:
        engine = get_readiness_engine()
        result = await engine.check_readiness(device_id)
    except Exception:
        # Fallback: read from database
        db = get_db_session()
        try:
            caps = db.query(DeviceCapability).filter(
                DeviceCapability.device_id == device_id,
            ).all()
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()

            capabilities = []
            for cap in caps:
                capabilities.append({
                    "name": cap.capability_name,
                    "status": cap.status.value if hasattr(cap.status, 'value') else str(cap.status),
                    "score": cap.score,
                })

            return {
                "success": True,
                "device_id": device_id,
                "readiness_score": twin.readiness_score if twin else 0,
                "ai_ready": twin.ai_ready if twin else False,
                "capabilities": capabilities,
            }
        finally:
            db.close()

    return {
        "success": True,
        "device_id": device_id,
        "ready": result.ready,
        "readiness_score": result.score,
        "missing_capabilities": result.missing_capabilities,
        "message": result.message,
        "capabilities": [
            {"name": c.name, "status": c.status, "score": c.score, "message": c.message}
            for c in result.capabilities
        ] if hasattr(result, 'capabilities') else [],
    }


@router.get("/device/permissions")
async def get_device_permissions(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Get all permission states for a device"""
    from services.permission_engine import get_permission_engine
    engine = get_permission_engine()
    summary = engine.get_permission_summary(device_id)
    return {
        "success": True,
        "device_id": device_id,
        "summary": summary,
    }


@router.get("/device/heartbeat")
async def get_device_heartbeat(device_id: str = Query(...), user_id: str = Depends(get_current_user)):
    """Get latest heartbeat for device"""
    from services.heartbeat_service import get_heartbeat_service
    service = get_heartbeat_service()
    data = service.get_device_data(device_id)
    online = service.is_device_online(device_id)
    if not data:
        return {
            "success": True,
            "online": False,
            "heartbeat": None,
            "message": "No heartbeat data available",
        }
    return {
        "success": True,
        "online": online,
        "device_id": device_id,
        "heartbeat": {
            "battery_level": data.battery_level,
            "battery_charging": data.battery_charging,
            "foreground_app": data.foreground_app,
            "foreground_package": data.foreground_package,
            "current_activity": data.current_activity,
            "screen_state": data.screen_state,
            "lock_state": data.lock_state,
            "network_type": data.network_type,
            "network_strength": data.network_strength,
            "memory_usage_mb": data.memory_usage_mb,
            "cpu_usage_percent": data.cpu_usage_percent,
            "storage_free_gb": data.storage_free_gb,
            "storage_total_gb": data.storage_total_gb,
            "uptime_seconds": data.uptime_seconds,
            "agent_version": data.agent_version,
            "accessibility_active": data.accessibility_active,
        },
    }


@router.post("/device/disconnect")
async def disconnect_device(request: DisconnectRequest, user_id: str = Depends(get_current_user)):
    """Disconnect a paired device"""
    from services.heartbeat_service import get_heartbeat_service
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice, USBSession, PairingWorkflow

    device_id = request.device_id

    # Mark disconnected in heartbeat service
    heartbeat_service = get_heartbeat_service()
    heartbeat_service.mark_device_disconnected(device_id)

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.id == device_id,
            RegisteredDevice.user_id == user_id,
        ).first()
        if device:
            device.is_online = False
            device.updated_at = datetime.utcnow()

        # Update USB session
        if device and device.serial:
            usb_session = db.query(USBSession).filter(
                USBSession.user_id == user_id,
                USBSession.serial == device.serial,
            ).first()
            if usb_session:
                usb_session.status = "disconnected"
                usb_session.disconnected_at = datetime.utcnow()
                usb_session.updated_at = datetime.utcnow()

        # Update workflow
        workflow = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.device_id == device_id,
        ).order_by(PairingWorkflow.started_at.desc()).first()
        if workflow:
            workflow.workflow_state = "idle"
            workflow.completed_at = datetime.utcnow()
            workflow.updated_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()

    _emit_event("DEVICE_DISCONNECTED", {
        "device_id": device_id,
        "reason": "user_disconnected",
    })

    _create_audit_log(user_id, "disconnect_device", "device", device_id, {"reason": "user_disconnected"})

    return {
        "success": True,
        "message": "Device disconnected",
    }


# ==================== Flutter Agent WebSocket ====================

@router.websocket("/ws/device")
async def device_websocket(websocket: WebSocket):
    """WebSocket for real-time device updates (battery, foreground, heartbeats, etc)"""
    from services.websocket_service import get_websocket_manager
    from services.heartbeat_service import get_heartbeat_service, HeartbeatData

    mgr = get_websocket_manager()
    await websocket.accept()

    # Register as a system-level connection (no user_id filtering)
    if "system" not in mgr.active_connections:
        mgr.active_connections["system"] = set()
    mgr.active_connections["system"].add(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"type": raw}

            msg_type = payload.get("type", "ping")

            if msg_type == "ping":
                await websocket.send_json({"event": "pong", "timestamp": datetime.utcnow().isoformat()})

            elif msg_type == "heartbeat":
                device_id = payload.get("device_id", "")
                hb = HeartbeatData(
                    device_id=device_id,
                    battery_level=payload.get("battery_level", 0),
                    battery_charging=payload.get("battery_charging", False),
                    foreground_app=payload.get("foreground_app", ""),
                    foreground_package=payload.get("foreground_package", ""),
                    current_activity=payload.get("current_activity", ""),
                    screen_state=payload.get("screen_state", ""),
                    lock_state=payload.get("lock_state", ""),
                    network_type=payload.get("network_type", ""),
                    network_strength=payload.get("network_strength", 0),
                    memory_usage_mb=payload.get("memory_usage_mb", 0),
                    cpu_usage_percent=payload.get("cpu_usage_percent", 0.0),
                    storage_free_gb=payload.get("storage_free_gb", 0.0),
                    storage_total_gb=payload.get("storage_total_gb", 0.0),
                    uptime_seconds=payload.get("uptime_seconds", 0),
                    agent_version=payload.get("agent_version", ""),
                    accessibility_active=payload.get("accessibility_active", False),
                )
                was_disconnected = get_heartbeat_service().record_heartbeat(device_id, hb)
                await mgr.send_personal_message({
                    "event": "HEARTBEAT",
                    "device_id": device_id,
                    "battery_level": hb.battery_level,
                    "battery_charging": hb.battery_charging,
                    "foreground_app": hb.foreground_app,
                    "foreground_package": hb.foreground_package,
                    "current_activity": hb.current_activity,
                    "screen_state": hb.screen_state,
                    "lock_state": hb.lock_state,
                    "network_type": hb.network_type,
                    "timestamp": datetime.utcnow().isoformat(),
                }, device_id)
                if was_disconnected:
                    await mgr.send_personal_message({
                        "event": "DEVICE_RECONNECTED",
                        "device_id": device_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }, device_id)

            elif msg_type == "subscribe":
                device_id = payload.get("device_id", "")
                # Track subscription
                if device_id not in mgr.active_connections:
                    mgr.active_connections[device_id] = set()
                mgr.active_connections[device_id].add(websocket)
                await websocket.send_json({
                    "event": "subscribed",
                    "device_id": device_id,
                })

            elif msg_type == "unsubscribe":
                device_id = payload.get("device_id", "")
                if device_id in mgr.active_connections:
                    mgr.active_connections[device_id].discard(websocket)
                await websocket.send_json({
                    "event": "unsubscribed",
                    "device_id": device_id,
                })

            elif msg_type == "permission_update":
                device_id = payload.get("device_id", "")
                permissions = payload.get("permissions", {})
                from services.permission_engine import get_permission_engine
                engine = get_permission_engine()
                for perm_name, status in permissions.items():
                    engine.update_permission_status(device_id, perm_name, status)
                await mgr.send_personal_message({
                    "event": "PERMISSIONS_UPDATED",
                    "device_id": device_id,
                    "permissions": permissions,
                }, device_id)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Device WebSocket error: {e}")
    finally:
        mgr.active_connections.get("system", set()).discard(websocket)
        for key in list(mgr.active_connections.keys()):
            mgr.active_connections[key].discard(websocket)


# ==================== Flutter Agent Heartbeat Endpoint ====================

class AgentHeartbeatRequest(BaseModel):
    device_id: str
    battery_level: int = 0
    battery_charging: bool = False
    foreground_app: str = ""
    foreground_package: str = ""
    current_activity: str = ""
    screen_state: str = ""
    lock_state: str = ""
    network_type: str = ""
    network_strength: int = 0
    memory_usage_mb: int = 0
    cpu_usage_percent: float = 0.0
    storage_free_gb: float = 0.0
    storage_total_gb: float = 0.0
    uptime_seconds: int = 0
    agent_version: str = ""
    accessibility_active: bool = False


@router.post("/agent/heartbeat")
async def agent_heartbeat(request: AgentHeartbeatRequest):
    """Receive heartbeat from Flutter agent (no auth required - uses device_id as identity)"""
    from services.heartbeat_service import get_heartbeat_service, HeartbeatData

    device_id = request.device_id
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")

    hb = HeartbeatData(
        device_id=device_id,
        battery_level=request.battery_level,
        battery_charging=request.battery_charging,
        foreground_app=request.foreground_app,
        foreground_package=request.foreground_package,
        current_activity=request.current_activity,
        screen_state=request.screen_state,
        lock_state=request.lock_state,
        network_type=request.network_type,
        network_strength=request.network_strength,
        memory_usage_mb=request.memory_usage_mb,
        cpu_usage_percent=request.cpu_usage_percent,
        storage_free_gb=request.storage_free_gb,
        storage_total_gb=request.storage_total_gb,
        uptime_seconds=request.uptime_seconds,
        agent_version=request.agent_version,
        accessibility_active=request.accessibility_active,
    )

    service = get_heartbeat_service()
    was_disconnected = service.record_heartbeat(device_id, hb)

    # Emit events
    try:
        from services.websocket_service import get_websocket_manager
        mgr = get_websocket_manager()
        await mgr.send_personal_message({
            "event": "HEARTBEAT",
            "device_id": device_id,
            "battery_level": hb.battery_level,
            "battery_charging": hb.battery_charging,
            "foreground_app": hb.foreground_app,
            "foreground_package": hb.foreground_package,
            "current_activity": hb.current_activity,
            "screen_state": hb.screen_state,
            "lock_state": hb.lock_state,
            "timestamp": datetime.utcnow().isoformat(),
        }, device_id)
    except Exception:
        pass

    return {
        "success": True,
        "device_id": device_id,
        "reconnected": was_disconnected,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==================== Flutter Agent Permission Sync ====================

class AgentPermissionSyncRequest(BaseModel):
    device_id: str
    permissions: Dict[str, str]


@router.post("/agent/permissions/sync")
async def agent_permissions_sync(request: AgentPermissionSyncRequest):
    """Receive permission statuses from Flutter agent"""
    from services.permission_engine import get_permission_engine

    device_id = request.device_id
    permissions = request.permissions

    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")

    engine = get_permission_engine()
    for perm_name, status in permissions.items():
        engine.update_permission_status(device_id, perm_name, status)

    _emit_event("PERMISSIONS_UPDATED", {
        "device_id": device_id,
        "permissions": permissions,
    })

    return {
        "success": True,
        "message": f"Synced {len(permissions)} permissions",
    }
