"""
APA-OS Authentication Service
Complete authentication with JWT, sessions, email verification, and password reset
"""

import bcrypt
import jwt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import re
import logging

from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import User
from database.auth_models import UserSession, EmailVerification, PasswordReset
from config import Config

logger = logging.getLogger(__name__)

# ==================== Token Generation ====================

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify bcrypt password"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def generate_jwt_token(user_id: str, jti: str, expires_minutes: int = 1440) -> str:
    """Generate JWT access token"""
    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def validate_password(password: str) -> Optional[str]:
    """Validate password strength"""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\;'`~/]", password):
        return "Password must contain at least one special character"
    return None


class AuthResult:
    """Result of authentication operations"""
    def __init__(self, success: bool = True, message: str = "", 
                 user_id: str = None, token: str = None,
                 refresh_token: str = None, session_id: str = None,
                 expires_at: datetime = None, access_token: str = None):
        self.success = success
        self.message = message
        self.user_id = user_id
        self.token = token
        self.refresh_token = refresh_token
        self.session_id = session_id
        self.expires_at = expires_at
        self.access_token = access_token


class AuthService:
    """Complete authentication service"""
    
    def _get_session(self) -> Session:
        """Get database session"""
        return get_db_session()

    def signup(self, name: str, email: str, password: str) -> AuthResult:
        """Create new user account"""
        session = self._get_session()
        try:
            # Check if email already exists
            existing_user = session.query(User).filter(User.email == email.lower()).first()
            if existing_user:
                return AuthResult(success=False, message="Email already registered")

            # Validate email format
            if "@" not in email:
                return AuthResult(success=False, message="Invalid email format")

            # Validate password strength
            pw_error = validate_password(password)
            if pw_error:
                return AuthResult(success=False, message=pw_error)

            # Create user (auto-verified)
            user = User(
                id=secrets.token_urlsafe(16),
                full_name=name,
                email=email.lower(),
                password_hash=hash_password(password),
                email_verified=True,
                verification_token=None,
                reset_token=None,
                reset_token_expiry=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                status="active",
            )
            session.add(user)
            session.commit()

            logger.info(f"User signed up (auto-verified): {user.id} - {email}")
            return AuthResult(success=True, message="Account created successfully", user_id=user.id)

        except Exception as e:
            session.rollback()
            logger.error(f"Signup error: {e}")
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    def resend_verification(self, email: str) -> AuthResult:
        """Resend verification email"""
        session = self._get_session()
        try:
            email = email.lower()
            user = session.query(User).filter(User.email == email).first()
            if not user:
                return AuthResult(success=True, message="If an account exists, a verification email has been sent.")
            if user.email_verified:
                return AuthResult(success=True, message="Email already verified.")
            verification_token = generate_token()
            user.verification_token = verification_token
            verification_link = f"{Config.FRONTEND_URL}/verify-email?token={verification_token}"
            from services.email_service import EmailService
            EmailService().send_verification(email, verification_link)
            session.commit()
            logger.info(f"Verification email resent: {email}")
            return AuthResult(success=True, message="Verification email sent.")
        except Exception as e:
            session.rollback()
            logger.error(f"Resend verification error: {e}")
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    def login(self, email: str, password: str, device_info: Dict[str, Any] = None) -> AuthResult:
        """Authenticate user and return tokens"""
        session = self._get_session()
        try:
            # Find user
            user = session.query(User).filter(User.email == email.lower()).first()
            if not user:
                return AuthResult(success=False, message="Invalid email or password")

            # Check if email is verified
            if not user.email_verified:
                return AuthResult(success=False, message="Email not verified")

            # Check if account is active
            if user.status != "active":
                return AuthResult(success=False, message="Account is not active")

            # Verify password
            try:
                if not verify_password(password, user.password_hash):
                    return AuthResult(success=False, message="Invalid email or password")
            except Exception:
                return AuthResult(success=False, message="Invalid email or password")

            # Generate tokens
            access_token_jti = generate_token()
            refresh_token_jti = generate_token()
            access_token = generate_jwt_token(user.id, access_token_jti)
            refresh_token = generate_jwt_token(user.id, refresh_token_jti, 10080)

            # Create user session
            user_session = UserSession(
                id=secrets.token_urlsafe(16),
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                device_name=device_info.get("device_name") if device_info else "Unknown Device",
                ip_address="unknown",
                status="active",
                last_active_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=1),
                created_at=datetime.utcnow(),
            )
            session.add(user_session)

            # Update user last login
            user.last_login = datetime.utcnow()
            session.commit()

            logger.info(f"User login: {user.id} - {email}")
            return AuthResult(
                success=True,
                message="Login successful",
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=user_session.id,
                expires_at=datetime.utcnow() + timedelta(days=1),
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Login error: {e}")
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    def verify_email(self, token: str) -> AuthResult:
        """Verify email address with token"""
        session = self._get_session()
        try:
            # Find user with this token
            user = session.query(User).filter(User.verification_token == token).first()

            if not user:
                return AuthResult(success=False, message="Invalid or expired token")

            # Update user
            user.email_verified = True
            user.verification_token = None
            user.updated_at = datetime.utcnow()

            # Create a verification record for auditing
            verification = EmailVerification(
                id=secrets.token_urlsafe(16),
                user_id=user.id,
                token=token,
                email=user.email,
                verified=True,
                expires_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(verification)

            session.commit()

            logger.info(f"Email verified: {user.id}")
            return AuthResult(success=True, message="Email verified successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"Email verification error: {e}")
            return AuthResult(success=False, message=str(e))
        finally:
            session.close()

    def verify_reset_token(self, raw_token: str) -> AuthResult:
        """Verify a password reset token without consuming it"""
        session = self._get_session()
        try:
            token_hash = generate_token_hash(raw_token)
            reset = session.query(PasswordReset).filter(
                PasswordReset.token == token_hash,
                PasswordReset.used == False,
            ).first()

            if not reset:
                return AuthResult(success=False, message="Invalid or used reset token")

            if reset.expires_at < datetime.utcnow():
                return AuthResult(success=False, message="Reset token expired")

            return AuthResult(success=True, message="Token is valid", user_id=reset.user_id)
        finally:
            session.close()

    def reset_password(self, raw_token: str, new_password: str) -> AuthResult:
        """Reset password with token"""
        session = self._get_session()
        try:
            # Validate password strength
            pw_error = validate_password(new_password)
            if pw_error:
                return AuthResult(success=False, message=pw_error)

            # Find user with this token
            user = session.query(User).filter(
                User.reset_token == raw_token,
                User.reset_token_expiry >= datetime.utcnow()
            ).first()

            if not user:
                return AuthResult(success=False, message="Invalid or expired reset token")

            # Update password
            user.password_hash = hash_password(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            user.updated_at = datetime.utcnow()

            # Invalidate other sessions
            session.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.status == "active",
            ).update({"status": "revoked"})

            session.commit()

            logger.info(f"Password reset completed for user: {user.id}")
            return AuthResult(success=True, message="Password reset successful")
        finally:
            session.close()

    def forgot_password(self, email: str) -> AuthResult:
        """Generate password reset token and send email"""
        session = self._get_session()
        try:
            email = email.lower()

            # Find user
            user = session.query(User).filter(User.email == email).first()

            if not user:
                # Never reveal if email exists
                return AuthResult(
                    success=True,
                    message="If an account exists with this email, a reset link has been sent",
                )

            # Generate reset token
            raw_token = generate_token()
            user.reset_token = raw_token
            user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)

            # Store reset record for auditing
            reset = PasswordReset(
                id=secrets.token_urlsafe(16),
                user_id=user.id,
                token=raw_token,
                used=False,
                expires_at=user.reset_token_expiry,
                created_at=datetime.utcnow(),
            )
            session.add(reset)

            # Send reset email
            reset_link = f"{Config.FRONTEND_URL}/reset-password?token={raw_token}"
            from services.email_service import EmailService
            email_sent = EmailService().send_password_reset(email, reset_link)

            if not email_sent:
                logger.warning(f"Failed to send reset email to {email}")

            session.commit()

            logger.info(f"Password reset requested for: {email}")
            return AuthResult(
                success=True,
                message="If an account exists with this email, a reset link has been sent",
                token=raw_token,
            )
        finally:
            session.close()

    def refresh_tokens(self, refresh_token: str) -> AuthResult:
        """Refresh access token"""
        try:
            payload = jwt.decode(refresh_token, Config.JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("sub")
            jti = payload.get("jti")

            if not user_id or not jti:
                return AuthResult(success=False, message="Invalid refresh token")

            session = self._get_session()
            try:
                user_session = session.query(UserSession).filter(
                    UserSession.refresh_token == refresh_token,
                    UserSession.status == "active",
                ).first()

                if not user_session:
                    return AuthResult(success=False, message="Invalid session")

                if user_session.expires_at < datetime.utcnow():
                    return AuthResult(success=False, message="Session expired")

                # Generate new tokens
                new_access_token_jti = generate_token()
                new_refresh_token_jti = generate_token()
                new_access_token = generate_jwt_token(user_id, new_access_token_jti)
                new_refresh_token = generate_jwt_token(user_id, new_refresh_token_jti, 10080)

                # Update session
                user_session.access_token = new_access_token
                user_session.refresh_token = new_refresh_token
                user_session.last_active_at = datetime.utcnow()
                user_session.expires_at = datetime.utcnow() + timedelta(days=1)

                session.commit()

                logger.info(f"Tokens refreshed for user: {user_id}")
                return AuthResult(
                    success=True,
                    message="Tokens refreshed",
                    access_token=new_access_token,
                    refresh_token=new_refresh_token,
                )
            finally:
                session.close()

        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, message="Refresh token expired")
        except jwt.InvalidTokenError:
            return AuthResult(success=False, message="Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return AuthResult(success=False, message=str(e))

    def logout(self, session_id: str) -> AuthResult:
        """Logout user and revoke session"""
        session = self._get_session()
        try:
            user_session = session.query(UserSession).filter(
                UserSession.id == session_id,
                UserSession.status == "active",
            ).first()

            if not user_session:
                return AuthResult(success=False, message="Session not found")

            user_session.status = "revoked"
            session.commit()

            logger.info(f"User logout: {user_session.user_id}")
            return AuthResult(success=True, message="Logout successful")
        finally:
            session.close()

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token and return user info"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            return {
                "user_id": payload.get("sub"),
                "jti": payload.get("jti"),
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None


def get_auth_service():
    """Get auth service instance"""
    return AuthService()
