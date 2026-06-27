"""
APA-OS Complete Authentication - v1 API
End-to-end authentication with PostgreSQL database
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
import logging
from passlib.hash import pbkdf2_sha256
import jwt

from database.connection import get_db_session
from database.models import User
from database.auth_models import UserSession, EmailVerification, PasswordReset
from services.email_service import EmailService
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Authentication v1"])


# ==================== Auth APIs ====================

@router.post("/register")
async def register(user_data: dict):
    """Create new user account"""
    session = get_db_session()
    try:
        # Check if email exists
        user = session.query(User).filter(User.email == user_data["email"].lower()).first()
        if user:
            raise HTTPException(status_code=409, detail="Email already registered")

        # Create user
        user = User(
            full_name=user_data["name"],
            email=user_data["email"].lower(),
            password_hash=pbkdf2_sha256.hash(user_data["password"]),
            email_verified=False,
            verification_token=pbkdf2_sha256.hash(secrets.token_urlsafe(32)),
            reset_token=None,
            reset_token_expiry=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="active",
        )
        session.add(user)
        session.flush()

        # Send verification email
        verification_token = secrets.token_urlsafe(32)
        verification = EmailVerification(
            user_id=user.id,
            token=pbkdf2_sha256.hash(verification_token),
            email=user.email,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        session.add(verification)

        verification_link = f"{Config.FRONTEND_URL}/verify-email?token={verification_token}"
        EmailService().send_verification(user.email, verification_link)

        session.commit()

        return {"success": True, "message": "Account created. Check your email.", "user_id": user.id}

    except Exception as e:
        session.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/login")
async def login(login_data: dict):
    """Authenticate user and return tokens"""
    session = get_db_session()
    try:
        # Find user
        user = session.query(User).filter(User.email == login_data["email"].lower()).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify email
        if not user.email_verified:
            raise HTTPException(status_code=403, detail="Email not verified")

        # Verify password
        if not pbkdf2_sha256.verify(login_data["password"], user.password_hash):
            # Log failed attempt
            from database.auth_models import LoginHistory
            history = LoginHistory(
                user_id=user.id,
                ip="unknown",
                browser="unknown",
                os="unknown",
                device="unknown",
            )
            session.add(history)
            session.commit()
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Generate tokens
        access_token_jti = f"at_{secrets.token_urlsafe(32)}"
        refresh_token_jti = f"rt_{secrets.token_urlsafe(32)}"
        access_token = jwt.encode(
            {"sub": user.id, "jti": access_token_jti, "exp": datetime.utcnow() + timedelta(minutes=1440)},
            Config.JWT_SECRET,
            algorithm="HS256"
        )
        refresh_token = jwt.encode(
            {"sub": user.id, "jti": refresh_token_jti, "exp": datetime.utcnow() + timedelta(days=7)},
            Config.JWT_SECRET,
            algorithm="HS256"
        )

        # Create session
        user_session = UserSession(
            user_id=user.id,
            access_token_jti=access_token_jti,
            refresh_token_jti=refresh_token_jti,
            device_info=login_data.get("device_info", {}),
            ip_address="unknown",
            user_agent="unknown",
            status="active",
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        session.add(user_session)

        # Update user
        user.last_login = datetime.utcnow()
        session.commit()

        return {
            "success": True,
            "message": "Login successful",
            "user_id": user.id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": user_session.id,
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/forgot-password")
async def forgot_password(forgot_data: dict):
    """Request password reset"""
    session = get_db_session()
    try:
        email = forgot_data["email"].lower()
        
        # Find user
        user = session.query(User).filter(User.email == email).first()
        
        if not user:
            # Return success even if user doesn't exist for security
            return {"success": True, "message": "If the email exists, a reset link has been sent"}

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_hash = pbkdf2_sha256.hash(reset_token)
        
        # Store reset
        reset = PasswordReset(
            user_id=user.id,
            token=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=15),
        )
        session.add(reset)
        session.commit()

        # Send email
        reset_link = f"{Config.FRONTEND_URL}/reset-password?token={reset_token}"
        EmailService().send_password_reset(email, reset_link)

        return {"success": True, "message": "Password reset email sent", "token": reset_token}

    except Exception as e:
        session.rollback()
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.get("/reset-password/verify")
async def verify_reset_token(token: str = Query(...)):
    """Verify password reset token"""
    session = get_db_session()
    try:
        token_hash = pbkdf2_sha256.hash(token)
        reset = session.query(PasswordReset).filter(
            PasswordReset.token == token_hash,
            PasswordReset.used == False,
        ).first()

        if not reset:
            return {"success": False, "message": "Invalid or expired token"}

        if reset.expires_at < datetime.utcnow():
            return {"success": False, "message": "Token expired"}

        return {"success": True, "message": "Token valid", "user_id": reset.user_id}

    except Exception as e:
        logger.error(f"Verify reset token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/reset-password")
async def reset_password(reset_data: dict):
    """Reset password with token"""
    session = get_db_session()
    try:
        token_hash = pbkdf2_sha256.hash(reset_data["token"])
        reset = session.query(PasswordReset).filter(
            PasswordReset.token == token_hash,
            PasswordReset.used == False,
        ).first()

        if not reset:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        if reset.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expired")

        # Find user
        user = session.query(User).filter(User.id == reset.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update password
        user.password_hash = pbkdf2_sha256.hash(reset_data["new_password"])
        reset.used = True

        # Invalidate other sessions
        session.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.status == "active",
        ).update({"status": "revoked"})

        session.commit()

        return {"success": True, "message": "Password reset successful"}

    except Exception as e:
        session.rollback()
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.get("/verify-email")
async def verify_email(token: str = Query(...)):
    """Verify email address"""
    session = get_db_session()
    try:
        token_hash = pbkdf2_sha256.hash(token)
        verification = session.query(EmailVerification).filter(
            EmailVerification.token == token_hash,
        ).first()

        if not verification:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        if verification.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expired")

        # Update user
        user = session.query(User).filter(User.id == verification.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.email_verified = True
        user.verification_token = None

        # Mark verification as used
        verification.used = True

        session.commit()

        return {"success": True, "message": "Email verified successfully"}

    except Exception as e:
        session.rollback()
        logger.error(f"Verify email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/logout")
async def logout(logout_data: dict):
    """Logout user"""
    session = get_db_session()
    try:
        user_session = session.query(UserSession).filter(
            UserSession.id == logout_data["session_id"],
            UserSession.status == "active",
        ).first()

        if not user_session:
            raise HTTPException(status_code=404, detail="Session not found")

        user_session.status = "revoked"
        session.commit()

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        session.rollback()
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.post("/refresh")
async def refresh_token(refresh_data: dict):
    """Refresh access token"""
    try:
        payload = jwt.decode(refresh_data["refresh_token"], Config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Invalid token")

        session = get_db_session()
        try:
            user_session = session.query(UserSession).filter(
                UserSession.refresh_token_jti == jti,
                UserSession.status == "active",
            ).first()

            if not user_session or user_session.expires_at < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Session expired")

            # Generate new tokens
            new_access_token_jti = f"at_{secrets.token_urlsafe(32)}"
            new_refresh_token_jti = f"rt_{secrets.token_urlsafe(32)}"
            new_access_token = jwt.encode(
                {"sub": user_id, "jti": new_access_token_jti, "exp": datetime.utcnow() + timedelta(minutes=1440)},
                Config.JWT_SECRET,
                algorithm="HS256"
            )
            new_refresh_token = jwt.encode(
                {"sub": user_id, "jti": new_refresh_token_jti, "exp": datetime.utcnow() + timedelta(days=7)},
                Config.JWT_SECRET,
                algorithm="HS256"
            )

            # Update session
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
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
