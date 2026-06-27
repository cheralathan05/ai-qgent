"""
APA-OS AI Readiness Service
Calculates readiness score based on device capabilities and permissions
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.auth_models import DevicePermission, PermissionStatus, DeviceCapability, CapabilityStatus
from config import Config

logger = logging.getLogger(__name__)

class ReadinessResult:
    def __init__(self, ready: bool, score: float, missing_capabilities: List[str], message: str):
        self.ready = ready
        self.score = score
        self.missing_capabilities = missing_capabilities
        self.message = message

class AIReadinessService:
    # Core capabilities required for full AI operation
    REQUIRED_CAPABILITIES = [
        "adb",
        "ocr",
        "screenshot",
        "navigation"
    ]

    # Permissions required for full AI operation
    REQUIRED_PERMISSIONS = [
        "screen_capture",
        "navigation",
        "notifications",
        "overlay"
    ]

    def _get_session(self) -> Session:
        return get_db_session()

    async def check_readiness(self, device_id: str) -> ReadinessResult:
        """
        Analyze device capabilities and permissions to determine AI readiness score
        """
        session = self._get_session()
        try:
            # 1. Check Capabilities
            capabilities = session.query(DeviceCapability).filter(
                DeviceCapability.device_id == device_id
            ).all()
            cap_map = {c.capability_name: c.status for c in capabilities}

            missing_caps = [cap for cap in self.REQUIRED_CAPABILITIES if cap not in cap_map or cap_map[cap] != CapabilityStatus.READY]

            # 2. Check Permissions
            permissions = session.query(DevicePermission).filter(
                DevicePermission.device_id == device_id
            ).all()
            perm_map = {p.permission_name: p.status for p in permissions}

            missing_perms = [perm for perm in self.REQUIRED_PERMISSIONS if perm not in perm_map or perm_map[perm] != PermissionStatus.GRANTED]

            # Calculate Score
            total_checks = len(self.REQUIRED_CAPABILITIES) + len(self.REQUIRED_PERMISSIONS)
            passed_checks = total_checks - (len(missing_caps) + len(missing_perms))
            score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

            ready = len(missing_caps) == 0 and len(missing_perms) == 0

            all_missing = missing_caps + missing_perms
            message = "Device is fully ready" if ready else f"Missing {len(all_missing)} requirements"

            return ReadinessResult(
                ready=ready,
                score=round(score, 1),
                missing_capabilities=all_missing,
                message=message
            )
        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            return ReadinessResult(ready=False, score=0.0, missing_capabilities=["error"], message=str(e))
        finally:
            session.close()

def get_readiness_engine():
    return AIReadinessService()
