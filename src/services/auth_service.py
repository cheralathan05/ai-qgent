"""
APA-OS Authentication Service
JWT-based auth with signup, login, email verification, password reset, session management
"""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ==================== Password Hashing ====================

try:
    from bcrypt import hashpw, checkpw, gensalt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not available, using fallback hashing")


def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    if BCRYPT_AVAILABLE:
        return hashpw(password.encode("utf-8"), gensalt(rounds=12)).decode("utf-8")
    # Fallback: sha256 + salt (not production-grade but functional)
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"sha256${salt}${h}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    if BCRYPT_AVAILABLE and password_hash.startswith("$2"):
        return checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    # Fallback for sha256 hashes
    if password_hash.startswith("sha256$"):
        parts = password_hash.split("$")
        if len(parts) == 3:
            salt, h = parts[1], parts[2]
            return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == h
    return False


# ==================== JWT Management ====================

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not available, using token-based auth fallback")


JWT_SECRET = None
JWT_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """Get or generate JWT secret"""
    global JWT_SECRET
    if JWT_SECRET is None:
        import os
        JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
    return JWT_SECRET


def generate_access_token(
    user_id: str,
    email: str,
    expires_minutes: int = 60,
    jti: Optional[str] = None,
) -> Tuple[str, str, datetime]:
    """
    Generate JWT access token
    Returns: (token, jti, expires_at)
    """
    jti = jti or secrets.token_hex(16)
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)

    if JWT_AVAILABLE:
        payload = {
            "sub": user_id,
            "email": email,
            "jti": jti,
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": expires_at,
        }
        token = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
    else:
        # Fallback: signed token
        payload = f"{user_id}:{email}:{jti}:{expires_at.isoformat()}"
        sig = hashlib.sha256(f"{_get_jwt_secret()}:{payload}".encode()).hexdigest()
        token = f"apa_{payload}:{sig}"

    return token, jti, expires_at


def generate_refresh_token(
    user_id: str,
    expires_days: int = 30,
    jti: Optional[str] = None,
) -> Tuple[str, str, datetime]:
    """
    Generate refresh token
    Returns: (token, jti, expires_at)
    """
    jti = jti or secrets.token_hex(16)
    expires_at = datetime.utcnow() + timedelta(days=expires_days)

    if JWT_AVAILABLE:
        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "refresh",
            "iat": datetime.utcnow(),
            "exp": expires_at,
        }
        token = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
    else:
        payload = f"{user_id}:refresh:{jti}:{expires_at.isoformat()}"
        sig = hashlib.sha256(f"{_get_jwt_secret()}:{payload}".encode()).hexdigest()
        token = f"apa_ref_{payload}:{sig}"

    return token, jti, expires_at


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token"""
    if JWT_AVAILABLE:
        try:
            return jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    else:
        # Fallback decode
        try:
            if token.startswith("apa_ref_"):
                payload_str = token[8:]
            elif token.startswith("apa_"):
                payload_str = token[4:]
            else:
                return None

            parts = payload_str.rsplit(":", 1)
            if len(parts) != 2:
                return None

            payload, sig = parts
            expected_sig = hashlib.sha256(f"{_get_jwt_secret()}:{payload}".encode()).hexdigest()
            if sig != expected_sig:
                return None

            fields = payload.split(":")
            if len(fields) >= 4:
                return {"sub": fields[0], "email": fields[1] if len(fields) > 1 else "", "jti": fields[2] if len(fields) > 2 else ""}
            return None
        except Exception:
            return None


# ==================== Token Generation ====================

def generate_verification_token() -> str:
    """Generate email verification token"""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generate password reset token"""
    return secrets.token_urlsafe(32)


def generate_pair_code() -> str:
    """Generate device pairing code"""
    return secrets.token_hex(3).upper()


def generate_trust_code() -> str:
    """Generate 6-digit trust verification code"""
    return f"{secrets.randbelow(900000) + 100000}"


# ==================== Auth Service ====================

@dataclass
class AuthResult:
    """Authentication result"""
    success: bool
    message: str
    user_id: Optional[str] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    session_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class AuthService:
    """Complete authentication service"""

    def __init__(self, db_session_factory=None):
        self._db_session_factory = db_session_factory

    def _get_session(self):
        if self._db_session_factory:
            return self._db_session_factory()
        from database.connection import get_db_session
        return get_db_session()

    # ==================== Signup ====================

    def signup(
        self,
        name: str,
        email: str,
        password: str,
    ) -> AuthResult:
        """Create new user account"""
        session = self._get_session()
        try:
            from database.models import User

            # Check if email exists
            existing = session.query(User).filter(User.email == email.lower()).first()
            if existing:
                return AuthResult(success=False, message="Email already registered")

            # Validate password strength
            if len(password) < 8:
                return AuthResult(success=False, message="Password must be at least 8 characters")

            # Create user
            user = User(
                name=name,
                email=email.lower(),
                password_hash=hash_password(password),
                email_verified=False,
                status="active",
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create workspace
            from database.auth_models import UserWorkspace, UserProfile
            workspace = UserWorkspace(
                user_id=user.id,
                workspace_name=f"{name}'s Workspace",
            )
            session.add(workspace)

            profile = UserProfile(
                user_id=user.id,
            )
            session.add(profile)
            session.commit()

            # Generate verification token
            from database.auth_models import EmailVerification
            verification_token = generate_verification_token()
            verification = EmailVerification(
                user_id=user.id,
                token=verification_token,
                email=email.lower(),
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            session.add(verification)
            session.commit()

            # Generate tokens
            token, jti, expires_at = generate_access_token(user.id, email)
            refresh, refresh_jti, refresh_expires = generate_refresh_token(user.id)

            # Create session
            from database.auth_models import UserSession
            user_session = UserSession(
                user_id=user.id,
                access_token_jti=jti,
                refresh_token_jti=refresh_jti,
                status="active",
                expires_at=refresh_expires,
            )
            session.add(user_session)
            session.commit()

            logger.info(f"User signed up: {user.id} ({email})")

            return AuthResult(
                success=True,
                message="Account created successfully",
                user_id=user.id,
                token=token,
                refresh_token=refresh,
                session_id=user_session.id,
                expires_at=expires_at,
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Signup failed: {e}")
            return AuthResult(success=False, message=f"Signup failed: {str(e)}")
        finally:
            session.close()

    # ==================== Login ====================

    def login(
        self,
        email: str,
        password: str,
        device_info: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthResult:
        """Authenticate user and create session"""
        session = self._get_session()
        try:
            from database.models import User

            user = session.query(User).filter(User.email == email.lower()).first()
            if not user:
                return AuthResult(success=False, message="Invalid email or password")

            if not verify_password(password, user.password_hash):
                return AuthResult(success=False, message="Invalid email or password")

            if user.status != "active":
                return AuthResult(success=False, message="Account is not active")

            # Update login info
            user.last_login_at = datetime.utcnow()
            user.login_count = (user.login_count or 0) + 1
            session.commit()

            # Generate tokens
            token, jti, expires_at = generate_access_token(user.id, user.email)
            refresh, refresh_jti, refresh_expires = generate_refresh_token(user.id)

            # Create session
            from database.auth_models import UserSession
            user_session = UserSession(
                user_id=user.id,
                access_token_jti=jti,
                refresh_token_jti=refresh_jti,
                device_info=device_info or {},
                ip_address=ip_address,
                user_agent=user_agent,
                status="active",
                expires_at=refresh_expires,
            )
            session.add(user_session)
            session.commit()

            # Audit log
            from database.auth_models import SystemAuditLog
            audit = SystemAuditLog(
                user_id=user.id,
                session_id=user_session.id,
                action="login",
                resource_type="user",
                resource_id=user.id,
                details={"method": "password"},
                ip_address=ip_address,
                user_agent=user_agent,
                result="success",
            )
            session.add(audit)
            session.commit()

            logger.info(f"User logged in: {user.id} ({email})")

            return AuthResult(
                success=True,
                message="Login successful",
                user_id=user.id,
                token=token,
                refresh_token=refresh,
                session_id=user_session.id,
                expires_at=expires_at,
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Login failed: {e}")
            return AuthResult(success=False, message=f"Login failed: {str(e)}")
        finally:
            session.close()

    # ==================== Token Refresh ====================

    def refresh_tokens(self, refresh_token: str) -> AuthResult:
        """Refresh access token using refresh token"""
        session = self._get_session()
        try:
            from database.auth_models import UserSession, User
            from database.models import User as UserModel

            decoded = decode_token(refresh_token)
            if not decoded:
                return AuthResult(success=False, message="Invalid refresh token")

            user_id = decoded.get("sub")
            jti = decoded.get("jti")

            # Find session
            user_session = session.query(UserSession).filter(
                UserSession.refresh_token_jti == jti,
                UserSession.status == "active",
            ).first()

            if not user_session:
                return AuthResult(success=False, message="Session not found or expired")

            if user_session.expires_at and user_session.expires_at < datetime.utcnow():
                user_session.status = "expired"
                session.commit()
                return AuthResult(success=False, message="Session expired")

            # Get user
            user = session.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                return AuthResult(success=False, message="User not found")

            # Generate new tokens
            token, new_jti, expires_at = generate_access_token(user.id, user.email)
            new_refresh, new_refresh_jti, new_refresh_expires = generate_refresh_token(user.id)

            # Update session
            user_session.access_token_jti = new_jti
            user_session.refresh_token_jti = new_refresh_jti
            user_session.last_active_at = datetime.utcnow()
            user_session.expires_at = new_refresh_expires
            session.commit()

            return AuthResult(
                success=True,
                message="Tokens refreshed",
                user_id=user.id,
                token=token,
                refresh_token=new_refresh,
                session_id=user_session.id,
                expires_at=expires_at,
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Token refresh failed: {e}")
            return AuthResult(success=False, message=f"Refresh failed: {str(e)}")
        finally:
            session.close()

    # ==================== Logout ====================

    def logout(self, session_id: str, user_id: Optional[str] = None) -> AuthResult:
        """Revoke session"""
        session = self._get_session()
        try:
            from database.auth_models import UserSession

            query = session.query(UserSession).filter(UserSession.id == session_id)
            if user_id:
                query = query.filter(UserSession.user_id == user_id)

            user_session = query.first()
            if not user_session:
                return AuthResult(success=False, message="Session not found")

            user_session.status = "revoked"
            session.commit()

            logger.info(f"Session revoked: {session_id}")
            return AuthResult(success=True, message="Logged out successfully")
        except Exception as e:
            session.rollback()
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    # ==================== Verify Email ====================

    def verify_email(self, token: str) -> AuthResult:
        """Verify email with token"""
        session = self._get_session()
        try:
            from database.auth_models import EmailVerification
            from database.models import User

            verification = session.query(EmailVerification).filter(
                EmailVerification.token == token,
                EmailVerification.verified == False,
            ).first()

            if not verification:
                return AuthResult(success=False, message="Invalid or used verification token")

            if verification.expires_at < datetime.utcnow():
                return AuthResult(success=False, message="Verification token expired")

            # Mark verified
            verification.verified = True
            user = session.query(User).filter(User.id == verification.user_id).first()
            if user:
                user.email_verified = True
            session.commit()

            logger.info(f"Email verified for user: {verification.user_id}")
            return AuthResult(success=True, message="Email verified", user_id=verification.user_id)
        except Exception as e:
            session.rollback()
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    # ==================== Forgot Password ====================

    def forgot_password(self, email: str) -> AuthResult:
        """Generate password reset token"""
        session = self._get_session()
        try:
            from database.auth_models import PasswordReset
            from database.models import User

            user = session.query(User).filter(User.email == email.lower()).first()
            if not user:
                # Don't reveal if user exists
                return AuthResult(success=True, message="If the email exists, a reset link has been sent")

            reset_token = generate_reset_token()
            reset = PasswordReset(
                user_id=user.id,
                token=reset_token,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
            session.add(reset)
            session.commit()

            logger.info(f"Password reset requested for: {email}")
            return AuthResult(
                success=True,
                message="If the email exists, a reset link has been sent",
                token=reset_token,
            )
        except Exception as e:
            session.rollback()
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    # ==================== Reset Password ====================

    def reset_password(self, token: str, new_password: str) -> AuthResult:
        """Reset password with token"""
        session = self._get_session()
        try:
            from database.auth_models import PasswordReset, UserSession
            from database.models import User

            reset = session.query(PasswordReset).filter(
                PasswordReset.token == token,
                PasswordReset.used == False,
            ).first()

            if not reset:
                return AuthResult(success=False, message="Invalid or used reset token")

            if reset.expires_at < datetime.utcnow():
                return AuthResult(success=False, message="Reset token expired")

            # Update password
            user = session.query(User).filter(User.id == reset.user_id).first()
            if not user:
                return AuthResult(success=False, message="User not found")

            user.password_hash = hash_password(new_password)
            reset.used = True

            # Invalidate all other sessions
            session.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.status == "active",
            ).update({"status": "revoked"})

            session.commit()

            logger.info(f"Password reset completed for user: {user.id}")
            return AuthResult(success=True, message="Password reset successful")
        except Exception as e:
            session.rollback()
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    # ==================== Validate Token ====================

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate access token and return user info"""
        decoded = decode_token(token)
        if not decoded:
            return None

        if decoded.get("type") != "access":
            return None

        session = self._get_session()
        try:
            from database.auth_models import UserSession

            jti = decoded.get("jti")
            user_session = session.query(UserSession).filter(
                UserSession.access_token_jti == jti,
                UserSession.status == "active",
            ).first()

            if not user_session:
                return None

            return {
                "user_id": decoded.get("sub"),
                "email": decoded.get("email"),
                "session_id": user_session.id,
            }
        finally:
            session.close()


# ==================== Singleton ====================

_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
