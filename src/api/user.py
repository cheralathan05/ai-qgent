"""
APA-OS User API - Complete user management with signup, login, email verification, password reset, and session management
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import secrets
import re

from passlib.hash import pbkdf2_sha256

import jwt

from database.models import User
from database.auth_models import UserSession, EmailVerification, PasswordReset
from services.auth_service import (
    hash_password, verify_password, generate_jwt_token,
    generate_access_token_jti, generate_refresh_token_jti,
    generate_email_verification_token, generate_reset_token,
    generate_token_hash, AuthResult
)
from services.email_service import EmailService
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str
    device_name: Optional[str] = None
    device_ip: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


# ==================== Auth APIs ====================

@router.post("/register", status_code=201)
async def register(request: RegisterRequest):
    """Create new user account"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().signup(
            name=request.name,
            email=request.email,
            password=request.password,
        )
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return {
            "success": True,
            "message": "Account created. Check your email.",
            "user_id": result.user_id,
        }
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(request: LoginRequest):
    """Authenticate user and return tokens"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().login(
            email=request.email,
            password=request.password,
            device_info={"device_name": request.device_name} if request.device_name else None,
        )
        if not result.success:
            if "Email not verified" in result.message:
                raise HTTPException(status_code=403, detail=result.message)
            raise HTTPException(status_code=401, detail=result.message)

        from database.models import User
        from database.connection import get_db_session
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == result.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return {
                "success": True,
                "message": result.message,
                "user": {
                    "id": user.id,
                    "full_name": user.name,
                    "email": user.email,
                    "email_verified": user.email_verified,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                },
                "accessToken": result.access_token,
                "refreshToken": result.refresh_token,
                "session_id": result.session_id,
                "expires_at": result.expires_at.isoformat() if result.expires_at else None,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
async def verify_email(token: str = Query(...)):
    """Verify email address with token"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().verify_email(token)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return {"success": True, "message": "Email verified successfully"}
    except Exception as e:
        logger.error(f"Verify email error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """Send password reset email"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().forgot_password(request.email)
        return {
            "success": True,
            "message": "Password reset email sent.",
            "token": result.token,
        }
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reset-password/verify")
async def verify_reset_token(token: str = Query(...)):
    """Verify a password reset token"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().verify_reset_token(token)
        return {"success": result.success, "message": result.message}
    except Exception as e:
        logger.error(f"Verify reset token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password with token"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().reset_password(
            request.token, request.new_password
        )
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return {"success": True, "message": "Password reset successful"}
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh access token"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().refresh_tokens(request.refresh_token)
        if not result.success:
            raise HTTPException(status_code=401, detail=result.message)
        return {
            "success": True,
            "accessToken": result.access_token,
            "refreshToken": result.refresh_token,
            "expires_at": datetime.utcnow() + timedelta(days=1),
        }
    except Exception as e:
        logger.error(f"Refresh token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def logout(session_id: str = Body(..., embed=True)):
    """Logout and revoke session"""
    auth_service = None
    try:
        auth_service = __import__("services.auth_service", fromlist=["AuthService"])
        AuthServiceClass = auth_service.AuthService
        result = AuthServiceClass().logout(session_id)
        return {"success": result.success, "message": result.message}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(token: str = Query(...)):
    """Get current user info"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise HTTPException(status_code=401, detail="Invalid token")

        from database.connection import get_db_session
        db = get_db_session()
        try:
            from database.auth_models import UserSession
            user_session = db.query(UserSession).filter(
                UserSession.access_token_jti == jti,
                UserSession.status == "active",
            ).first()

            if not user_session:
                raise HTTPException(status_code=401, detail="Invalid session")

            from database.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            return {"success": True, "user": {
                "id": user.id,
                "full_name": user.name,
                "email": user.email,
                "email_verified": user.email_verified,
                "status": user.status,
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }}
        finally:
            db.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Get me error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
