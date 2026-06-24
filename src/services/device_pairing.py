"""
APA-OS Device Pairing Engine
Complete device lifecycle: USB, Wireless ADB, QR code pairing with trust verification
"""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Device information collected during pairing"""
    serial: str = ""
    model: str = ""
    manufacturer: str = ""
    android_version: str = ""
    screen_width: int = 0
    screen_height: int = 0
    battery_level: int = 0
    connection_type: str = ""
    connection_ip: str = ""
    connection_port: int = 0
    device_name: str = ""
    agent_installed: bool = False
    agent_version: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serial": self.serial,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "android_version": self.android_version,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "battery_level": self.battery_level,
            "connection_type": self.connection_type,
            "connection_ip": self.connection_ip,
            "connection_port": self.connection_port,
            "device_name": self.device_name,
            "agent_installed": self.agent_installed,
            "agent_version": self.agent_version,
        }


@dataclass
class PairingResult:
    """Pairing operation result"""
    success: bool
    message: str
    device_id: Optional[str] = None
    pair_code: Optional[str] = None
    trust_code: Optional[str] = None
    device_info: Optional[DeviceInfo] = None
    session_id: Optional[str] = None


class DevicePairingEngine:
    """Complete device pairing engine supporting USB, Wireless ADB, and QR code"""

    def __init__(self, adb_service=None):
        self._adb = adb_service
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    # ==================== USB Pairing ====================

    async def discover_usb_devices(self) -> List[Dict[str, Any]]:
        """Discover devices connected via USB using ADB"""
        if not self._adb:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb = get_adb_service(find_adb_binary())

        try:
            devices = await self._adb.list_devices()
            results = []
            for dev in devices:
                serial = dev.get("serial", "")
                info = await self._extract_device_info(serial)
                results.append({
                    "serial": serial,
                    "status": dev.get("state", "unknown"),
                    **info.to_dict(),
                })
            return results
        except Exception as e:
            logger.error(f"USB discovery failed: {e}")
            return []

    async def pair_usb(self, user_id: str, serial: str) -> PairingResult:
        """Pair device via USB connection"""
        try:
            if not self._adb:
                from services.adb_service import get_adb_service, find_adb_binary
                self._adb = get_adb_service(find_adb_binary())

            # Check if device is connected
            devices = await self._adb.list_devices()
            connected_serials = [d.get("serial") for d in devices]
            if serial not in connected_serials:
                return PairingResult(
                    success=False,
                    message=f"Device {serial} not connected via USB",
                )

            # Extract device info
            info = await self._extract_device_info(serial)
            info.connection_type = "usb"

            # Register device
            device_id = await self._register_device(user_id, info)

            # Create pairing session
            pair_code = generate_pair_code()
            session_id = self._create_pairing_session(
                user_id=user_id,
                pair_code=pair_code,
                pairing_type="usb",
                device_serial=serial,
                device_info=info.to_dict(),
            )

            # Mark as paired
            self._update_pairing_status(session_id, "paired")

            logger.info(f"USB pairing completed: {serial} for user {user_id}")

            return PairingResult(
                success=True,
                message="Device paired via USB",
                device_id=device_id,
                pair_code=pair_code,
                device_info=info,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"USB pairing failed: {e}")
            return PairingResult(success=False, message=f"USB pairing failed: {str(e)}")

    # ==================== Wireless ADB Pairing ====================

    async def pair_wireless(
        self,
        user_id: str,
        device_ip: str,
        port: int,
        pair_code: str,
    ) -> PairingResult:
        """Pair device via Wireless ADB"""
        try:
            if not self._adb:
                from services.adb_service import get_adb_service, find_adb_binary
                self._adb = get_adb_service(find_adb_binary())

            # ADB pair
            pair_address = f"{device_ip}:{port}"
            logger.info(f"Attempting wireless ADB pair: {pair_address}")

            pair_result = await self._adb.pair(pair_address, pair_code)
            if not pair_result:
                return PairingResult(
                    success=False,
                    message="ADB pair failed - check IP, port, and pairing code",
                )

            # ADB connect
            connect_result = await self._adb.connect(f"{device_ip}:{port}")
            if not connect_result:
                return PairingResult(
                    success=False,
                    message="ADB connect failed after pair",
                )

            # Get device serial
            devices = await self._adb.list_devices()
            serial = ""
            for dev in devices:
                if device_ip in dev.get("serial", ""):
                    serial = dev["serial"]
                    break
            if not serial and devices:
                serial = devices[-1]["serial"]

            # Extract device info
            info = await self._extract_device_info(serial)
            info.connection_type = "wireless"
            info.connection_ip = device_ip
            info.connection_port = port

            # Register device
            device_id = await self._register_device(user_id, info)

            # Create pairing session
            session_pair_code = generate_pair_code()
            session_id = self._create_pairing_session(
                user_id=user_id,
                pair_code=session_pair_code,
                pairing_type="wireless",
                device_serial=serial,
                device_ip=device_ip,
                device_port=port,
                device_info=info.to_dict(),
            )

            self._update_pairing_status(session_id, "paired")

            logger.info(f"Wireless pairing completed: {device_ip}:{port}")

            return PairingResult(
                success=True,
                message="Device paired via Wireless ADB",
                device_id=device_id,
                pair_code=session_pair_code,
                device_info=info,
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"Wireless pairing failed: {e}")
            return PairingResult(success=False, message=f"Wireless pairing failed: {str(e)}")

    # ==================== QR Code Pairing ====================

    def create_qr_session(self, user_id: str) -> PairingResult:
        """Create a QR pairing session for desktop"""
        pair_code = generate_pair_code()
        session_id = f"qr_{secrets.token_hex(8)}"
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        qr_data = {
            "pairId": session_id,
            "pairCode": pair_code,
            "type": "apaos_pair",
            "version": "1.0",
        }

        self._active_sessions[session_id] = {
            "user_id": user_id,
            "pair_code": pair_code,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "device_info": None,
        }

        # Store in database
        db = self._get_db()
        try:
            from database.auth_models import DevicePairingSession
            pairing = DevicePairingSession(
                id=session_id,
                user_id=user_id,
                pair_code=pair_code,
                pairing_type="qr",
                status="pending",
                expires_at=expires_at,
            )
            db.add(pairing)
            db.commit()
        finally:
            db.close()

        logger.info(f"QR session created: {session_id}")

        return PairingResult(
            success=True,
            message="QR pairing session created",
            pair_code=pair_code,
            session_id=session_id,
            device_info=DeviceInfo(metadata=qr_data),
        )

    async def handle_qr_scan(
        self,
        session_id: str,
        device_serial: str,
        device_info_dict: Dict[str, Any],
    ) -> PairingResult:
        """Handle QR scan from mobile agent"""
        session_data = self._active_sessions.get(session_id)
        if not session_data:
            return PairingResult(success=False, message="Invalid or expired QR session")

        if session_data["expires_at"] < datetime.utcnow():
            del self._active_sessions[session_id]
            return PairingResult(success=False, message="QR session expired")

        # Generate trust code for verification
        trust_code = generate_trust_code()
        session_data["trust_code"] = trust_code
        session_data["device_info"] = device_info_dict
        session_data["status"] = "scanned"

        # Update database
        db = self._get_db()
        try:
            from database.auth_models import DevicePairingSession
            pairing = db.query(DevicePairingSession).filter(
                DevicePairingSession.id == session_id
            ).first()
            if pairing:
                pairing.status = "scanned"
                pairing.device_serial = device_serial
                pairing.device_info = device_info_dict
                pairing.trust_code = trust_code
                db.commit()
        finally:
            db.close()

        logger.info(f"QR scanned for session: {session_id}")

        return PairingResult(
            success=True,
            message="Device scanned QR code",
            trust_code=trust_code,
            session_id=session_id,
            device_info=DeviceInfo(**{k: v for k, v in device_info_dict.items() if hasattr(DeviceInfo, k)}),
        )

    async def confirm_qr_pair(
        self,
        session_id: str,
        trust_code: str,
    ) -> PairingResult:
        """Confirm QR pairing with trust code verification"""
        session_data = self._active_sessions.get(session_id)
        if not session_data:
            return PairingResult(success=False, message="Invalid session")

        if session_data.get("trust_code") != trust_code:
            return PairingResult(success=False, message="Invalid trust code")

        user_id = session_data["user_id"]
        device_info_dict = session_data.get("device_info", {})
        serial = device_info_dict.get("serial", "")

        info = DeviceInfo(**{k: v for k, v in device_info_dict.items() if hasattr(DeviceInfo, k)})
        info.connection_type = "qr"

        device_id = await self._register_device(user_id, info)

        session_data["status"] = "paired"
        del self._active_sessions[session_id]

        # Update database
        db = self._get_db()
        try:
            from database.auth_models import DevicePairingSession
            pairing = db.query(DevicePairingSession).filter(
                DevicePairingSession.id == session_id
            ).first()
            if pairing:
                pairing.status = "paired"
                pairing.paired_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

        logger.info(f"QR pairing confirmed: {session_id}")

        return PairingResult(
            success=True,
            message="QR pairing confirmed",
            device_id=device_id,
            session_id=session_id,
        )

    # ==================== Device Info Extraction ====================

    async def _extract_device_info(self, serial: str) -> DeviceInfo:
        """Extract comprehensive device info via ADB"""
        info = DeviceInfo(serial=serial)

        if not self._adb:
            return info

        try:
            # Model
            model = await self._adb.shell(serial, "getprop ro.product.model")
            info.model = (model or "").strip()

            # Manufacturer
            mfr = await self._adb.shell(serial, "getprop ro.product.manufacturer")
            info.manufacturer = (mfr or "").strip()

            # Android version
            version = await self._adb.shell(serial, "getprop ro.build.version.release")
            info.android_version = (version or "").strip()

            # Screen size
            try:
                wm_size = await self._adb.shell(serial, "wm size")
                if wm_size and "x" in wm_size:
                    parts = wm_size.strip().split()[-1].split("x")
                    info.screen_width = int(parts[0])
                    info.screen_height = int(parts[1])
            except Exception:
                pass

            # Battery
            try:
                battery = await self._adb.shell(serial, "dumpsys battery")
                for line in (battery or "").split("\n"):
                    if "level:" in line:
                        info.battery_level = int(line.split(":")[-1].strip())
                        break
            except Exception:
                pass

            # Device name
            name = await self._adb.shell(serial, "getprop ro.product.name")
            info.device_name = (name or info.model or "Android Device").strip()

            # Check for APA agent
            try:
                ps_output = await self._adb.shell(serial, "ps | grep apaos")
                info.agent_installed = bool(ps_output and "apaos" in ps_output.lower())
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Device info extraction error for {serial}: {e}")

        return info

    # ==================== Database Helpers ====================

    def _create_pairing_session(
        self,
        user_id: str,
        pair_code: str,
        pairing_type: str,
        device_serial: str = "",
        device_ip: str = "",
        device_port: int = 0,
        device_info: Dict = None,
    ) -> str:
        """Create pairing session in database"""
        db = self._get_db()
        try:
            from database.auth_models import DevicePairingSession
            import uuid
            session_id = f"prs_{uuid.uuid4().hex[:12]}"
            pairing = DevicePairingSession(
                id=session_id,
                user_id=user_id,
                pair_code=pair_code,
                pairing_type=pairing_type,
                status="paired",
                device_ip=device_ip,
                device_port=device_port,
                device_serial=device_serial,
                device_info=device_info or {},
                paired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            db.add(pairing)
            db.commit()
            return session_id
        finally:
            db.close()

    def _update_pairing_status(self, session_id: str, status: str):
        """Update pairing session status"""
        db = self._get_db()
        try:
            from database.auth_models import DevicePairingSession
            pairing = db.query(DevicePairingSession).filter(
                DevicePairingSession.id == session_id
            ).first()
            if pairing:
                pairing.status = status
                db.commit()
        finally:
            db.close()

    async def _register_device(self, user_id: str, info: DeviceInfo) -> str:
        """Register or update device in database"""
        db = self._get_db()
        try:
            from database.auth_models import RegisteredDevice
            import uuid

            # Check if device already registered by serial
            existing = db.query(RegisteredDevice).filter(
                RegisteredDevice.user_id == user_id,
                RegisteredDevice.serial == info.serial,
            ).first()

            if existing:
                existing.device_name = info.device_name or info.model
                existing.model = info.model
                existing.manufacturer = info.manufacturer
                existing.android_version = info.android_version
                existing.screen_width = info.screen_width
                existing.screen_height = info.screen_height
                existing.battery_level = info.battery_level
                existing.connection_type = info.connection_type
                existing.connection_ip = info.connection_ip
                existing.connection_port = info.connection_port
                existing.is_online = True
                existing.last_seen = datetime.utcnow()
                existing.agent_installed = info.agent_installed
                existing.agent_version = info.agent_version
                existing.updated_at = datetime.utcnow()
                db.commit()
                return existing.id

            device_id = f"dev_{uuid.uuid4().hex[:12]}"
            device = RegisteredDevice(
                id=device_id,
                user_id=user_id,
                device_name=info.device_name or info.model or "Android Device",
                device_type="android",
                serial=info.serial,
                android_version=info.android_version,
                manufacturer=info.manufacturer,
                model=info.model,
                screen_width=info.screen_width,
                screen_height=info.screen_height,
                battery_level=info.battery_level,
                connection_type=info.connection_type,
                connection_ip=info.connection_ip,
                connection_port=info.connection_port,
                is_online=True,
                last_seen=datetime.utcnow(),
                agent_installed=info.agent_installed,
                agent_version=info.agent_version,
            )
            db.add(device)
            db.commit()
            return device_id
        finally:
            db.close()


# ==================== Singleton ====================

_pairing_engine: Optional[DevicePairingEngine] = None


def get_pairing_engine(adb_service=None) -> DevicePairingEngine:
    global _pairing_engine
    if _pairing_engine is None:
        _pairing_engine = DevicePairingEngine(adb_service)
    return _pairing_engine


# Re-export for convenience
from database.auth_models import DevicePairingSession, RegisteredDevice  # noqa: F401

# Expose generate helpers at module level
generate_pair_code = lambda: secrets.token_hex(3).upper()
generate_trust_code = lambda: f"{secrets.randbelow(900000) + 100000}"
