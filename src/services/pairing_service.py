"""
APA-OS Device Pairing Service
Handles the lifecycle of pairing a mobile device with a desktop workspace
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.auth_models import DevicePairingSession, RegisteredDevice, TrustedDevice, DevicePairingStatus, TrustLevel
from database.models import User
from config import Config

logger = logging.getLogger(__name__)

class PairingResult:
    def __init__(self, success: bool = True, message: str = "",
                 pair_code: str = None, device_id: str = None,
                 token: str = None, data: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.pair_code = pair_code
        self.device_id = device_id
        self.token = token
        self.data = data

class PairingService:
    def _get_session(self) -> Session:
        return get_db_session()

    def create_pairing_session(self, user_id: str, pairing_type: str = "qr") -> PairingResult:
        """
        Step 1: Create a pairing session on the desktop
        Generates a QR token/Pair code for the phone to scan
        """
        session = self._get_session()
        try:
            pair_code = secrets.token_urlsafe(8).upper() # e.g. "A1B2C3D4"
            qr_token = secrets.token_urlsafe(32)

            pairing_session = DevicePairingSession(
                id=f"prs_{secrets.token_urlsafe(6)}",
                user_id=user_id,
                pair_code=pair_code,
                pairing_type=pairing_type,
                status=DevicePairingStatus.PENDING,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                created_at=datetime.utcnow(),
                device_info={"qr_token": qr_token}
            )
            session.add(pairing_session)
            session.commit()

            return PairingResult(
                success=True,
                message="Pairing session created",
                pair_code=pair_code,
                token=qr_token
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Create pairing session error: {e}")
            return PairingResult(success=False, message=str(e))
        finally:
            session.close()

    def request_pairing(self, qr_token: str, device_info: Dict[str, Any]) -> PairingResult:
        """
        Step 2: Phone scans QR and requests pairing
        Validates token and updates session status
        """
        session = self._get_session()
        try:
            # Find session by qr_token in device_info JSON
            pairing_session = session.query(DevicePairingSession).filter(
                DevicePairingSession.device_info["qr_token"].astext == qr_token,
                DevicePairingSession.status == DevicePairingStatus.PENDING,
                DevicePairingSession.expires_at > datetime.utcnow()
            ).first()

            if not pairing_session:
                return PairingResult(success=False, message="Invalid or expired pairing token")

            # Update session with device info from phone
            pairing_session.status = DevicePairingStatus.SCANNED
            pairing_session.device_info.update(device_info)
            pairing_session.device_info = pairing_session.device_info # Trigger SQLAlchemy JSON update

            session.commit()

            return PairingResult(success=True, message="Pairing request received", data={"session_id": pairing_session.id})
        except Exception as e:
            session.rollback()
            logger.error(f"Request pairing error: {e}")
            return PairingResult(success=False, message=str(e))
        finally:
            session.close()

    def approve_pairing(self, session_id: str, user_id: str) -> PairingResult:
        """
        Step 3: Desktop approves the pairing
        Pairs devices and marks as trusted
        """
        session = self._get_session()
        try:
            pairing_session = session.query(DevicePairingSession).filter(
                DevicePairingSession.id == session_id,
                DevicePairingSession.user_id == user_id,
                DevicePairingSession.status == DevicePairingStatus.SCANNED
            ).first()

            if not pairing_session:
                return PairingResult(success=False, message="Pairing session not found or not in scanned state")

            # Create RegisteredDevice
            device_info = pairing_session.device_info
            device = RegisteredDevice(
                id=f"dev_{secrets.token_urlsafe(6)}",
                user_id=user_id,
                device_name=device_info.get("model", "Unknown Device"),
                device_type="android",
                manufacturer=device_info.get("manufacturer", "Unknown"),
                model=device_info.get("model", "Unknown"),
                android_version=device_info.get("android_version", "Unknown"),
                connection_type=pairing_session.pairing_type,
                connection_ip=device_info.get("ip", "0.0.0.0"),
                is_online=True,
                last_seen=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            session.add(device)
            session.flush()

            # Create Trust binding
            trust = TrustedDevice(
                id=f"trt_{secrets.token_urlsafe(6)}",
                device_id=device.id,
                user_id=user_id,
                trust_level=TrustLevel.PENDING,
                created_at=datetime.utcnow()
            )
            session.add(trust)

            # Complete pairing session
            pairing_session.status = DevicePairingStatus.PAIRED
            pairing_session.paired_at = datetime.utcnow()

            session.commit()

            return PairingResult(
                success=True,
                message="Device paired successfully",
                device_id=device.id,
                token=secrets.token_urlsafe(32) # Secure WebSocket token
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Approve pairing error: {e}")
            return PairingResult(success=False, message=str(e))
        finally:
            session.close()

    def verify_trust(self, device_id: str, user_id: str) -> PairingResult:
        """
        Step 4: Phone confirms trust
        Updates TrustLevel to ALWAYS_TRUSTED
        """
        session = self._get_session()
        try:
            trust = session.query(TrustedDevice).filter(
                TrustedDevice.device_id == device_id,
                TrustedDevice.user_id == user_id
            ).first()

            if not trust:
                return PairingResult(success=False, message="Trust relationship not found")

            trust.trust_level = TrustLevel.ALWAYS_TRUSTED
            trust.trusted_at = datetime.utcnow()

            session.commit()
            return PairingResult(success=True, message="Device trusted successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Verify trust error: {e}")
            return PairingResult(success=False, message=str(e))
        finally:
            session.close()

def get_pairing_service():
    return PairingService()
