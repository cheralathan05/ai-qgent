"""
APA-OS Authentication API
Auth endpoints: signup, login, forgot-password, reset-password, verify
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import secrets
import logging

import jwt
from passlib.hash import pbkdf2_sha256

from database.connection import get_db_session
from database.models import User
from database.auth_models import UserSession, EmailVerification, PasswordReset
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def generate_token() -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(32)


def generate_token_hash(token: str) -> str:
    """Hash token for storage"""
    return pbkdf2_sha256.hash(token)


def validate_password(password: str) -> Optional[str]:
    """Validate password strength"""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    if not any(c in r"!@#$%^&*(),.?:{}|<>_-+=[]\\;'`~/" for c in password):
        return "Password must contain at least one special character"
    return None


@router.post("/signup")
async def signup(request: dict):
    """Create new user account"""
    try:
        if not request.get("email") or not request.get("password"):
            raise HTTPException(status_code=400, detail="Email and password required")

        session = get_db_session()
        try:
            # Check if email exists
            existing = session.query(User).filter(User.email == request["email"].lower()).first()
            if existing:
                raise HTTPException(status_code=409, detail="Email already registered")

            # Validate password
            pw_error = validate_password(request["password"])
            if pw_error:
                raise HTTPException(status_code=400, detail=pw_error)

            # Create user
            user = User(
                id=secrets.token_urlsafe(16),
                name=request.get("name", ""),
                email=request["email"].lower(),
                password_hash=pbkdf2_sha256.hash(request["password"]),
                email_verified=False,
                verification_token=None,
                reset_token=None,
                reset_token_expiry=None,
                created_at=datetime.utcnow(),
                status="active",
            )
            session.add(user)
            session.flush()

            # Send verification email
            verification_token = generate_token()
            verification = EmailVerification(
                id=secrets.token_urlsafe(16),
                user_id=user.id,
                token=generate_token_hash(verification_token),
                email=user.email,
                verified=False,
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            session.add(verification)

            from services.email_service import EmailService
            verification_link = f"{Config.FRONTEND_URL}/verify-email?token={verification_token}"
            EmailService().send_verification(user.email, verification_link)

            session.commit()

            logger.info(f"User signed up: {user.id}")
            return {"success": True, "message": "Check your email to verify your account", "user_id": user.id}

        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Signup failed")


@router.post("/login")
async def login(request: dict):
    """Authenticate user and return tokens"""
    try:
        if not request.get("email") or not request.get("password"):
            raise HTTPException(status_code=400, detail="Email and password required")

        session = get_db_session()
        try:
            # Find user
            user = session.query(User).filter(User.email == request["email"].lower()).first()
            if not user:
                return {"success": False, "message": "Invalid email or password"}

            # Check email verification
            if not user.email_verified:
                return {"success": False, "message": "Email not verified"}

            # Verify password
            try:
                if not pbkdf2_sha256.verify(request["password"], user.password_hash):
                    return {"success": False, "message": "Invalid email or password"}
            except Exception:
                return {"success": False, "message": "Invalid email or password"}

            # Generate tokens
            access_token_jti = generate_token()
            refresh_token_jti = generate_token()
            access_token = jwt.encode(
                {"sub": user.id, "jti": access_token_jti, "exp": datetime.utcnow() + timedelta(minutes=1440)},
                Config.JWT_SECRET, algorithm="HS256"
            )
            refresh_token = jwt.encode(
                {"sub": user.id, "jti": refresh_token_jti, "exp": datetime.utcnow() + timedelta(days=7)},
                Config.JWT_SECRET, algorithm="HS256"
            )

            # Create session
            user_session = UserSession(
                id=secrets.token_urlsafe(16),
                user_id=user.id,
                access_token_jti=access_token_jti,
                refresh_token_jti=refresh_token_jti,
                status="active",
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
            session.add(user_session)

            # Update user
            user.last_login = datetime.utcnow()
            session.commit()

            logger.info(f"User login: {user.id}")
            return {
                "success": True,
                "message": "Login successful",
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "session_id": user_session.id,
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/forgot-password")
async def forgot_password(request: dict):
    """Request password reset"""
    try:
        email = request.get("email", "").lower()
        if not email:
            raise HTTPException(status_code=400, detail="Email required")

        session = get_db_session()
        try:
            # Find user
            user = session.query(User).filter(User.email == email).first()

            # Generate token regardless
            reset_token = generate_token()
            reset_hash = generate_token_hash(reset_token)

            # Store reset if user exists
            if user:
                reset = PasswordReset(
                    id=secrets.token_urlsafe(16),
                    user_id=user.id,
                    token=reset_hash,
                    used=False,
                    expires_at=datetime.utcnow() + timedelta(minutes=15),
                )
                session.add(reset)

                # Send email
                reset_link = f"{Config.FRONTEND_URL}/reset-password?token={reset_token}"
                from services.email_service import EmailService
                EmailService().send_password_reset(email, reset_link)
                logger.info(f"Password reset email sent to {email}")

            session.commit()

            # Never reveal if email exists
            return {"success": True, "message": "If the email exists, a reset link has been sent", "token": reset_token}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail="Forgot password failed")


@router.get("/reset-password/verify")
async def verify_reset_token(token: str):
    """Verify reset token"""
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token required")

        session = get_db_session()
        try:
            token_hash = generate_token_hash(token)
            reset = session.query(PasswordReset).filter(
                PasswordReset.token == token_hash, PasswordReset.used == False
            ).first()

            if not reset or reset.expires_at < datetime.utcnow():
                return {"success": False, "message": "Invalid or expired token"}

            return {"success": True, "message": "Token valid", "user_id": reset.user_id}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify reset token error: {e}")
        raise HTTPException(status_code=500, detail="Token verification failed")


@router.post("/reset-password")
async def reset_password(request: dict):
    """Reset password with token"""
    try:
        token = request.get("token", "")
        new_password = request.get("new_password", "")
        if not token or not new_password:
            raise HTTPException(status_code=400, detail="Token and new password required")

        # Validate password
        pw_error = validate_password(new_password)
        if pw_error:
            raise HTTPException(status_code=400, detail=pw_error)

        session = get_db_session()
        try:
            token_hash = generate_token_hash(token)
            reset = session.query(PasswordReset).filter(
                PasswordReset.token == token_hash, PasswordReset.used == False
            ).first()

            if not reset or reset.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="Invalid or expired token")

            user = session.query(User).filter(User.id == reset.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Update password
            user.password_hash = pbkdf2_sha256.hash(new_password)
            user.updated_at = datetime.utcnow()
            reset.used = True

            # Invalidate sessions
            session.query(UserSession).filter(
                UserSession.user_id == user.id, UserSession.status == "active"
            ).update({"status": "revoked"})

            session.commit()

            logger.info(f"Password reset for user: {user.id}")
            return {"success": True, "message": "Password reset successful"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed")


@router.get("/verify")
async def verify_email(token: str):
    """Verify email address"""
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token required")

        session = get_db_session()
        try:
            token_hash = generate_token_hash(token)
            verification = session.query(EmailVerification).filter(
                EmailVerification.token == token_hash
            ).first()

            if not verification or verification.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="Invalid or expired token")

            user = session.query(User).filter(User.id == verification.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.email_verified = True
            user.verification_token = None
            user.updated_at = datetime.utcnow()
            verification.used = True

            session.commit()

            logger.info(f"Email verified: {user.id}")
            return {"success": True, "message": "Email verified successfully"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=500, detail="Email verification failed")


@router.post("/refresh")
async def refresh_token(request: dict):
    """Refresh access token"""
    try:
        refresh_token = request.get("refresh_token", "")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token required")

        try:
            payload = jwt.decode(refresh_token, Config.JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("sub")
            jti = payload.get("jti")

            if not user_id or not jti:
                raise HTTPException(status_code=401, detail="Invalid token")

            session = get_db_session()
            try:
                user_session = session.query(UserSession).filter(
                    UserSession.refresh_token_jti == jti, UserSession.status == "active"
                ).first()

                if not user_session or user_session.expires_at < datetime.utcnow():
                    raise HTTPException(status_code=401, detail="Session expired")

                new_access_token_jti = generate_token()
                new_refresh_token_jti = generate_token()
                new_access_token = jwt.encode(
                    {"sub": user_id, "jti": new_access_token_jti, "exp": datetime.utcnow() + timedelta(minutes=1440)},
                    Config.JWT_SECRET, algorithm="HS256"
                )
                new_refresh_token = jwt.encode(
                    {"sub": user_id, "jti": new_refresh_token_jti, "exp": datetime.utcnow() + timedelta(days=7)},
                    Config.JWT_SECRET, algorithm="HS256"
                )

                user_session.access_token_jti = new_access_token_jti
                user_session.refresh_token_jti = new_refresh_token_jti
                user_session.last_active_at = datetime.utcnow()
                user_session.expires_at = datetime.utcnow() + timedelta(days=1)

                session.commit()

                return {
                    "success": True,
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                }
            finally:
                session.close()
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")


@router.post("/logout")
async def logout(request: dict):
    """Logout user"""
    try:
        session_id = request.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")

        session = get_db_session()
        try:
            user_session = session.query(UserSession).filter(
                UserSession.id == session_id, UserSession.status == "active"
            ).first()

            if not user_session:
                raise HTTPException(status_code=404, detail="Session not found")

            user_session.status = "revoked"
            session.commit()

            return {"success": True, "message": "Logged out successfully"}
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/me")
async def get_me(token: str):
    """Get current user info"""
    try:
        if not token:
            raise HTTPException(status_code=400, detail="Token required")

        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        session = get_db_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "email_verified": user.email_verified,
                    "status": user.status,
                },
            }
        finally:
            session.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Get me error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user info")
