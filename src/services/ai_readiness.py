"""
APA-OS AI Readiness Engine
Complete device capability scanning and diagnostics
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CapabilityCheck:
    """Individual capability check result"""
    name: str
    status: str  # ready, not_ready, error
    score: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadinessResult:
    """Overall readiness check result"""
    success: bool
    ready: bool
    message: str
    score: float = 0.0
    capabilities: List[CapabilityCheck] = field(default_factory=list)
    ready_count: int = 0
    total_count: int = 0
    missing_capabilities: List[str] = field(default_factory=list)


class AIReadinessEngine:
    """Device AI readiness scanning and diagnostics"""

    def __init__(self, adb_service=None):
        self._adb = adb_service

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    async def check_readiness(self, device_id: str) -> ReadinessResult:
        """Run complete AI readiness check on device"""
        checks = []

        # 1. ADB Connection
        checks.append(await self._check_adb(device_id))

        # 2. Trust Verification
        checks.append(await self._check_trust(device_id))

        # 3. Battery Check
        checks.append(await self._check_battery(device_id))

        # 4. Screen State
        checks.append(await self._check_screen(device_id))

        # 5. Screenshot Capability
        checks.append(await self._check_screenshot(device_id))

        # 6. OCR Capability
        checks.append(await self._check_ocr(device_id))

        # 7. Navigation (Accessibility)
        checks.append(await self._check_navigation(device_id))

        # 8. Notifications
        checks.append(await self._check_notifications(device_id))

        # 9. File Access
        checks.append(await self._check_file_access(device_id))

        # 10. Agent Installation
        checks.append(await self._check_agent(device_id))

        # 11. Network
        checks.append(await self._check_network(device_id))

        # 12. Memory
        checks.append(await self._check_memory(device_id))

        # Calculate overall readiness
        ready_count = sum(1 for c in checks if c.status == "ready")
        total_count = len(checks)
        score = ready_count / total_count if total_count > 0 else 0.0
        missing = [c.name for c in checks if c.status != "ready"]

        is_ready = score >= 0.7  # 70% threshold

        # Store results
        await self._store_results(device_id, checks)

        # Create capability records
        self._update_capability_records(device_id, checks)

        logger.info(f"AI readiness: {device_id} = {'READY' if is_ready else 'NOT READY'} ({score:.0%})")

        return ReadinessResult(
            success=True,
            ready=is_ready,
            message=f"Device is {'ready' if is_ready else 'not ready'} ({ready_count}/{total_count} capabilities)",
            score=score,
            capabilities=checks,
            ready_count=ready_count,
            total_count=total_count,
            missing_capabilities=missing,
        )

    async def _check_adb(self, device_id: str) -> CapabilityCheck:
        """Check ADB connectivity"""
        if not self._adb:
            return CapabilityCheck(name="adb", status="error", message="ADB not configured")

        try:
            devices = await self._adb.list_devices()
            connected = any(d.get("serial") == device_id for d in devices)
            return CapabilityCheck(
                name="adb",
                status="ready" if connected else "not_ready",
                score=1.0 if connected else 0.0,
                message="ADB connected" if connected else "Device not connected via ADB",
            )
        except Exception as e:
            return CapabilityCheck(name="adb", status="error", message=str(e))

    async def _check_trust(self, device_id: str) -> CapabilityCheck:
        """Check device trust status"""
        try:
            from services.trust_engine import get_trust_engine
            engine = get_trust_engine()
            # We need user_id - get from device record
            db = self._get_db()
            try:
                from database.auth_models import RegisteredDevice
                device = db.query(RegisteredDevice).filter(RegisteredDevice.id == device_id).first()
                if not device:
                    return CapabilityCheck(name="trust", status="not_ready", message="Device not registered")

                result = engine.verify_trust(device_id, device.user_id)
                return CapabilityCheck(
                    name="trust",
                    status="ready" if result.success else "not_ready",
                    score=1.0 if result.success else 0.0,
                    message=result.message,
                    details={"trust_level": result.trust_level},
                )
            finally:
                db.close()
        except Exception as e:
            return CapabilityCheck(name="trust", status="error", message=str(e))

    async def _check_battery(self, device_id: str) -> CapabilityCheck:
        """Check battery level"""
        if not self._adb:
            return CapabilityCheck(name="battery", status="error", message="ADB not available")

        try:
            battery_output = await self._adb.shell(device_id, "dumpsys battery")
            level = 50  # default
            for line in (battery_output or "").split("\n"):
                if "level:" in line:
                    level = int(line.split(":")[-1].strip())
                    break

            status = "ready" if level > 10 else "not_ready"
            return CapabilityCheck(
                name="battery",
                status=status,
                score=level / 100.0,
                message=f"Battery at {level}%",
                details={"level": level, "charging": "AC powered" in (battery_output or "")},
            )
        except Exception as e:
            return CapabilityCheck(name="battery", status="error", message=str(e))

    async def _check_screen(self, device_id: str) -> CapabilityCheck:
        """Check screen state"""
        if not self._adb:
            return CapabilityCheck(name="screen", status="error", message="ADB not available")

        try:
            screen_output = await self._adb.shell(device_id, "dumpsys power | grep 'Display Power'")
            is_on = "ON" in (screen_output or "").upper()
            return CapabilityCheck(
                name="screen",
                status="ready" if is_on else "not_ready",
                score=1.0 if is_on else 0.0,
                message="Screen is on" if is_on else "Screen is off",
                details={"screen_on": is_on},
            )
        except Exception as e:
            return CapabilityCheck(name="screen", status="error", message=str(e))

    async def _check_screenshot(self, device_id: str) -> CapabilityCheck:
        """Check screenshot capability"""
        if not self._adb:
            return CapabilityCheck(name="screenshot", status="error", message="ADB not available")

        try:
            from vision.screen_capture import get_screen_capture_service
            result = await get_screen_capture_service().capture_from_adb(device_id)
            return CapabilityCheck(
                name="screenshot",
                status="ready" if result.success else "not_ready",
                score=1.0 if result.success else 0.0,
                message="Screenshot capture works" if result.success else f"Screenshot failed: {result.error}",
                details={"filepath": result.filepath} if result.success else {},
            )
        except Exception as e:
            return CapabilityCheck(name="screenshot", status="error", message=str(e))

    async def _check_ocr(self, device_id: str) -> CapabilityCheck:
        """Check OCR capability"""
        try:
            from vision.ocr_service import get_ocr_service
            import numpy as np
            # Create a test image
            test_img = np.ones((100, 300, 3), dtype=np.uint8) * 255
            result = await get_ocr_service().extract_text(test_img)
            return CapabilityCheck(
                name="ocr",
                status="ready",
                score=1.0,
                message="OCR engine available",
            )
        except Exception as e:
            return CapabilityCheck(name="ocr", status="error", message=f"OCR not available: {str(e)}")

    async def _check_navigation(self, device_id: str) -> CapabilityCheck:
        """Check navigation (accessibility) capability"""
        if not self._adb:
            return CapabilityCheck(name="navigation", status="error", message="ADB not available")

        try:
            # Test basic ADB input
            result = await self._adb.shell(device_id, "input keyevent 3")  # HOME key
            return CapabilityCheck(
                name="navigation",
                status="ready",
                score=1.0,
                message="Navigation via ADB available",
            )
        except Exception as e:
            return CapabilityCheck(name="navigation", status="error", message=str(e))

    async def _check_notifications(self, device_id: str) -> CapabilityCheck:
        """Check notification access"""
        if not self._adb:
            return CapabilityCheck(name="notifications", status="error", message="ADB not available")

        try:
            result = await self._adb.shell(device_id, "dumpsys notification --noredact | head -5")
            has_access = bool(result and "Notification" in result)
            return CapabilityCheck(
                name="notifications",
                status="ready" if has_access else "not_ready",
                score=1.0 if has_access else 0.0,
                message="Notification access available" if has_access else "Notification access not granted",
            )
        except Exception as e:
            return CapabilityCheck(name="notifications", status="not_ready", message=str(e))

    async def _check_file_access(self, device_id: str) -> CapabilityCheck:
        """Check file access"""
        if not self._adb:
            return CapabilityCheck(name="files", status="error", message="ADB not available")

        try:
            result = await self._adb.shell(device_id, "ls /sdcard/ | head -5")
            has_access = bool(result)
            return CapabilityCheck(
                name="files",
                status="ready" if has_access else "not_ready",
                score=1.0 if has_access else 0.0,
                message="File access available" if has_access else "File access denied",
            )
        except Exception as e:
            return CapabilityCheck(name="files", status="not_ready", message=str(e))

    async def _check_agent(self, device_id: str) -> CapabilityCheck:
        """Check APA agent installation"""
        if not self._adb:
            return CapabilityCheck(name="agent", status="error", message="ADB not available")

        try:
            ps = await self._adb.shell(device_id, "ps | grep -i apaos")
            installed = bool(ps and "apaos" in ps.lower())
            return CapabilityCheck(
                name="agent",
                status="ready" if installed else "not_ready",
                score=1.0 if installed else 0.0,
                message="APA Agent installed" if installed else "APA Agent not installed",
                details={"installed": installed},
            )
        except Exception as e:
            return CapabilityCheck(name="agent", status="not_ready", message=str(e))

    async def _check_network(self, device_id: str) -> CapabilityCheck:
        """Check network connectivity"""
        if not self._adb:
            return CapabilityCheck(name="network", status="error", message="ADB not available")

        try:
            ping = await self._adb.shell(device_id, "ping -c 1 -W 2 8.8.8.8")
            connected = "1 received" in (ping or "")
            return CapabilityCheck(
                name="network",
                status="ready" if connected else "not_ready",
                score=1.0 if connected else 0.0,
                message="Network connected" if connected else "No network",
            )
        except Exception as e:
            return CapabilityCheck(name="network", status="error", message=str(e))

    async def _check_memory(self, device_id: str) -> CapabilityCheck:
        """Check device memory"""
        if not self._adb:
            return CapabilityCheck(name="memory", status="error", message="ADB not available")

        try:
            meminfo = await self._adb.shell(device_id, "cat /proc/meminfo | head -3")
            return CapabilityCheck(
                name="memory",
                status="ready",
                score=1.0,
                message="Memory accessible",
                details={"raw": meminfo[:200] if meminfo else ""},
            )
        except Exception as e:
            return CapabilityCheck(name="memory", status="error", message=str(e))

    async def _store_results(self, device_id: str, checks: List[CapabilityCheck]):
        """Store readiness results"""
        # Emit event
        try:
            from console.event_stream import get_event_manager, EventType, EventSeverity
            manager = get_event_manager()
            await manager.emit(
                workflow_id=f"readiness_{device_id}",
                event_type=EventType.DEVICE_CAPABILITY_DETECTED,
                payload={
                    "device_id": device_id,
                    "capabilities": [
                        {"name": c.name, "status": c.status, "score": c.score}
                        for c in checks
                    ],
                },
                source="ai_readiness",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
        except Exception:
            pass

    def _update_capability_records(self, device_id: str, checks: List[CapabilityCheck]):
        """Update capability records in database"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceCapability

            for check in checks:
                existing = db.query(DeviceCapability).filter(
                    DeviceCapability.device_id == device_id,
                    DeviceCapability.capability_name == check.name,
                ).first()

                if existing:
                    existing.status = check.status
                    existing.score = check.score
                    existing.details = check.details
                    existing.last_tested_at = datetime.utcnow()
                    existing.updated_at = datetime.utcnow()
                else:
                    cap = DeviceCapability(
                        device_id=device_id,
                        capability_name=check.name,
                        status=check.status,
                        score=check.score,
                        details=check.details,
                        last_tested_at=datetime.utcnow(),
                    )
                    db.add(cap)

            db.commit()
        except Exception as e:
            logger.warning(f"Failed to store capability records: {e}")
            db.rollback()
        finally:
            db.close()


# ==================== Singleton ====================

_readiness_engine: Optional[AIReadinessEngine] = None


def get_readiness_engine(adb_service=None) -> AIReadinessEngine:
    global _readiness_engine
    if _readiness_engine is None:
        _readiness_engine = AIReadinessEngine(adb_service)
    return _readiness_engine
