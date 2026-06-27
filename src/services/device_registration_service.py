"""
APA-OS Device Registration & Permission Service
Handles device onboarding and permission management
"""

import logging
import secrets
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.auth_models import RegisteredDevice, DevicePermission, PermissionStatus, DeviceCapability, CapabilityStatus
from config import Config

logger = logging.getLogger(__name__)

class RegistrationResult:
    def __init__(self, success: bool = True, message: str = "",
                 device_id: str = None, readiness_score: float = None):
        self.success = success
        self.message = message
        self.device_id = device_id
        self.readiness_score = readiness_score

class DeviceRegistrationService:
    def _get_session(self) -> Session:
        return get_db_session()

    def register_device(self, user_id: str, device_data: Dict[str, Any]) -> RegistrationResult:
        """
        Registers a device with complete hardware and software metadata
        """
        session = self._get_session()
        try:
            # Create RegisteredDevice record
            device = RegisteredDevice(
                id=f"dev_{secrets.token_urlsafe(6)}",
                user_id=user_id,
                device_name=device_data.get("device_name", "Android Device"),
                device_type="android",
                manufacturer=device_data.get("manufacturer"),
                model=device_data.get("model"),
                android_version=device_data.get("android_version"),
                battery_level=device_data.get("battery"),
                connection_type=device_data.get("connection_type", "wireless"),
                connection_ip=device_data.get("ip"),
                is_online=True,
                last_seen=datetime.utcnow(),
                metadata_json={
                    "storage": device_data.get("storage"),
                    "ram": device_data.get("ram"),
                    "installed_apps_count": device_data.get("installed_apps_count"),
                    "capabilities": device_data.get("capabilities", [])
                },
                created_at=datetime.utcnow()
            )
            session.add(device)
            session.flush()

            # Initialize default capabilities based on data
            capabilities = device_data.get("capabilities", [])
            for cap in capabilities:
                capability = DeviceCapability(
                    id=f"cap_{secrets.token_urlsafe(6)}",
                    device_id=device.id,
                    capability_name=cap,
                    status=CapabilityStatus.READY,
                    score=1.0,
                    created_at=datetime.utcnow()
                )
                session.add(capability)

            session.commit()
            return RegistrationResult(success=True, message="Device registered successfully", device_id=device.id)
        except Exception as e:
            session.rollback()
            logger.error(f"Device registration error: {e}")
            return RegistrationResult(success=False, message=str(e))
        finally:
            session.close()

    def update_permission(self, user_id: str, device_id: str, permission_name: str, status: str) -> bool:
        """
        Store permission status for a specific device
        """
        session = self._get_session()
        try:
            perm_status = PermissionStatus[status.upper()] if status.upper() in PermissionStatus.__members__ else PermissionStatus.NOT_REQUESTED

            permission = session.query(DevicePermission).filter(
                DevicePermission.device_id == device_id,
                DevicePermission.permission_name == permission_name
            ).first()

            if not permission:
                permission = DevicePermission(
                    id=f"prm_{secrets.token_urlsafe(6)}",
                    device_id=device_id,
                    user_id=user_id,
                    permission_name=permission_name,
                    status=perm_status,
                    created_at=datetime.utcnow()
                )
                session.add(permission)
            else:
                permission.status = perm_status
                permission.updated_at = datetime.utcnow()

            if perm_status == PermissionStatus.GRANTED:
                permission.granted_at = datetime.utcnow()
            elif perm_status == PermissionStatus.DENIED:
                permission.denied_at = datetime.utcnow()

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Permission update error: {e}")
            return False
        finally:
            session.close()

def get_registration_service():
    return DeviceRegistrationService()
