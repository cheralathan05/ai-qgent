"""
APA-OS Authentication API - Complete auth endpoints matching Phase 1 spec
POST /api/auth/register, GET /api/auth/verify, POST /api/auth/login, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import secrets

from services.auth_service import get_auth_service
from services.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
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


@router.post("/register", status_code=201)
async def register(request: RegisterRequest):
    """Create new user account"""
    service = get_auth_service()
    result = service.signup(
        name=request.full_name,
        email=request.email,
        password=request.password,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": "Account Created. Check your email.",
        "user_id": result.user_id,
    }


@router.get("/verify")
async def verify_email(token: str = Query(...)):
    """Verify email address with token"""
    service = get_auth_service()
    result = service.verify_email(token)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "message": "Email Verified"}


@router.post("/login")
async def login(request: LoginRequest, _: None = Depends(rate_limit(10, 300))):
    """Authenticate user and return tokens"""
    service = get_auth_service()
    result = service.login(
        email=request.email,
        password=request.password,
        device_info={"device_name": request.device_name} if request.device_name else None,
    )
    if not result.success:
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
                "full_name": user.full_name,
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


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Refresh access token"""
    service = get_auth_service()
    result = service.refresh_tokens(request.refresh_token)
    if not result.success:
        raise HTTPException(status_code=401, detail=result.message)
    return {
        "success": True,
        "accessToken": result.access_token,
        "refreshToken": result.refresh_token,
        "expires_at": result.expires_at.isoformat() if result.expires_at else None,
    }


@router.post("/logout")
async def logout(session_id: str = Body(..., embed=True)):
    """Logout and revoke session"""
    service = get_auth_service()
    result = service.logout(session_id)
    return {"success": result.success, "message": result.message}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, _: None = Depends(rate_limit(3, 600))):
    """Send password reset email"""
    service = get_auth_service()
    result = service.forgot_password(request.email)
    return {"success": True, "message": result.message}


@router.get("/reset-password/verify")
async def verify_reset_token(token: str = Query(...)):
    """Verify a password reset token"""
    service = get_auth_service()
    result = service.verify_reset_token(token)
    return {"success": result.success, "message": result.message}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Reset password with token"""
    service = get_auth_service()
    result = service.reset_password(request.token, request.new_password)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {"success": True, "message": "Password reset successful"}


class ResendVerificationRequest(BaseModel):
    email: str


@router.post("/resend-verification")
async def resend_verification(request: ResendVerificationRequest):
    """Resend verification email"""
    service = get_auth_service()
    result = service.resend_verification(request.email)
    return {"success": True, "message": result.message}


@router.get("/me")
async def get_me(token: str = Query(...)):
    """Get current user info"""
    service = get_auth_service()
    user_info = service.validate_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    from database.models import User
    from database.connection import get_db_session
    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == user_info["user_id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "success": True,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "email_verified": user.email_verified,
                "status": user.status,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }
    finally:
        db.close()
