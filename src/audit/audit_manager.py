"""
Audit Manager
Complete audit trail for all operations
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from enum import Enum

from database.models import AuditEvent

logger = logging.getLogger(__name__)


class AuditActionType(str, Enum):
    """All auditable action types"""
    # Workflow actions
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    
    # Execution actions
    STEP_EXECUTED = "step_executed"
    STEP_FAILED = "step_failed"
    STEP_VERIFIED = "step_verified"
    
    # Agent actions
    AGENT_CALLED = "agent_called"
    AGENT_RESPONSE_RECEIVED = "agent_response_received"
    
    # Device actions
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_COMMAND_SENT = "device_command_sent"
    DEVICE_STATE_CHANGED = "device_state_changed"
    
    # Approval actions
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    
    # Security actions
    SECRET_ACCESSED = "secret_accessed"
    PERMISSION_DENIED = "permission_denied"
    CREDENTIAL_USED = "credential_used"
    
    # System actions
    RETRY_ATTEMPTED = "retry_attempted"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    FALLBACK_ACTIVATED = "fallback_activated"


class AuditResourceType(str, Enum):
    """Resource types being audited"""
    WORKFLOW = "workflow"
    WORKFLOW_STEP = "workflow_step"
    AGENT = "agent"
    DEVICE = "device"
    APPROVAL = "approval"
    SECRET = "secret"
    USER = "user"


class AuditResult(str, Enum):
    """Result of audited action"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AuditManager:
    """Centralized audit logging"""
    
    def __init__(self, session):
        self.session = session
        self.pending_events: List[Dict[str, Any]] = []
    
    async def log_action(
        self,
        user_id: str,
        action_type: AuditActionType,
        resource_type: AuditResourceType,
        resource_id: str,
        workflow_id: str,
        result: AuditResult,
        details: Dict[str, Any],
        device_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> AuditEvent:
        """
        Log an audit event
        
        Args:
            user_id: User performing action
            action_type: Type of action
            resource_type: Resource type affected
            resource_id: Resource ID
            workflow_id: Associated workflow
            result: Result of action
            details: Additional details
            device_id: Associated device
            agent_id: Associated agent
            
        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            user_id=user_id,
            action_type=action_type.value,
            resource_type=resource_type.value,
            resource_id=resource_id,
            device_id=device_id,
            agent_id=agent_id,
            action_details=details,
            result=result.value,
            timestamp=datetime.utcnow(),
        )
        
        self.session.add(event)
        self.session.commit()
        
        logger.info(
            f"Audit: {user_id} {action_type.value} {resource_type.value} "
            f"{resource_id} -> {result.value}"
        )
        
        return event
    
    async def log_workflow_created(
        self,
        user_id: str,
        workflow_id: str,
        command: str,
        intent: str,
    ) -> AuditEvent:
        """Log workflow creation"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.WORKFLOW_CREATED,
            resource_type=AuditResourceType.WORKFLOW,
            resource_id=workflow_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "command": command,
                "intent": intent,
            },
        )
    
    async def log_workflow_completed(
        self,
        user_id: str,
        workflow_id: str,
        duration_ms: int,
    ) -> AuditEvent:
        """Log workflow completion"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.WORKFLOW_COMPLETED,
            resource_type=AuditResourceType.WORKFLOW,
            resource_id=workflow_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "duration_ms": duration_ms,
            },
        )
    
    async def log_workflow_failed(
        self,
        user_id: str,
        workflow_id: str,
        error: str,
    ) -> AuditEvent:
        """Log workflow failure"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.WORKFLOW_FAILED,
            resource_type=AuditResourceType.WORKFLOW,
            resource_id=workflow_id,
            workflow_id=workflow_id,
            result=AuditResult.FAILURE,
            details={
                "error": error,
            },
        )
    
    async def log_step_executed(
        self,
        user_id: str,
        workflow_id: str,
        step_id: str,
        step_type: str,
        duration_ms: int,
    ) -> AuditEvent:
        """Log step execution"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.STEP_EXECUTED,
            resource_type=AuditResourceType.WORKFLOW_STEP,
            resource_id=step_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "step_type": step_type,
                "duration_ms": duration_ms,
            },
        )
    
    async def log_agent_called(
        self,
        user_id: str,
        workflow_id: str,
        agent_id: str,
        agent_type: str,
        input_size: int,
    ) -> AuditEvent:
        """Log agent call"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.AGENT_CALLED,
            resource_type=AuditResourceType.AGENT,
            resource_id=agent_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "agent_type": agent_type,
                "input_size": input_size,
            },
            agent_id=agent_id,
        )
    
    async def log_device_command(
        self,
        user_id: str,
        workflow_id: str,
        device_id: str,
        command: str,
        status: str,
    ) -> AuditEvent:
        """Log device command execution"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.DEVICE_COMMAND_SENT,
            resource_type=AuditResourceType.DEVICE,
            resource_id=device_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS if status == "success" else AuditResult.FAILURE,
            details={
                "command": command,
                "status": status,
            },
            device_id=device_id,
        )
    
    async def log_approval_requested(
        self,
        user_id: str,
        workflow_id: str,
        approval_id: str,
        approval_type: str,
    ) -> AuditEvent:
        """Log approval request"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.APPROVAL_REQUESTED,
            resource_type=AuditResourceType.APPROVAL,
            resource_id=approval_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "approval_type": approval_type,
            },
        )
    
    async def log_approval_granted(
        self,
        user_id: str,
        workflow_id: str,
        approval_id: str,
    ) -> AuditEvent:
        """Log approval grant"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.APPROVAL_GRANTED,
            resource_type=AuditResourceType.APPROVAL,
            resource_id=approval_id,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={},
        )
    
    async def log_secret_accessed(
        self,
        user_id: str,
        workflow_id: str,
        secret_type: str,
    ) -> AuditEvent:
        """Log secret access"""
        return await self.log_action(
            user_id=user_id,
            action_type=AuditActionType.SECRET_ACCESSED,
            resource_type=AuditResourceType.SECRET,
            resource_id=secret_type,
            workflow_id=workflow_id,
            result=AuditResult.SUCCESS,
            details={
                "secret_type": secret_type,
            },
        )
    
    async def get_audit_log(
        self,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        action_type: Optional[AuditActionType] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """Query audit log"""
        query = self.session.query(AuditEvent)
        
        if user_id:
            query = query.filter(AuditEvent.user_id == user_id)
        if workflow_id:
            query = query.filter(AuditEvent.workflow_id == workflow_id)
        if action_type:
            query = query.filter(AuditEvent.action_type == action_type.value)
        
        return query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()


# Global instance (will be initialized with session)
audit_manager = None


def get_audit_manager(session=None) -> AuditManager:
    """Get or create audit manager"""
    global audit_manager
    if audit_manager is None and session:
        audit_manager = AuditManager(session)
    return audit_manager
