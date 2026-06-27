"""
APA-OS Pairing API
Endpoints for QR pairing, device approval, and trust verification
"""

from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from services.pairing_service import get_pairing_service, PairingResult
from services.auth_service import get_auth_service

router = APIRouter(prefix="/api/pair", tags=["Pairing"])

class PairingRequest(BaseModel):
    qr_token: str
    device_info: Dict[str, Any]

class ApprovalRequest(BaseModel):
    session_id: str

class TrustRequest(BaseModel):
    device_id: str

@router.post("/session")
async def create_pairing_session(user_id: str = Depends(get_auth_service().validate_token)):
    """Step 1: Create pairing session (Desktop)"""
    service = get_pairing_service()
    result = service.create_pairing_session(user_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "pair_code": result.pair_code,
        "qr_token": result.token,
        "message": result.message
    }

@router.post("/request")
async def request_pairing(request: PairingRequest):
    """Step 2: Request pairing via QR (Phone)"""
    service = get_pairing_service()
    result = service.request_pairing(request.qr_token, request.device_info)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "session_id": result.data.get("session_id"),
        "message": result.message
    }

@router.post("/approve")
async def approve_pairing(request: ApprovalRequest, user_id: str = Depends(get_auth_service().validate_token)):
    """Step 3: Approve pairing (Desktop)"""
    service = get_pairing_service()
    result = service.approve_pairing(request.session_id, user_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "device_id": result.device_id,
        "websocket_token": result.token,
        "message": result.message
    }

@router.post("/trust")
async def verify_trust(request: TrustRequest, user_id: str = Depends(get_auth_service().validate_token)):
    """Step 4: Confirm trust (Phone)"""
    service = get_pairing_service()
    result = service.verify_trust(request.device_id, user_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return {
        "success": True,
        "message": result.message
    }
