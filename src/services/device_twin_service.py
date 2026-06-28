"""
APA-OS Device Twin Service
Creates and manages the digital twin representation of paired Android devices
"""

import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeviceTwinData:
    manufacturer: str = ""
    model: str = ""
    brand: str = ""
    android_version: str = ""
    sdk_version: int = 0
    build_number: str = ""
    cpu_abi: str = ""
    ram_total_gb: float = 0.0
    storage_total_gb: float = 0.0
    screen_width: int = 0
    screen_height: int = 0
    screen_density: int = 0
    installed_apps_count: int = 0
    capabilities: List[str] = field(default_factory=list)
    permissions: Dict[str, str] = field(default_factory=dict)
    security_patch: str = ""


class DeviceTwinService:
    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    def create_or_update_twin(self, device_id: str, user_id: str, data: DeviceTwinData) -> Dict[str, Any]:
        """Create or update the digital twin for a device"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceTwin, RegisteredDevice

            existing = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()

            cap_list = data.capabilities or []
            perm_dict = data.permissions or {}

            # Calculate scores
            health_score = self._calculate_health_score(data)
            readiness_score = self._calculate_readiness_score(cap_list, perm_dict)
            trust_score = 0.75  # Base trust, updated after trust gestures
            ai_ready = readiness_score >= 80.0

            twin_data = {
                "manufacturer": data.manufacturer,
                "model": data.model,
                "brand": data.brand,
                "android_version": data.android_version,
                "sdk_version": data.sdk_version,
                "build_number": data.build_number,
                "cpu_abi": data.cpu_abi,
                "ram_total_gb": data.ram_total_gb,
                "storage_total_gb": data.storage_total_gb,
                "screen_width": data.screen_width,
                "screen_height": data.screen_height,
                "screen_density": data.screen_density,
                "installed_apps_count": data.installed_apps_count,
                "capabilities": cap_list,
                "permissions": perm_dict,
                "health_score": health_score,
                "readiness_score": readiness_score,
                "trust_score": trust_score,
                "ai_ready": ai_ready,
                "sync_state": "synced",
                "last_sync_at": datetime.utcnow(),
                "last_seen": datetime.utcnow(),
                "security_patch": data.security_patch,
            }

            if existing:
                for key, value in twin_data.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                twin_id = existing.id
            else:
                import uuid
                twin = DeviceTwin(
                    id=f"twn_{uuid.uuid4().hex[:12]}",
                    device_id=device_id,
                    user_id=user_id,
                    **twin_data,
                )
                db.add(twin)
                db.flush()
                twin_id = twin.id

            # Update device record
            device = db.query(RegisteredDevice).filter(
                RegisteredDevice.id == device_id
            ).first()
            if device:
                device.metadata_json = device.metadata_json or {}
                meta = device.metadata_json
                meta["twin_id"] = twin_id
                meta["readiness_score"] = readiness_score
                meta["ai_ready"] = ai_ready
                device.updated_at = datetime.utcnow()

            db.commit()
            logger.info(f"Device twin {'updated' if existing else 'created'}: {twin_id} for device {device_id}")
            return self.get_twin(device_id, user_id) or {}
        except Exception as e:
            db.rollback()
            logger.error(f"Device twin creation failed: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def get_twin(self, device_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the digital twin for a device"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceTwin
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id,
                DeviceTwin.user_id == user_id,
            ).first()
            if not twin:
                return None
            return {
                "id": twin.id,
                "device_id": twin.device_id,
                "manufacturer": twin.manufacturer,
                "model": twin.model,
                "brand": twin.brand,
                "android_version": twin.android_version,
                "sdk_version": twin.sdk_version,
                "build_number": twin.build_number,
                "cpu_abi": twin.cpu_abi,
                "ram_total_gb": twin.ram_total_gb,
                "storage_total_gb": twin.storage_total_gb,
                "screen_width": twin.screen_width,
                "screen_height": twin.screen_height,
                "screen_density": twin.screen_density,
                "installed_apps_count": twin.installed_apps_count,
                "capabilities": twin.capabilities,
                "permissions": twin.permissions,
                "health_score": twin.health_score,
                "trust_score": twin.trust_score,
                "readiness_score": twin.readiness_score,
                "ai_ready": twin.ai_ready,
                "sync_state": twin.sync_state,
                "last_sync_at": twin.last_sync_at.isoformat() if twin.last_sync_at else None,
                "last_seen": twin.last_seen.isoformat() if twin.last_seen else None,
                "created_at": twin.created_at.isoformat() if twin.created_at else None,
                "updated_at": twin.updated_at.isoformat() if twin.updated_at else None,
            }
        finally:
            db.close()

    def update_health_score(self, device_id: str, score: float):
        """Update device twin health score"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceTwin
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()
            if twin:
                twin.health_score = score
                twin.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def update_trust_score(self, device_id: str, score: float):
        """Update device twin trust score"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceTwin
            twin = db.query(DeviceTwin).filter(
                DeviceTwin.device_id == device_id
            ).first()
            if twin:
                twin.trust_score = score
                twin.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _calculate_health_score(self, data: DeviceTwinData) -> float:
        """Calculate device health score (0.0 - 1.0)"""
        score = 1.0

        # Battery health
        if hasattr(data, 'battery_percentage') and data.battery_percentage < 15:
            score -= 0.2
        return max(0.1, score)

    def _calculate_readiness_score(self, capabilities: List[str], permissions: Dict[str, str]) -> float:
        """Calculate AI readiness score (0.0 - 100.0)"""
        required_caps = {"adb", "screenshot", "navigation", "notification"}
        required_perms = {"screen_capture", "accessibility", "overlay", "notifications"}

        caps_present = required_caps.intersection(set(capabilities))
        perms_granted = {k for k, v in permissions.items() if v == "granted"}

        total_checks = len(required_caps) + len(required_perms)
        passed_checks = len(caps_present) + len(perms_granted.intersection(required_perms))

        return (passed_checks / total_checks) * 100.0 if total_checks > 0 else 0.0


_twin_service: Optional[DeviceTwinService] = None


def get_twin_service() -> DeviceTwinService:
    global _twin_service
    if _twin_service is None:
        _twin_service = DeviceTwinService()
    return _twin_service
