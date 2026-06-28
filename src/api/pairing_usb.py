"""
APA-OS USB Pairing API
Complete production endpoints for USB device discovery, pairing, verification, trust, and registration
Backed by the PairingWorkflow state machine for consistent state transitions
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

from services.pairing_workflow_service import (
    get_pairing_workflow_service,
    WorkflowState,
    PairingWorkflowService,
)

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
    """Get complete pairing workflow status with state machine state"""
    svc = get_pairing_workflow_service()
    status = svc.get_full_status(user_id)
    return {"success": True, **status}


@router.post("/usb/discover")
async def usb_discover(user_id: str = Depends(get_current_user)):
    """Discover USB-connected Android devices with full info from real ADB"""
    from services.usb_discovery_service import get_discovery_engine
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow, USBSession, RegisteredDevice

    svc = get_pairing_workflow_service()
    workflow = svc.get_or_create_workflow(user_id)

    # Transition to DISCOVERING
    workflow = svc.transition_to(
        workflow.id, WorkflowState.DISCOVERING,
        progress=5,
    )
    if not workflow:
        raise HTTPException(status_code=500, detail="Failed to create workflow")

    engine = get_discovery_engine()
    try:
        devices = await engine.discover()
    except Exception as e:
        svc.transition_to(
            workflow.id, WorkflowState.PAIRING_FAILED,
            error_message=f"Discovery error: {str(e)}",
            error_code="DISCOVERY_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"Discovery error: {str(e)}")

    if not devices:
        # Stay in DISCOVERING - user can retry
        return {
            "success": True,
            "devices_found": 0,
            "devices": [],
            "workflow_id": workflow.id,
            "state": WorkflowState.DISCOVERING.value,
            "progress": 5,
            "message": "No USB devices found. Connect an Android device with USB debugging enabled.",
        }

    db = get_db_session()
    try:
        device_list = []
        for dev in devices:
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
        db.commit()
    finally:
        db.close()

    first_dev = devices[0]
    workflow = svc.transition_to(
        workflow.id, WorkflowState.DEVICE_FOUND,
        progress=10,
        serial=first_dev.serial,
        manufacturer=first_dev.manufacturer,
        model=first_dev.model,
        android_version=first_dev.android_version,
        connected=True,
        is_online=True,
    )

    _create_audit_log(user_id, "usb_discover", "usb_session", first_dev.serial, {"count": len(devices)})

    return {
        "success": True,
        "devices_found": len(device_list),
        "devices": device_list,
        "workflow_id": workflow.id,
        "state": workflow.workflow_state,
        "progress": workflow.progress,
        "message": f"Found {len(device_list)} device(s)",
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

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)
    if not workflow:
        workflow = svc.get_or_create_workflow(user_id, serial)

    # Transition to CONNECTING
    workflow = svc.transition_to(
        workflow.id, WorkflowState.CONNECTING,
        progress=20, serial=serial,
    )
    if not workflow:
        raise HTTPException(status_code=500, detail="Failed to update workflow")

    # Verify device is connected via ADB
    adb = get_adb_service(find_adb_binary())
    try:
        devices = await adb.list_devices()
        connected_serials = [d.get("serial") for d in devices if d.get("state") == "device"]
    except Exception as e:
        svc.transition_to(
            workflow.id, WorkflowState.ADB_OFFLINE,
            error_message=f"ADB error: {str(e)}",
            error_code="ADB_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"ADB error: {str(e)}")

    if serial not in connected_serials:
        svc.transition_to(
            workflow.id, WorkflowState.USB_DISCONNECTED,
            error_message=f"Device {serial} not connected via USB",
            error_code="DEVICE_NOT_FOUND",
        )
        raise HTTPException(status_code=400, detail=f"Device {serial} not connected via USB")

    # Extract full device info
    engine = get_discovery_engine(adb)
    try:
        info = await engine._extract_full_info(serial)
        info.adb_authorized = True
    except Exception as e:
        svc.transition_to(
            workflow.id, WorkflowState.PAIRING_FAILED,
            error_message=f"Failed to extract device info: {str(e)}",
            error_code="INFO_EXTRACTION_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"Device info extraction failed: {str(e)}")

    # Update to CONNECTED
    workflow = svc.transition_to(
        workflow.id, WorkflowState.CONNECTED,
        progress=25,
        serial=serial,
        manufacturer=info.manufacturer,
        model=info.model,
        android_version=info.android_version,
        connected=True,
        is_online=True,
    )

    # Update USB session
    db = get_db_session()
    try:
        usb_session = db.query(USBSession).filter(
            USBSession.user_id == user_id,
            USBSession.serial == serial,
        ).first()
        if usb_session:
            usb_session.status = "pairing"
            usb_session.adb_authorized = True
            usb_session.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

    _create_audit_log(user_id, "usb_connect", "usb_session", serial, {
        "manufacturer": info.manufacturer,
        "model": info.model,
    })

    return {
        "success": True,
        "message": "USB device connected",
        "serial": serial,
        "workflow_id": workflow.id,
        "state": workflow.workflow_state,
        "progress": workflow.progress,
        "device_info": info.to_dict(),
    }


@router.post("/usb/verify")
async def usb_verify(request: ConnectRequest, user_id: str = Depends(get_current_user)):
    """Verify device identity using hardware fingerprint with real ADB data"""
    from services.usb_discovery_service import get_discovery_engine
    from services.adb_service import get_adb_service, find_adb_binary
    from database.connection import get_db_session
    from database.auth_models import PairingWorkflow

    serial = request.serial
    if not serial:
        raise HTTPException(status_code=400, detail="Serial number required")

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)
    if not workflow:
        workflow = svc.get_or_create_workflow(user_id, serial)

    # Transition to VERIFYING
    workflow = svc.transition_to(
        workflow.id, WorkflowState.VERIFYING,
        progress=35, serial=serial,
    )
    if not workflow:
        raise HTTPException(status_code=500, detail="Failed to update workflow")

    # Run verification with timeout
    try:
        verification = await asyncio.wait_for(
            _run_verification(serial),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        svc.transition_to(
            workflow.id, WorkflowState.TIMEOUT,
            error_message="Verification timed out after 30 seconds",
            error_code="VERIFICATION_TIMEOUT",
        )
        return {
            "success": False,
            "state": WorkflowState.TIMEOUT.value,
            "progress": workflow.progress,
            "message": "Verification timed out",
            "serial": serial,
        }
    except Exception as e:
        svc.transition_to(
            workflow.id, WorkflowState.VERIFICATION_FAILED,
            error_message=f"Verification error: {str(e)}",
            error_code="VERIFICATION_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"Device verification failed: {str(e)}")

    fingerprint = verification.get("fingerprint", "")
    fingerprint_data = verification.get("fingerprint_data", {})

    # Compare against database if device was previously registered
    db = get_db_session()
    try:
        existing_device = db.query(PairingWorkflow).filter(
            PairingWorkflow.user_id == user_id,
            PairingWorkflow.serial == serial,
            PairingWorkflow.device_fingerprint != None,
            PairingWorkflow.workflow_state == WorkflowState.ACTIVE.value,
        ).order_by(PairingWorkflow.started_at.desc()).first()

        if existing_device and existing_device.device_fingerprint:
            if existing_device.device_fingerprint != fingerprint:
                svc.transition_to(
                    workflow.id, WorkflowState.VERIFICATION_FAILED,
                    error_message="Device fingerprint mismatch. This may be a different device.",
                    error_code="FINGERPRINT_MISMATCH",
                )
                return {
                    "success": False,
                    "state": WorkflowState.VERIFICATION_FAILED.value,
                    "progress": workflow.progress,
                    "message": "Device fingerprint mismatch",
                    "serial": serial,
                    "fingerprint": fingerprint,
                    "device_identity_confirmed": False,
                }
    finally:
        db.close()

    # Success - transition to VERIFIED
    workflow = svc.transition_to(
        workflow.id, WorkflowState.VERIFIED,
        progress=50,
        fingerprint=fingerprint,
        fingerprint_data=fingerprint_data,
    )

    _create_audit_log(user_id, "usb_verify", "device", serial, {
        "fingerprint": fingerprint[:16] + "...",
    })

    return {
        "success": True,
        "message": "Device verified successfully",
        "serial": serial,
        "workflow_id": workflow.id,
        "state": workflow.workflow_state,
        "progress": workflow.progress,
        "fingerprint": fingerprint,
        "fingerprint_data": {
            "android_id": fingerprint_data.get("android_id", "")[:8] + "...",
            "manufacturer": fingerprint_data.get("manufacturer", ""),
            "model": fingerprint_data.get("model", ""),
            "installed_packages_count": fingerprint_data.get("installed_packages_count", "0"),
        },
        "device_identity_confirmed": True,
    }


async def _run_verification(serial: str) -> dict:
    """Run real ADB verification commands to build hardware fingerprint"""
    from services.adb_service import get_adb_service, find_adb_binary

    adb = get_adb_service(find_adb_binary())

    # Collect device properties
    props = {}
    prop_keys = [
        "ro.product.manufacturer",
        "ro.product.model",
        "ro.build.version.release",
        "ro.build.version.sdk",
        "ro.serialno",
        "ro.product.cpu.abi",
        "ro.build.display.id",
        "ro.build.fingerprint",
        "ro.build.date.utc",
    ]

    for key in prop_keys:
        try:
            result = await adb.run_shell_command(f"getprop {key}", serial)
            props[key] = result.strip() if result else ""
        except Exception:
            props[key] = ""

    # Get settings
    settings_data = {}
    setting_keys = ["secure android_id", "system screen_brightness", "system screen_off_timeout"]
    for key in setting_keys:
        try:
            ns, k = key.split(" ", 1)
            result = await adb.run_shell_command(f"settings get {ns} {k}", serial)
            settings_data[key] = result.strip() if result else ""
        except Exception:
            settings_data[key] = ""

    # Get battery info
    battery_info = {}
    try:
        battery_raw = await adb.run_shell_command("dumpsys battery", serial)
        if battery_raw:
            for line in battery_raw.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    battery_info[k.strip()] = v.strip()
    except Exception:
        pass

    # Get screen size
    screen_size = ""
    try:
        wm_result = await adb.run_shell_command("wm size", serial)
        if wm_result:
            screen_size = wm_result.replace("Physical size: ", "").strip()
    except Exception:
        pass

    # Get window info
    window_info = {}
    try:
        window_raw = await adb.run_shell_command("dumpsys window", serial)
        if window_raw:
            for line in window_raw.split("\n"):
                line = line.strip()
                if "mCurrentFocus" in line or "mFocusedApp" in line or "DisplayPowerController" in line:
                    window_info["focus"] = line
    except Exception:
        pass

    # Get installed packages count
    packages_count = "0"
    try:
        packages = await adb.run_shell_command("pm list packages", serial)
        if packages:
            packages_count = str(len([p for p in packages.split("\n") if p.strip()]))
    except Exception:
        pass

    # Build fingerprint
    fingerprint_parts = [
        props.get("ro.serialno", ""),
        props.get("ro.product.manufacturer", ""),
        props.get("ro.product.model", ""),
        settings_data.get("secure android_id", ""),
        props.get("ro.build.fingerprint", ""),
        props.get("ro.build.date.utc", ""),
    ]
    fingerprint_raw = "|".join(fingerprint_parts)
    fingerprint = hashlib.sha256(fingerprint_raw.encode()).hexdigest()

    return {
        "fingerprint": fingerprint,
        "fingerprint_data": {
            "android_id": settings_data.get("secure android_id", ""),
            "manufacturer": props.get("ro.product.manufacturer", ""),
            "model": props.get("ro.product.model", ""),
            "android_version": props.get("ro.build.version.release", ""),
            "sdk_version": props.get("ro.build.version.sdk", ""),
            "cpu_abi": props.get("ro.product.cpu.abi", ""),
            "build_display": props.get("ro.build.display.id", ""),
            "build_fingerprint": props.get("ro.build.fingerprint", ""),
            "screen_size": screen_size,
            "battery_level": battery_info.get("level", "0"),
            "battery_status": battery_info.get("status", "unknown"),
            "installed_packages_count": packages_count,
            "security_patch": "",  # Would need additional adb call
        },
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

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)

    if workflow:
        svc.transition_to(workflow.id, WorkflowState.TRUST_PENDING, progress=55)

    trust_engine = get_trust_engine()
    result = trust_engine.trust_device(
        device_id=device_id,
        user_id=user_id,
        trust_level=request.trust_level,
        duration_days=365,
    )

    if not result.success:
        if workflow:
            svc.transition_to(
                workflow.id, WorkflowState.PAIRING_FAILED,
                error_message=result.message,
                error_code="TRUST_FAILED",
            )
        raise HTTPException(status_code=400, detail=result.message)

    if workflow:
        svc.transition_to(
            workflow.id, WorkflowState.TRUSTED,
            progress=60, device_id=device_id,
        )

        # Update device twin trust score
        db = get_db_session()
        try:
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()
            if twin:
                twin.trust_score = 1.0
                twin.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    _create_audit_log(user_id, "trust_device", "device", device_id, {
        "trust_level": request.trust_level,
    })

    return {
        "success": True,
        "message": result.message,
        "device_id": device_id,
        "state": workflow.workflow_state if workflow else "TRUSTED",
        "progress": workflow.progress if workflow else 60,
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
    for perm_name, status in permissions.items():
        engine.update_permission_status(device_id, perm_name, status)

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)

    if workflow:
        svc.transition_to(
            workflow.id, WorkflowState.PERMISSION_SYNC,
            progress=65, device_id=device_id,
        )

        db = get_db_session()
        try:
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()
            if twin:
                twin.permissions = permissions
                twin.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    return {
        "success": True,
        "message": f"Permissions synchronized: {len(permissions)} permissions",
        "device_id": device_id,
        "state": workflow.workflow_state if workflow else "PERMISSION_SYNC",
        "progress": workflow.progress if workflow else 65,
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

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)
    if not workflow:
        workflow = svc.get_or_create_workflow(user_id, serial)

    svc.transition_to(workflow.id, WorkflowState.REGISTERING, progress=70, serial=serial)

    # Get full device info
    engine = get_discovery_engine()
    try:
        info = await engine._extract_full_info(serial)
        verification = await engine.verify_device(serial)
    except Exception as e:
        svc.transition_to(
            workflow.id, WorkflowState.PAIRING_FAILED,
            error_message=f"Device info extraction failed: {str(e)}",
            error_code="INFO_EXTRACTION_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"Device info extraction failed: {str(e)}")

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
        svc.transition_to(
            workflow.id, WorkflowState.PAIRING_FAILED,
            error_message=result.message,
            error_code="REGISTRATION_FAILED",
        )
        raise HTTPException(status_code=400, detail=result.message)

    device_id = result.device_id

    workflow = svc.transition_to(
        workflow.id, WorkflowState.DEVICE_REGISTERED,
        progress=75, device_id=device_id,
    )

    return {
        "success": True,
        "message": "Device registered successfully",
        "device_id": device_id,
        "workflow_id": workflow.id,
        "state": workflow.workflow_state,
        "progress": workflow.progress,
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
    """Get current device with live connection status.
    Never returns stale/cached data - always re-checks if device is actually connected."""
    from database.connection import get_db_session
    from database.auth_models import RegisteredDevice, DeviceHeartbeat, DeviceTwin, PairingWorkflow
    from services.pairing_workflow_service import get_pairing_workflow_service, WorkflowState

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)

    db = get_db_session()
    try:
        device = db.query(RegisteredDevice).filter(
            RegisteredDevice.user_id == user_id,
        ).order_by(RegisteredDevice.last_seen.desc()).first()

        if not device:
            return {
                "success": True,
                "connected": False,
                "device": None,
                "state": WorkflowState.IDLE.value,
                "message": "No device registered",
            }

        # Verify device is actually still connected via ADB
        is_actually_connected = False
        if device.serial:
            is_actually_connected = svc.is_device_connected_via_adb(device.serial)

        # If ADB says disconnected but DB says online, fix the inconsistency
        if device.is_online and not is_actually_connected:
            device.is_online = False
            device.updated_at = datetime.utcnow()
            if workflow:
                svc.transition_to(
                    workflow.id, WorkflowState.USB_DISCONNECTED,
                    error_message="Device disconnected (detected on status check)",
                    connected=False, is_online=False,
                )
            db.commit()

        if not is_actually_connected:
            return {
                "success": True,
                "connected": False,
                "device": None,
                "state": workflow.workflow_state if workflow else WorkflowState.IDLE.value,
                "message": "Device not connected",
            }

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
            "connected": True,
            "state": workflow.workflow_state if workflow else WorkflowState.ACTIVE.value,
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

    svc = get_pairing_workflow_service()
    workflow = svc.get_active_workflow(user_id)
    if not workflow:
        workflow = svc.get_or_create_workflow(user_id, serial)

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
        svc.transition_to(
            workflow.id, WorkflowState.PAIRING_FAILED,
            error_message=f"Device info extraction failed: {str(e)}",
            error_code="INFO_EXTRACTION_ERROR",
        )
        raise HTTPException(status_code=503, detail=f"Device info extraction failed: {str(e)}")

    # Load permissions from database
    db = get_db_session()
    try:
        perms = db.query(DevicePermission).filter(
            DevicePermission.device_id == device_id,
        ).all()
        permissions = {p.permission_name: p.status.value if hasattr(p.status, 'value') else str(p.status) for p in perms}
    finally:
        db.close()

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

    # Transition through twin created and AI check to READY
    workflow = svc.transition_to(
        workflow.id, WorkflowState.DEVICE_TWIN_CREATED,
        progress=85, device_id=device_id,
    )
    workflow = svc.transition_to(
        workflow.id, WorkflowState.AI_CHECK,
        progress=90,
    )

    # Check AI readiness
    try:
        from services.ai_readiness import get_readiness_engine
        readiness = await get_readiness_engine().check_readiness(device_id)
        ai_ready = readiness.ready if hasattr(readiness, 'ready') else False
    except Exception:
        ai_ready = True

    workflow = svc.transition_to(
        workflow.id, WorkflowState.READY,
        progress=95,
    )

    return {
        "success": True,
        "message": "Device twin created",
        "device_id": device_id,
        "workflow_id": workflow.id,
        "state": workflow.workflow_state,
        "progress": workflow.progress,
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

    svc = get_pairing_workflow_service()

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

            if device.serial:
                usb_session = db.query(USBSession).filter(
                    USBSession.user_id == user_id,
                    USBSession.serial == device.serial,
                ).first()
                if usb_session:
                    usb_session.status = "disconnected"
                    usb_session.disconnected_at = datetime.utcnow()
                    usb_session.updated_at = datetime.utcnow()

        # Cancel active workflow
        workflow = svc.get_active_workflow(user_id)
        if workflow:
            svc.transition_to(
                workflow.id, WorkflowState.CANCELLED,
                error_message="User disconnected device",
                connected=False, is_online=False,
            )

        db.commit()
    finally:
        db.close()

    return {
        "success": True,
        "message": "Device disconnected",
    }


# ==================== Pairing WebSocket for per-user events ====================

@router.websocket("/ws/pairing")
async def pairing_websocket(websocket: WebSocket):
    """WebSocket for real-time pairing workflow events per user.
    Frontend connects here to receive state machine transitions."""
    from services.websocket_service import get_websocket_manager
    from services.auth_service import get_auth_service

    await websocket.accept()

    mgr = get_websocket_manager()
    user_id = None

    try:
        # First message must contain auth token
        raw = await websocket.receive_text()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"type": raw}

        token = payload.get("token", "")
        if not token:
            await websocket.send_json({"event": "ERROR", "message": "Authentication required"})
            await websocket.close()
            return

        auth_service = get_auth_service()
        user_info = auth_service.validate_token(token)
        if not user_info:
            await websocket.send_json({"event": "ERROR", "message": "Invalid token"})
            await websocket.close()
            return

        user_id = user_info["user_id"]
        await mgr.connect(websocket, user_id)

        # Send current workflow state
        svc = get_pairing_workflow_service()
        status = svc.get_full_status(user_id)
        await websocket.send_json({
            "event": "STATE_SYNC",
            "data": status,
        })

        # Handle incoming messages
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                msg = {"type": raw}

            msg_type = msg.get("type", "ping")

            if msg_type == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            elif msg_type == "get_status":
                status = svc.get_full_status(user_id)
                await websocket.send_json({
                    "event": "STATE_SYNC",
                    "data": status,
                })
            elif msg_type == "cancel":
                svc.cancel_all_for_user(user_id, reason="User requested cancellation")
                await websocket.send_json({
                    "event": "CANCELLED",
                    "data": {"message": "Pairing cancelled"},
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Pairing WebSocket error: {e}")
    finally:
        if user_id and mgr:
            mgr.disconnect(websocket, user_id)


# ==================== Flutter Agent WebSocket ====================

@router.websocket("/ws/device")
async def device_websocket(websocket: WebSocket):
    """WebSocket for real-time device updates (battery, foreground, heartbeats, etc)"""
    from services.websocket_service import get_websocket_manager
    from services.heartbeat_service import get_heartbeat_service, HeartbeatData

    mgr = get_websocket_manager()
    await websocket.accept()

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

    try:
        from services.websocket_service import get_websocket_manager
        mgr = get_websocket_manager()
        import asyncio
        asyncio.ensure_future(mgr.send_personal_message({
            "event": "PERMISSIONS_UPDATED",
            "device_id": device_id,
            "permissions": permissions,
        }, device_id))
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Synced {len(permissions)} permissions",
    }
