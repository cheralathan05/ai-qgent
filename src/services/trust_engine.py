"""
APA-OS Trust Engine
Device trust management with certificates, trust tokens, and verification
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrustResult:
    """Trust operation result"""
    success: bool
    message: str
    trust_level: str = "none"
    trust_token: Optional[str] = None
    certificate: Optional[str] = None
    device_id: Optional[str] = None


class TrustEngine:
    """Device trust management engine"""

    def __init__(self):
        self._trust_cache: Dict[str, Dict[str, Any]] = {}

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    def trust_device(
        self,
        device_id: str,
        user_id: str,
        trust_level: str = "always_trusted",
        duration_days: int = 365,
    ) -> TrustResult:
        """Trust a device and generate certificates"""
        try:
            # Generate trust artifacts
            certificate = self._generate_certificate(device_id, user_id)
            secret_key = secrets.token_hex(32)
            trust_token = self._generate_trust_token(device_id, user_id, secret_key)
            fingerprint = self._generate_fingerprint(device_id, user_id)

            db = self._get_db()
            try:
                from database.auth_models import TrustedDevice

                existing = db.query(TrustedDevice).filter(
                    TrustedDevice.device_id == device_id,
                    TrustedDevice.user_id == user_id,
                ).first()

                if existing:
                    existing.trust_level = trust_level
                    existing.certificate = certificate
                    existing.secret_key = secret_key
                    existing.trust_token = trust_token
                    existing.fingerprint = fingerprint
                    existing.trusted_at = datetime.utcnow()
                    existing.expires_at = datetime.utcnow() + timedelta(days=duration_days)
                    existing.revoked_at = None
                else:
                    trusted = TrustedDevice(
                        device_id=device_id,
                        user_id=user_id,
                        trust_level=trust_level,
                        certificate=certificate,
                        secret_key=secret_key,
                        trust_token=trust_token,
                        fingerprint=fingerprint,
                        trusted_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=duration_days),
                    )
                    db.add(trusted)

                # Audit log
                from database.auth_models import SystemAuditLog
                audit = SystemAuditLog(
                    user_id=user_id,
                    device_id=device_id,
                    action="trust_device",
                    resource_type="device",
                    resource_id=device_id,
                    details={"trust_level": trust_level, "duration_days": duration_days},
                    result="success",
                )
                db.add(audit)
                db.commit()

            finally:
                db.close()

            # Cache
            self._trust_cache[f"{device_id}:{user_id}"] = {
                "trust_level": trust_level,
                "trust_token": trust_token,
                "expires_at": datetime.utcnow() + timedelta(days=duration_days),
            }

            logger.info(f"Device trusted: {device_id} for user {user_id} ({trust_level})")

            return TrustResult(
                success=True,
                message=f"Device trusted ({trust_level})",
                trust_level=trust_level,
                trust_token=trust_token,
                certificate=certificate,
                device_id=device_id,
            )
        except Exception as e:
            logger.error(f"Trust failed: {e}")
            return TrustResult(success=False, message=f"Trust failed: {str(e)}")

    def verify_trust(self, device_id: str, user_id: str) -> TrustResult:
        """Verify device trust status"""
        try:
            # Check cache first
            cache_key = f"{device_id}:{user_id}"
            cached = self._trust_cache.get(cache_key)
            if cached:
                if cached["expires_at"] > datetime.utcnow():
                    return TrustResult(
                        success=True,
                        message="Device is trusted",
                        trust_level=cached["trust_level"],
                        trust_token=cached["trust_token"],
                        device_id=device_id,
                    )
                else:
                    del self._trust_cache[cache_key]

            # Check database
            db = self._get_db()
            try:
                from database.auth_models import TrustedDevice

                trusted = db.query(TrustedDevice).filter(
                    TrustedDevice.device_id == device_id,
                    TrustedDevice.user_id == user_id,
                ).first()

                if not trusted:
                    return TrustResult(
                        success=False,
                        message="Device not trusted",
                        trust_level="none",
                        device_id=device_id,
                    )

                if trusted.revoked_at:
                    return TrustResult(
                        success=False,
                        message="Device trust revoked",
                        trust_level="none",
                        device_id=device_id,
                    )

                if trusted.expires_at and trusted.expires_at < datetime.utcnow():
                    return TrustResult(
                        success=False,
                        message="Device trust expired",
                        trust_level="none",
                        device_id=device_id,
                    )

                # Update cache
                self._trust_cache[cache_key] = {
                    "trust_level": trusted.trust_level.value if hasattr(trusted.trust_level, 'value') else trusted.trust_level,
                    "trust_token": trusted.trust_token,
                    "expires_at": trusted.expires_at,
                }

                return TrustResult(
                    success=True,
                    message="Device is trusted",
                    trust_level=trusted.trust_level.value if hasattr(trusted.trust_level, 'value') else trusted.trust_level,
                    trust_token=trusted.trust_token,
                    certificate=trusted.certificate,
                    device_id=device_id,
                )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Trust verification failed: {e}")
            return TrustResult(success=False, message=str(e))

    def revoke_trust(self, device_id: str, user_id: str) -> TrustResult:
        """Revoke device trust"""
        try:
            db = self._get_db()
            try:
                from database.auth_models import TrustedDevice, SystemAuditLog

                trusted = db.query(TrustedDevice).filter(
                    TrustedDevice.device_id == device_id,
                    TrustedDevice.user_id == user_id,
                ).first()

                if not trusted:
                    return TrustResult(success=False, message="No trust record found")

                trusted.revoked_at = datetime.utcnow()
                trusted.trust_level = "revoked"

                audit = SystemAuditLog(
                    user_id=user_id,
                    device_id=device_id,
                    action="revoke_trust",
                    resource_type="device",
                    resource_id=device_id,
                    result="success",
                )
                db.add(audit)
                db.commit()

            finally:
                db.close()

            # Remove from cache
            cache_key = f"{device_id}:{user_id}"
            self._trust_cache.pop(cache_key, None)

            logger.info(f"Trust revoked for device: {device_id}")

            return TrustResult(
                success=True,
                message="Device trust revoked",
                trust_level="revoked",
                device_id=device_id,
            )
        except Exception as e:
            return TrustResult(success=False, message=str(e))

    def get_trusted_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trusted devices for a user"""
        db = self._get_db()
        try:
            from database.auth_models import TrustedDevice, RegisteredDevice

            trusted_list = db.query(TrustedDevice).filter(
                TrustedDevice.user_id == user_id,
                TrustedDevice.revoked_at == None,
            ).all()

            results = []
            for t in trusted_list:
                device = db.query(RegisteredDevice).filter(
                    RegisteredDevice.id == t.device_id
                ).first()
                results.append({
                    "device_id": t.device_id,
                    "trust_level": t.trust_level.value if hasattr(t.trust_level, 'value') else t.trust_level,
                    "trusted_at": t.trusted_at.isoformat() if t.trusted_at else None,
                    "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                    "fingerprint": t.fingerprint,
                    "device_name": device.device_name if device else "Unknown",
                    "device_model": device.model if device else "Unknown",
                    "is_online": device.is_online if device else False,
                })

            return results
        finally:
            db.close()

    # ==================== Crypto Helpers ====================

    def _generate_certificate(self, device_id: str, user_id: str) -> str:
        """Generate device certificate"""
        data = f"apaos-cert:{device_id}:{user_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _generate_trust_token(self, device_id: str, user_id: str, secret: str) -> str:
        """Generate trust token"""
        data = f"apaos-trust:{device_id}:{user_id}:{secret}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _generate_fingerprint(self, device_id: str, user_id: str) -> str:
        """Generate device fingerprint"""
        data = f"apaos-fp:{device_id}:{user_id}"
        return hashlib.md5(data.encode()).hexdigest()


# ==================== Singleton ====================

_trust_engine: Optional[TrustEngine] = None


def get_trust_engine() -> TrustEngine:
    global _trust_engine
    if _trust_engine is None:
        _trust_engine = TrustEngine()
    return _trust_engine
