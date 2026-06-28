"""
APA-OS Pairing Workflow State Machine Service
Manages complete pairing lifecycle with state transitions, validation, and event emission
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from enum import Enum

from database.connection import get_db_session
from database.auth_models import PairingWorkflow, RegisteredDevice, TrustedDevice, USBSession

logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    IDLE = "IDLE"
    DISCOVERING = "DISCOVERING"
    DEVICE_FOUND = "DEVICE_FOUND"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    TRUST_PENDING = "TRUST_PENDING"
    TRUSTED = "TRUSTED"
    PERMISSION_SYNC = "PERMISSION_SYNC"
    REGISTERING = "REGISTERING"
    DEVICE_REGISTERED = "DEVICE_REGISTERED"
    DEVICE_TWIN_CREATED = "DEVICE_TWIN_CREATED"
    AI_CHECK = "AI_CHECK"
    READY = "READY"
    ACTIVE = "ACTIVE"

    USB_DISCONNECTED = "USB_DISCONNECTED"
    ADB_OFFLINE = "ADB_OFFLINE"
    ADB_UNAUTHORIZED = "ADB_UNAUTHORIZED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    TIMEOUT = "TIMEOUT"
    DEVICE_REMOVED = "DEVICE_REMOVED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    PAIRING_FAILED = "PAIRING_FAILED"
    CANCELLED = "CANCELLED"


# Progress values for each state
STATE_PROGRESS = {
    WorkflowState.IDLE: 0,
    WorkflowState.DISCOVERING: 5,
    WorkflowState.DEVICE_FOUND: 10,
    WorkflowState.CONNECTING: 20,
    WorkflowState.CONNECTED: 25,
    WorkflowState.VERIFYING: 35,
    WorkflowState.VERIFIED: 50,
    WorkflowState.TRUST_PENDING: 55,
    WorkflowState.TRUSTED: 60,
    WorkflowState.PERMISSION_SYNC: 65,
    WorkflowState.REGISTERING: 70,
    WorkflowState.DEVICE_REGISTERED: 75,
    WorkflowState.DEVICE_TWIN_CREATED: 85,
    WorkflowState.AI_CHECK: 90,
    WorkflowState.READY: 95,
    WorkflowState.ACTIVE: 100,
}

# Valid transitions map
VALID_TRANSITIONS = {
    WorkflowState.IDLE: {WorkflowState.DISCOVERING, WorkflowState.CANCELLED},
    WorkflowState.DISCOVERING: {WorkflowState.DEVICE_FOUND, WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.TIMEOUT, WorkflowState.PAIRING_FAILED},
    WorkflowState.DEVICE_FOUND: {WorkflowState.CONNECTING, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.CONNECTING: {WorkflowState.CONNECTED, WorkflowState.CANCELLED, WorkflowState.ADB_OFFLINE, WorkflowState.ADB_UNAUTHORIZED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.CONNECTED: {WorkflowState.VERIFYING, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.ADB_OFFLINE},
    WorkflowState.VERIFYING: {WorkflowState.VERIFIED, WorkflowState.VERIFICATION_FAILED, WorkflowState.CANCELLED, WorkflowState.TIMEOUT, WorkflowState.USB_DISCONNECTED, WorkflowState.ADB_OFFLINE},
    WorkflowState.VERIFIED: {WorkflowState.TRUST_PENDING, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED},
    WorkflowState.TRUST_PENDING: {WorkflowState.TRUSTED, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.TRUSTED: {WorkflowState.PERMISSION_SYNC, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED},
    WorkflowState.PERMISSION_SYNC: {WorkflowState.REGISTERING, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.REGISTERING: {WorkflowState.DEVICE_REGISTERED, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.DEVICE_REGISTERED: {WorkflowState.DEVICE_TWIN_CREATED, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED},
    WorkflowState.DEVICE_TWIN_CREATED: {WorkflowState.AI_CHECK, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED},
    WorkflowState.AI_CHECK: {WorkflowState.READY, WorkflowState.CANCELLED, WorkflowState.USB_DISCONNECTED, WorkflowState.PAIRING_FAILED},
    WorkflowState.READY: {WorkflowState.ACTIVE, WorkflowState.USB_DISCONNECTED, WorkflowState.CANCELLED, WorkflowState.DEVICE_REMOVED},
    WorkflowState.ACTIVE: {WorkflowState.USB_DISCONNECTED, WorkflowState.DEVICE_REMOVED, WorkflowState.SESSION_EXPIRED, WorkflowState.CANCELLED},
    # Error states can transition to IDLE (restart) or CANCELLED
    WorkflowState.USB_DISCONNECTED: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.ADB_OFFLINE: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.ADB_UNAUTHORIZED: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.VERIFICATION_FAILED: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.TIMEOUT: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.DEVICE_REMOVED: {WorkflowState.IDLE, WorkflowState.CANCELLED, WorkflowState.DISCOVERING},
    WorkflowState.SESSION_EXPIRED: {WorkflowState.IDLE, WorkflowState.CANCELLED},
    WorkflowState.PAIRING_FAILED: {WorkflowState.IDLE, WorkflowState.CANCELLED},
    WorkflowState.CANCELLED: {WorkflowState.IDLE},
}

# Terminal states (workflow is done)
TERMINAL_STATES = {
    WorkflowState.ACTIVE,
    WorkflowState.READY,
    WorkflowState.CANCELLED,
    WorkflowState.VERIFICATION_FAILED,
    WorkflowState.PAIRING_FAILED,
    WorkflowState.SESSION_EXPIRED,
    WorkflowState.TIMEOUT,
    WorkflowState.DEVICE_REMOVED,
}

# Error states that should show error UI
ERROR_STATES = {
    WorkflowState.USB_DISCONNECTED,
    WorkflowState.ADB_OFFLINE,
    WorkflowState.ADB_UNAUTHORIZED,
    WorkflowState.VERIFICATION_FAILED,
    WorkflowState.TIMEOUT,
    WorkflowState.DEVICE_REMOVED,
    WorkflowState.SESSION_EXPIRED,
    WorkflowState.PAIRING_FAILED,
}


class PairingWorkflowService:

    def __init__(self):
        self._ws_manager = None

    def _get_ws_manager(self):
        if self._ws_manager is None:
            from services.websocket_service import get_websocket_manager
            self._ws_manager = get_websocket_manager()
        return self._ws_manager

    def _emit_event(self, user_id: str, event: str, data: dict):
        ws = self._get_ws_manager()
        import asyncio
        asyncio.ensure_future(ws.send_personal_message({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }, user_id))

    def get_or_create_workflow(self, user_id: str, serial: Optional[str] = None) -> PairingWorkflow:
        """Get active workflow or create a new one. Cancels any existing active workflow."""
        db = get_db_session()
        try:
            # Cancel any other active workflows for this user (only one at a time)
            active_workflows = db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.workflow_state.notin_([s.value for s in TERMINAL_STATES]),
            ).all()
            for wf in active_workflows:
                prev_state = wf.workflow_state
                wf.workflow_state = WorkflowState.CANCELLED.value
                wf.error_message = "Cancelled by new pairing session"
                wf.completed_at = datetime.utcnow()
                wf.updated_at = datetime.utcnow()
                self._emit_event(user_id, "SESSION_CANCELLED", {
                    "previous_workflow_id": wf.id,
                    "previous_state": prev_state,
                    "reason": "New pairing session started",
                })

            # Create new workflow
            workflow = PairingWorkflow(
                id=f"pwf_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                workflow_state=WorkflowState.IDLE.value,
                pairing_type="usb",
                serial=serial,
            )
            db.add(workflow)
            db.commit()
            db.refresh(workflow)
            return workflow
        finally:
            db.close()

    def get_active_workflow(self, user_id: str) -> Optional[PairingWorkflow]:
        """Get the currently active (non-terminal) workflow for a user."""
        db = get_db_session()
        try:
            return db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.workflow_state.notin_([s.value for s in TERMINAL_STATES]),
            ).order_by(PairingWorkflow.started_at.desc()).first()
        finally:
            db.close()

    def get_workflow_by_id(self, workflow_id: str) -> Optional[PairingWorkflow]:
        db = get_db_session()
        try:
            return db.query(PairingWorkflow).filter(
                PairingWorkflow.id == workflow_id
            ).first()
        finally:
            db.close()

    def get_workflow_by_user_and_serial(self, user_id: str, serial: str) -> Optional[PairingWorkflow]:
        db = get_db_session()
        try:
            return db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.serial == serial,
            ).order_by(PairingWorkflow.started_at.desc()).first()
        finally:
            db.close()

    def transition_to(
        self,
        workflow_id: str,
        new_state: WorkflowState,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        progress: Optional[int] = None,
        device_id: Optional[str] = None,
        fingerprint: Optional[str] = None,
        fingerprint_data: Optional[dict] = None,
        serial: Optional[str] = None,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        android_version: Optional[str] = None,
        connected: Optional[bool] = None,
        is_online: Optional[bool] = None,
    ) -> Optional[PairingWorkflow]:
        """Transition workflow to a new state with validation."""
        db = get_db_session()
        try:
            workflow = db.query(PairingWorkflow).filter(
                PairingWorkflow.id == workflow_id
            ).first()
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found for transition to {new_state.value}")
                return None

            old_state = workflow.workflow_state
            old_state_enum = WorkflowState(old_state)

            # Validate transition
            if new_state not in VALID_TRANSITIONS.get(old_state_enum, set()):
                logger.warning(
                    f"Invalid transition from {old_state} to {new_state.value} for workflow {workflow_id}"
                )
                workflow.error_message = f"Invalid transition: {old_state} -> {new_state.value}"
                workflow.error_code = "INVALID_TRANSITION"
                db.commit()
                return workflow

            # Update state
            workflow.workflow_state = new_state.value
            workflow.updated_at = datetime.utcnow()

            if progress is not None:
                workflow.progress = progress
            elif new_state in STATE_PROGRESS:
                workflow.progress = STATE_PROGRESS[new_state]

            if error_message:
                workflow.error_message = error_message
            if error_code:
                workflow.error_code = error_code
            if device_id:
                workflow.device_id = device_id
            if fingerprint:
                workflow.device_fingerprint = fingerprint
            if fingerprint_data:
                workflow.fingerprint_data = fingerprint_data
            if serial:
                workflow.serial = serial
            if manufacturer:
                workflow.manufacturer = manufacturer
            if model:
                workflow.model = model
            if android_version:
                workflow.android_version = android_version
            if connected is not None:
                workflow.connected = connected
            if is_online is not None:
                workflow.is_online = is_online

            # Set step timestamps
            now = datetime.utcnow()
            if new_state == WorkflowState.DEVICE_FOUND:
                workflow.discovered_at = now
            elif new_state == WorkflowState.CONNECTED:
                workflow.connected_at = now
            elif new_state == WorkflowState.VERIFIED:
                workflow.verified_at = now
            elif new_state == WorkflowState.TRUSTED:
                workflow.trusted_at = now
            elif new_state == WorkflowState.PERMISSION_SYNC:
                workflow.permissions_at = now
            elif new_state == WorkflowState.DEVICE_REGISTERED:
                workflow.registered_at = now
            elif new_state == WorkflowState.DEVICE_TWIN_CREATED:
                workflow.twin_created_at = now
            elif new_state in (WorkflowState.READY, WorkflowState.ACTIVE):
                workflow.ready_at = now

            # Set completed_at for terminal states
            if new_state in TERMINAL_STATES:
                workflow.completed_at = now

            db.commit()
            db.refresh(workflow)

            # Emit WebSocket event
            event_name = self._state_to_event(new_state)
            self._emit_event(workflow.user_id, event_name, self._workflow_to_dict(workflow))

            logger.info(f"Workflow {workflow_id}: {old_state} -> {new_state.value}")
            return workflow
        finally:
            db.close()

    def mark_disconnected(self, user_id: str, serial: str):
        """Mark all workflows for this user/device as disconnected."""
        db = get_db_session()
        try:
            workflows = db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.serial == serial,
                PairingWorkflow.workflow_state.notin_([s.value for s in TERMINAL_STATES]),
            ).all()
            for wf in workflows:
                old_state = wf.workflow_state
                wf.workflow_state = WorkflowState.USB_DISCONNECTED.value
                wf.connected = False
                wf.is_online = False
                wf.error_message = "USB device disconnected"
                wf.updated_at = datetime.utcnow()
                wf.completed_at = datetime.utcnow()
                self._emit_event(wf.user_id, "USB_DISCONNECTED", self._workflow_to_dict(wf))

            # Update USB sessions
            sessions = db.query(USBSession).filter(
                USBSession.user_id == user_id,
                USBSession.serial == serial,
            ).all()
            for s in sessions:
                s.status = "disconnected"
                s.disconnected_at = datetime.utcnow()
                s.updated_at = datetime.utcnow()

            # Mark registered devices as offline
            devices = db.query(RegisteredDevice).filter(
                RegisteredDevice.user_id == user_id,
                RegisteredDevice.serial == serial,
            ).all()
            for d in devices:
                d.is_online = False
                d.updated_at = datetime.utcnow()

            db.commit()
        finally:
            db.close()

    def cancel_all_for_user(self, user_id: str, reason: str = "User logout"):
        """Cancel all active workflows for a user (used on logout)."""
        db = get_db_session()
        try:
            workflows = db.query(PairingWorkflow).filter(
                PairingWorkflow.user_id == user_id,
                PairingWorkflow.workflow_state.notin_([s.value for s in TERMINAL_STATES]),
            ).all()
            for wf in workflows:
                wf.workflow_state = WorkflowState.CANCELLED.value
                wf.connected = False
                wf.is_online = False
                wf.error_message = reason
                wf.completed_at = datetime.utcnow()
                wf.updated_at = datetime.utcnow()

            # Also mark devices as offline
            devices = db.query(RegisteredDevice).filter(
                RegisteredDevice.user_id == user_id,
            ).all()
            for d in devices:
                d.is_online = False
                d.updated_at = datetime.utcnow()

            # Mark USB sessions as disconnected
            sessions = db.query(USBSession).filter(
                USBSession.user_id == user_id,
            ).all()
            for s in sessions:
                s.status = "disconnected"
                s.updated_at = datetime.utcnow()

            db.commit()
        finally:
            db.close()

    def is_device_connected_via_adb(self, serial: str) -> bool:
        """Check if device is still connected via ADB."""
        try:
            from services.adb_service import get_adb_service, find_adb_binary
            import asyncio
            adb = get_adb_service(find_adb_binary())
            loop = asyncio.new_event_loop()
            try:
                devices = loop.run_until_complete(adb.list_devices())
            finally:
                loop.close()
            for d in devices:
                if d.get("serial") == serial and d.get("state") == "device":
                    return True
            return False
        except Exception as e:
            logger.error(f"ADB check failed for {serial}: {e}")
            return False

    def get_full_status(self, user_id: str) -> dict:
        """Get complete pairing status for a user."""
        db = get_db_session()
        try:
            workflow = self.get_active_workflow(user_id)

            devices = db.query(RegisteredDevice).filter(
                RegisteredDevice.user_id == user_id,
            ).order_by(RegisteredDevice.last_seen.desc()).all()

            trusted = db.query(TrustedDevice).filter(
                TrustedDevice.user_id == user_id,
                TrustedDevice.revoked_at == None,
            ).count()

            return {
                "workflow_id": workflow.id if workflow else None,
                "state": workflow.workflow_state if workflow else WorkflowState.IDLE.value,
                "progress": workflow.progress if workflow else 0,
                "message": self._get_state_message(workflow.workflow_state if workflow else WorkflowState.IDLE.value),
                "has_active_session": workflow is not None,
                "device_id": workflow.device_id if workflow else None,
                "serial": workflow.serial if workflow else None,
                "manufacturer": workflow.manufacturer if workflow else None,
                "model": workflow.model if workflow else None,
                "connected": workflow.connected if workflow else False,
                "error_message": workflow.error_message if workflow else None,
                "error_code": workflow.error_code if workflow else None,
                "paired": len(devices) > 0,
                "trusted": trusted > 0,
                "device_count": len(devices),
                "devices": [
                    {
                        "id": d.id,
                        "name": d.device_name,
                        "model": d.model,
                        "manufacturer": d.manufacturer,
                        "serial": d.serial,
                        "is_online": d.is_online,
                        "connection_type": d.connection_type,
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                    }
                    for d in devices
                ],
            }
        finally:
            db.close()

    def _state_to_event(self, state: WorkflowState) -> str:
        mapping = {
            WorkflowState.DISCOVERING: "DISCOVERING",
            WorkflowState.DEVICE_FOUND: "DEVICE_FOUND",
            WorkflowState.CONNECTING: "CONNECTING",
            WorkflowState.CONNECTED: "CONNECTED",
            WorkflowState.VERIFYING: "VERIFYING",
            WorkflowState.VERIFIED: "VERIFIED",
            WorkflowState.TRUSTED: "TRUSTED",
            WorkflowState.PERMISSION_SYNC: "PERMISSIONS",
            WorkflowState.REGISTERING: "REGISTERING",
            WorkflowState.DEVICE_REGISTERED: "DEVICE_REGISTERED",
            WorkflowState.DEVICE_TWIN_CREATED: "DEVICE_TWIN_CREATED",
            WorkflowState.AI_CHECK: "AI_CHECK",
            WorkflowState.READY: "READY",
            WorkflowState.ACTIVE: "ACTIVE",
            WorkflowState.USB_DISCONNECTED: "USB_DISCONNECTED",
            WorkflowState.TIMEOUT: "TIMEOUT",
            WorkflowState.VERIFICATION_FAILED: "VERIFICATION_FAILED",
            WorkflowState.PAIRING_FAILED: "PAIRING_FAILED",
            WorkflowState.CANCELLED: "CANCELLED",
            WorkflowState.DEVICE_REMOVED: "DEVICE_REMOVED",
        }
        return mapping.get(state, state.value)

    def _get_state_message(self, state: str) -> str:
        messages = {
            "IDLE": "Ready to pair",
            "DISCOVERING": "Scanning for USB devices...",
            "DEVICE_FOUND": "Device detected",
            "CONNECTING": "Establishing connection...",
            "CONNECTED": "Device connected",
            "VERIFYING": "Verifying device identity...",
            "VERIFIED": "Device verified",
            "TRUST_PENDING": "Waiting for trust confirmation...",
            "TRUSTED": "Device trusted",
            "PERMISSION_SYNC": "Synchronizing permissions...",
            "REGISTERING": "Registering device...",
            "DEVICE_REGISTERED": "Device registered",
            "DEVICE_TWIN_CREATED": "Device twin created",
            "AI_CHECK": "Checking AI readiness...",
            "READY": "Device ready",
            "ACTIVE": "Device active",
            "USB_DISCONNECTED": "USB device disconnected",
            "ADB_OFFLINE": "ADB connection offline",
            "ADB_UNAUTHORIZED": "ADB authorization required",
            "VERIFICATION_FAILED": "Device verification failed",
            "TIMEOUT": "Operation timed out",
            "DEVICE_REMOVED": "Device removed",
            "SESSION_EXPIRED": "Session expired",
            "PAIRING_FAILED": "Pairing failed",
            "CANCELLED": "Pairing cancelled",
        }
        return messages.get(state, state)

    def _workflow_to_dict(self, workflow: PairingWorkflow) -> dict:
        return {
            "workflow_id": workflow.id,
            "state": workflow.workflow_state,
            "progress": workflow.progress,
            "message": self._get_state_message(workflow.workflow_state),
            "device_id": workflow.device_id,
            "serial": workflow.serial,
            "manufacturer": workflow.manufacturer,
            "model": workflow.model,
            "connected": workflow.connected,
            "error_message": workflow.error_message,
            "error_code": workflow.error_code,
        }


_singleton = None


def get_pairing_workflow_service() -> PairingWorkflowService:
    global _singleton
    if _singleton is None:
        _singleton = PairingWorkflowService()
    return _singleton
