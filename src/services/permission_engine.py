"""
APA-OS Permission Engine
Android permission management, sync, and status tracking
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Android permission mappings
ANDROID_PERMISSIONS = {
    "screen_capture": {
        "android_permission": "android.permission.FOREGROUND_SERVICE",
        "description": "Capture screen content for AI vision",
        "required": True,
    },
    "navigation": {
        "android_permission": "android.permission.SYSTEM_ALERT_WINDOW",
        "description": "Navigate and control device UI",
        "required": True,
    },
    "notifications": {
        "android_permission": "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
        "description": "Read and manage notifications",
        "required": True,
    },
    "files": {
        "android_permission": "android.permission.READ_EXTERNAL_STORAGE",
        "description": "Access device files and storage",
        "required": False,
    },
    "camera": {
        "android_permission": "android.permission.CAMERA",
        "description": "Access camera for visual AI",
        "required": False,
    },
    "microphone": {
        "android_permission": "android.permission.RECORD_AUDIO",
        "description": "Access microphone for voice commands",
        "required": False,
    },
    "contacts": {
        "android_permission": "android.permission.READ_CONTACTS",
        "description": "Read contacts for messaging",
        "required": False,
    },
    "sms": {
        "android_permission": "android.permission.READ_SMS",
        "description": "Read SMS messages",
        "required": False,
    },
    "phone": {
        "android_permission": "android.permission.CALL_PHONE",
        "description": "Make phone calls",
        "required": False,
    },
    "location": {
        "android_permission": "android.permission.ACCESS_FINE_LOCATION",
        "description": "Access device location",
        "required": False,
    },
    "accessibility": {
        "android_permission": "android.permission.BIND_ACCESSIBILITY_SERVICE",
        "description": "Accessibility service for UI control",
        "required": True,
    },
    "overlay": {
        "android_permission": "android.permission.SYSTEM_ALERT_WINDOW",
        "description": "Draw over other apps",
        "required": True,
    },
    "usage_stats": {
        "android_permission": "android.permission.PACKAGE_USAGE_STATS",
        "description": "Read app usage statistics",
        "required": False,
    },
    "battery_optimization": {
        "android_permission": "android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
        "description": "Disable battery optimization for always-on agent",
        "required": True,
    },
}


@dataclass
class PermissionStatus:
    """Permission status result"""
    name: str
    status: str  # granted, denied, pending, not_requested
    android_permission: str
    description: str
    required: bool
    granted_at: Optional[str] = None


@dataclass
class PermissionCheckResult:
    """Permission check result"""
    success: bool
    message: str
    permissions: List[PermissionStatus] = field(default_factory=list)
    all_granted: bool = False
    required_granted: bool = False
    missing_required: List[str] = field(default_factory=list)
    missing_optional: List[str] = field(default_factory=list)


class PermissionEngine:
    """Android permission management engine"""

    def __init__(self, adb_service=None):
        self._adb = adb_service

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    def request_permissions(
        self,
        device_id: str,
        user_id: str,
        permissions: List[str],
    ) -> PermissionCheckResult:
        """Request permissions for a device"""
        try:
            db = self._get_db()
            try:
                from database.auth_models import DevicePermission

                results = []
                for perm_name in permissions:
                    perm_config = ANDROID_PERMISSIONS.get(perm_name)
                    if not perm_config:
                        continue

                    existing = db.query(DevicePermission).filter(
                        DevicePermission.device_id == device_id,
                        DevicePermission.permission_name == perm_name,
                    ).first()

                    if existing:
                        existing.status = "pending"
                        existing.updated_at = datetime.utcnow()
                    else:
                        perm = DevicePermission(
                            device_id=device_id,
                            user_id=user_id,
                            permission_name=perm_name,
                            status="pending",
                            android_permission=perm_config["android_permission"],
                        )
                        db.add(perm)

                    results.append(PermissionStatus(
                        name=perm_name,
                        status="pending",
                        android_permission=perm_config["android_permission"],
                        description=perm_config["description"],
                        required=perm_config["required"],
                    ))

                db.commit()
            finally:
                db.close()

            logger.info(f"Permissions requested: {permissions} for device {device_id}")

            return PermissionCheckResult(
                success=True,
                message=f"Requested {len(permissions)} permissions",
                permissions=results,
            )
        except Exception as e:
            logger.error(f"Permission request failed: {e}")
            return PermissionCheckResult(success=False, message=str(e))

    def update_permission_status(
        self,
        device_id: str,
        permission_name: str,
        status: str,
    ) -> bool:
        """Update permission status after Android grant/deny"""
        try:
            db = self._get_db()
            try:
                from database.auth_models import DevicePermission

                perm = db.query(DevicePermission).filter(
                    DevicePermission.device_id == device_id,
                    DevicePermission.permission_name == permission_name,
                ).first()

                if not perm:
                    perm = DevicePermission(
                        device_id=device_id,
                        user_id="",
                        permission_name=permission_name,
                        status=status,
                    )
                    db.add(perm)
                else:
                    perm.status = status
                    if status == "granted":
                        perm.granted_at = datetime.utcnow()
                    elif status == "denied":
                        perm.denied_at = datetime.utcnow()
                    perm.updated_at = datetime.utcnow()

                db.commit()
                return True
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Permission update failed: {e}")
            return False

    def check_permissions(self, device_id: str) -> PermissionCheckResult:
        """Check all permissions for a device"""
        try:
            db = self._get_db()
            try:
                from database.auth_models import DevicePermission

                db_perms = db.query(DevicePermission).filter(
                    DevicePermission.device_id == device_id,
                ).all()

                perm_map = {p.permission_name: p.status.value if hasattr(p.status, 'value') else p.status for p in db_perms}

                results = []
                missing_required = []
                missing_optional = []

                for name, config in ANDROID_PERMISSIONS.items():
                    status = perm_map.get(name, "not_requested")
                    ps = PermissionStatus(
                        name=name,
                        status=status,
                        android_permission=config["android_permission"],
                        description=config["description"],
                        required=config["required"],
                    )
                    results.append(ps)

                    if status != "granted":
                        if config["required"]:
                            missing_required.append(name)
                        else:
                            missing_optional.append(name)

                all_granted = len(missing_required) == 0 and len(missing_optional) == 0
                required_granted = len(missing_required) == 0

                return PermissionCheckResult(
                    success=True,
                    message="Permissions checked",
                    permissions=results,
                    all_granted=all_granted,
                    required_granted=required_granted,
                    missing_required=missing_required,
                    missing_optional=missing_optional,
                )
            finally:
                db.close()
        except Exception as e:
            return PermissionCheckResult(success=False, message=str(e))

    def get_permission_summary(self, device_id: str) -> Dict[str, Any]:
        """Get permission summary for a device"""
        result = self.check_permissions(device_id)
        return {
            "device_id": device_id,
            "all_granted": result.all_granted,
            "required_granted": result.required_granted,
            "total": len(result.permissions),
            "granted": sum(1 for p in result.permissions if p.status == "granted"),
            "denied": sum(1 for p in result.permissions if p.status == "denied"),
            "pending": sum(1 for p in result.permissions if p.status == "pending"),
            "not_requested": sum(1 for p in result.permissions if p.status == "not_requested"),
            "missing_required": result.missing_required,
            "missing_optional": result.missing_optional,
            "permissions": [
                {"name": p.name, "status": p.status, "required": p.required}
                for p in result.permissions
            ],
        }

    def sync_permissions_from_device(self, device_id: str) -> PermissionCheckResult:
        """Sync permission status from actual Android device via ADB"""
        if not self._adb:
            return self.check_permissions(device_id)

        # This would check actual Android permission status via ADB
        # For now, return current database state
        return self.check_permissions(device_id)


# ==================== Singleton ====================

_permission_engine: Optional[PermissionEngine] = None


def get_permission_engine(adb_service=None) -> PermissionEngine:
    global _permission_engine
    if _permission_engine is None:
        _permission_engine = PermissionEngine(adb_service)
    return _permission_engine
