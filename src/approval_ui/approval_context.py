"""
Approval UI & Context Builder
Prepares approval requests for human review
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ApprovalPayload:
    """What needs approval"""
    action_type: str  # send_message, make_call, send_payment, etc.
    data: Dict[str, Any]
    requires_immediate_decision: bool = False
    expiry_seconds: int = 300


@dataclass
class ApprovalPreview:
    """Human-readable preview"""
    headline: str
    details: List[str]
    warning: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ApprovalContext:
    """Full context for approval decision"""
    workflow_id: str
    user_id: str
    timestamp: datetime
    payload: ApprovalPayload
    preview: ApprovalPreview
    explanation: str
    confidence_score: float
    source: str  # which agent made this decision


class ApprovalPayloadBuilder:
    """Builds structured approval payloads"""
    
    @staticmethod
    def build_send_message(
        recipient: str,
        message: str,
        platform: str,
        confidence: float = 0.9,
    ) -> ApprovalPayload:
        """Build approval for sending message"""
        return ApprovalPayload(
            action_type="send_message",
            data={
                "recipient": recipient,
                "message": message,
                "platform": platform,
                "character_count": len(message),
            },
            requires_immediate_decision=False,
            expiry_seconds=600,  # 10 minutes to decide
        )
    
    @staticmethod
    def build_make_call(
        recipient: str,
        call_type: str = "voice",
        confidence: float = 0.9,
    ) -> ApprovalPayload:
        """Build approval for making call"""
        return ApprovalPayload(
            action_type="make_call",
            data={
                "recipient": recipient,
                "call_type": call_type,
            },
            requires_immediate_decision=True,
            expiry_seconds=30,  # 30 seconds to decide
        )
    
    @staticmethod
    def build_payment(
        recipient: str,
        amount: float,
        currency: str,
        reason: str,
        confidence: float = 0.8,
    ) -> ApprovalPayload:
        """Build approval for payment"""
        return ApprovalPayload(
            action_type="payment",
            data={
                "recipient": recipient,
                "amount": amount,
                "currency": currency,
                "reason": reason,
            },
            requires_immediate_decision=False,
            expiry_seconds=300,
        )
    
    @staticmethod
    def build_app_permission(
        app_name: str,
        permission: str,
        reason: str,
        confidence: float = 0.9,
    ) -> ApprovalPayload:
        """Build approval for app permission"""
        return ApprovalPayload(
            action_type="app_permission",
            data={
                "app_name": app_name,
                "permission": permission,
                "reason": reason,
            },
            requires_immediate_decision=False,
            expiry_seconds=300,
        )
    
    @staticmethod
    def build_data_sharing(
        app_name: str,
        data_type: str,
        recipient: str,
        confidence: float = 0.85,
    ) -> ApprovalPayload:
        """Build approval for data sharing"""
        return ApprovalPayload(
            action_type="data_sharing",
            data={
                "app_name": app_name,
                "data_type": data_type,
                "recipient": recipient,
            },
            requires_immediate_decision=False,
            expiry_seconds=300,
        )


class ApprovalPreviewBuilder:
    """Builds human-readable preview"""
    
    @staticmethod
    def build_send_message_preview(
        recipient: str,
        message: str,
        platform: str,
    ) -> ApprovalPreview:
        """Preview for message"""
        return ApprovalPreview(
            headline=f"Send message to {recipient} on {platform}",
            details=[
                f"To: {recipient}",
                f"Message: {message[:100]}{'...' if len(message) > 100 else ''}",
                f"Platform: {platform}",
            ],
            warning=None if len(message) < 500 else "Long message",
            suggestion=None if "@" not in message else "Message contains @ mention",
        )
    
    @staticmethod
    def build_make_call_preview(
        recipient: str,
        call_type: str,
    ) -> ApprovalPreview:
        """Preview for call"""
        return ApprovalPreview(
            headline=f"Call {recipient}",
            details=[
                f"Recipient: {recipient}",
                f"Type: {call_type}",
            ],
            warning="Calls will be charged per your plan",
            suggestion=None,
        )
    
    @staticmethod
    def build_payment_preview(
        recipient: str,
        amount: float,
        currency: str,
        reason: str,
    ) -> ApprovalPreview:
        """Preview for payment"""
        return ApprovalPreview(
            headline=f"Send {currency} {amount} to {recipient}",
            details=[
                f"Recipient: {recipient}",
                f"Amount: {currency} {amount:.2f}",
                f"Reason: {reason}",
            ],
            warning="⚠️ MONEY TRANSFER - Verify recipient carefully",
            suggestion="Double-check recipient address before approving",
        )
    
    @staticmethod
    def build_app_permission_preview(
        app_name: str,
        permission: str,
        reason: str,
    ) -> ApprovalPreview:
        """Preview for permission"""
        permission_labels = {
            "camera": "📷 Camera",
            "microphone": "🎤 Microphone",
            "location": "📍 Location",
            "contacts": "📇 Contacts",
            "files": "📁 Files",
            "calendar": "📅 Calendar",
            "photos": "🖼️ Photos",
        }
        
        permission_display = permission_labels.get(permission, permission)
        
        return ApprovalPreview(
            headline=f"Allow {app_name} to access {permission_display}",
            details=[
                f"App: {app_name}",
                f"Permission: {permission_display}",
                f"Reason: {reason}",
            ],
            warning="⚠️ PRIVACY - Grant only if necessary",
            suggestion=None,
        )


class ApprovalExplainer:
    """Explains why approval is needed"""
    
    @staticmethod
    def explain_send_message(
        platform: str,
        recipient: str,
        confidence: float,
    ) -> str:
        """Explain message approval"""
        return (
            f"The AI will send a message to {recipient} on {platform}. "
            f"This requires your confirmation to ensure accuracy. "
            f"(Confidence: {confidence*100:.0f}%)"
        )
    
    @staticmethod
    def explain_make_call(
        recipient: str,
        confidence: float,
    ) -> str:
        """Explain call approval"""
        return (
            f"The AI will initiate a call to {recipient}. "
            f"Calls may incur charges based on your plan. "
            f"(Confidence: {confidence*100:.0f}%)"
        )
    
    @staticmethod
    def explain_payment(
        amount: float,
        currency: str,
        recipient: str,
        confidence: float,
    ) -> str:
        """Explain payment approval"""
        return (
            f"The AI will send {currency} {amount:.2f} to {recipient}. "
            f"This is a financial transaction and requires your explicit approval. "
            f"(Confidence: {confidence*100:.0f}%)"
        )
    
    @staticmethod
    def explain_app_permission(
        app_name: str,
        permission: str,
        reason: str,
        confidence: float,
    ) -> str:
        """Explain permission approval"""
        return (
            f"The AI needs to grant {app_name} access to {permission} "
            f"to: {reason}. (Confidence: {confidence*100:.0f}%)"
        )


class ApprovalContextBuilder:
    """Builds complete approval context"""
    
    def __init__(self, session=None):
        self.session = session
    
    async def build_context(
        self,
        workflow_id: str,
        user_id: str,
        payload: ApprovalPayload,
        preview: ApprovalPreview,
        explanation: str,
        confidence: float,
        source: str,
    ) -> ApprovalContext:
        """
        Build complete approval context
        
        Args:
            workflow_id: Associated workflow
            user_id: User who needs to approve
            payload: What needs approval
            preview: Human-readable preview
            explanation: Why approval needed
            confidence: AI confidence in decision
            source: Which agent made decision
            
        Returns:
            ApprovalContext
        """
        return ApprovalContext(
            workflow_id=workflow_id,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            payload=payload,
            preview=preview,
            explanation=explanation,
            confidence_score=confidence,
            source=source,
        )
    
    async def save_approval_request(
        self,
        context: ApprovalContext,
    ) -> str:
        """
        Save approval request to database
        
        Args:
            context: Approval context
            
        Returns:
            Approval ID
        """
        from database.models import ApprovalAction
        
        approval_id = str(uuid.uuid4())
        
        approval = ApprovalAction(
            id=approval_id,
            workflow_id=context.workflow_id,
            approval_type=context.payload.action_type,
            payload=context.payload.data,
            preview={
                "headline": context.preview.headline,
                "details": context.preview.details,
                "warning": context.preview.warning,
                "suggestion": context.preview.suggestion,
            },
            explanation=context.explanation,
            requested_at=context.timestamp,
        )
        
        if self.session:
            self.session.add(approval)
            self.session.commit()
        
        logger.info(f"Created approval request: {approval_id}")
        
        return approval_id


# Global instance
approval_context_builder = None


def get_approval_context_builder(session=None) -> ApprovalContextBuilder:
    """Get or create approval context builder"""
    global approval_context_builder
    if approval_context_builder is None:
        approval_context_builder = ApprovalContextBuilder(session)
    return approval_context_builder
