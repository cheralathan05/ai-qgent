"""
PostgreSQL Database Models for APA-OS Backend
Complete schema for all operational layers
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    Text, JSON, Enum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FailureType(str, enum.Enum):
    OLLAMA_UNAVAILABLE = "ollama_unavailable"
    DEVICE_DISCONNECTED = "device_disconnected"
    ADB_FAILURE = "adb_failure"
    WORKFLOW_TIMEOUT = "workflow_timeout"
    NETWORK_FAILURE = "network_failure"
    INVALID_AGENT_RESPONSE = "invalid_agent_response"
    PERMISSION_DENIED = "permission_denied"
    APP_NOT_FOUND = "app_not_found"
    DEVICE_LOCKED = "device_locked"
    VERIFICATION_FAILED = "verification_failed"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    MANUAL_REQUIRED = "manual_required"


class Workflow(Base):
    """Main workflow execution record"""
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    command = Column(Text, nullable=False)
    intent = Column(String(255), nullable=False, index=True)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING, index=True)
    
    plan_json = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    device_id = Column(String(255), nullable=True, index=True)
    agent_id = Column(String(255), nullable=True)
    
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(Enum(ApprovalStatus), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_workflow_user_time', 'user_id', 'start_time'),
        Index('idx_workflow_status_device', 'status', 'device_id'),
    )


class User(Base):
    """Application user record"""
    __tablename__ = "users"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DeviceRecord(Base):
    """Registered device record"""
    __tablename__ = "devices"

    id = Column(String(255), primary_key=True)
    device_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommandRecord(Base):
    """Command submission record"""
    __tablename__ = "commands"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    command_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionRecord(Base):
    """Execution record tied to workflow"""
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    result = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowState(Base):
    """Current workflow state snapshot"""
    __tablename__ = "workflow_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    state_name = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    current_step = Column(Integer, nullable=True)
    state_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeviceAction(Base):
    """Low-level device action record"""
    __tablename__ = "device_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    device_id = Column(String(255), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    action_data = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class Mission(Base):
    """Mission record for workflows"""
    __tablename__ = "missions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    """User notification record"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentState(Base):
    """Agent state and context storage"""
    __tablename__ = "agent_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    state_name = Column(String(100), nullable=False)
    state_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowStep(Base):
    """Individual step within a workflow"""
    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING, index=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_workflow_step_workflow', 'workflow_id', 'step_number'),
    )


class ExecutionStep(Base):
    """Low-level execution details"""
    __tablename__ = "execution_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_step_id = Column(String(36), ForeignKey('workflow_steps.id'), nullable=False)
    execution_sequence = Column(Integer, nullable=False)
    
    action_type = Column(String(100), nullable=False)
    action_data = Column(JSON, nullable=False)
    
    status = Column(String(20), nullable=False)
    output = Column(JSON, nullable=True)
    
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentRun(Base):
    """Track each agent execution"""
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    agent_type = Column(String(100), nullable=False)
    agent_name = Column(String(255), nullable=False)
    
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=True)
    
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_agent_run_workflow', 'workflow_id', 'agent_type'),
    )


class DeviceState(Base):
    """Current and historical device states"""
    __tablename__ = "device_states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(255), nullable=False, index=True)
    
    is_connected = Column(Boolean, nullable=False)
    is_locked = Column(Boolean, nullable=False)
    battery_level = Column(Integer, nullable=True)
    foreground_app = Column(String(255), nullable=True)
    
    installed_apps = Column(JSON, default=dict)
    permissions_cache = Column(JSON, default=dict)
    
    screenshot_uri = Column(String(500), nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApprovalAction(Base):
    """Human approval records"""
    __tablename__ = "approval_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    approval_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    preview = Column(JSON, nullable=False)
    explanation = Column(Text, nullable=False)
    
    requested_at = Column(DateTime, default=datetime.utcnow)
    decision_at = Column(DateTime, nullable=True)
    decision = Column(Enum(ApprovalStatus), nullable=True)
    decided_by = Column(String(255), nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_approval_workflow_status', 'workflow_id', 'decision'),
    )


class AuditEvent(Base):
    """Complete audit trail"""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    user_id = Column(String(255), nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    device_id = Column(String(255), nullable=True)
    agent_id = Column(String(255), nullable=True)
    
    action_details = Column(JSON, nullable=False)
    result = Column(String(20), nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'timestamp'),
        Index('idx_audit_action_type', 'action_type', 'timestamp'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


class EventSnapshot(Base):
    """Real-time console events"""
    __tablename__ = "event_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    event_type = Column(String(100), nullable=False, index=True)
    event_name = Column(String(255), nullable=False)
    severity = Column(String(20), default="info")
    
    payload = Column(JSON, nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_event_workflow_time', 'workflow_id', 'timestamp'),
    )


class VerificationResult(Base):
    """Execution verification records"""
    __tablename__ = "verification_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_step_id = Column(String(36), ForeignKey('workflow_steps.id'), nullable=False)
    
    verification_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    evidence = Column(JSON, nullable=True)
    screenshot_uri = Column(String(500), nullable=True)
    
    confidence_score = Column(Float, nullable=True)
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SourceRecord(Base):
    """Data provenance tracking"""
    __tablename__ = "source_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    result_id = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=False)
    source_location = Column(String(500), nullable=False)
    
    confidence_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=True)
    
    extracted_data = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemMetrics(Base):
    """System-wide performance metrics"""
    __tablename__ = "system_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    metric_type = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    
    tags = Column(JSON, default=dict)
    metadata_json = Column(JSON, nullable=True)
    
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metrics_type_time', 'metric_type', 'recorded_at'),
    )


class AgentMetrics(Base):
    """Per-agent performance metrics"""
    __tablename__ = "agent_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id = Column(String(36), ForeignKey('agent_runs.id'), nullable=False)
    
    agent_type = Column(String(100), nullable=False, index=True)
    agent_name = Column(String(255), nullable=False)
    
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=False)
    success_rate = Column(Float, nullable=True)
    error_count = Column(Integer, default=0)
    
    memory_used_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowMetrics(Base):
    """Per-workflow performance metrics"""
    __tablename__ = "workflow_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    intent_detection_ms = Column(Float, nullable=True)
    planning_ms = Column(Float, nullable=True)
    execution_ms = Column(Float, nullable=True)
    verification_ms = Column(Float, nullable=True)
    total_duration_ms = Column(Float, nullable=False)
    
    step_count = Column(Integer, nullable=False)
    agent_calls = Column(Integer, nullable=False)
    adb_calls = Column(Integer, nullable=False)
    
    success = Column(Boolean, nullable=False)
    failure_type = Column(Enum(FailureType), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeDocument(Base):
    """Indexed knowledge document"""
    __tablename__ = "knowledge_documents"

    id = Column(String(255), primary_key=True)
    file_name = Column(String(500), nullable=False)
    file_path = Column(Text, nullable=True)
    source_type = Column(String(100), nullable=False, index=True)
    source_name = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeChunk(Base):
    """Indexed text chunk"""
    __tablename__ = "knowledge_chunks"

    id = Column(String(255), primary_key=True)
    document_id = Column(String(255), ForeignKey('knowledge_documents.id'), nullable=False, index=True)
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    embedding_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeSource(Base):
    """Configured knowledge source"""
    __tablename__ = "knowledge_sources"

    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=False, index=True)
    is_connected = Column(Boolean, default=False)
    config_json = Column(JSON, default=dict)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeGraphEntity(Base):
    """Knowledge graph entity"""
    __tablename__ = "knowledge_graph_entities"

    id = Column(String(255), primary_key=True)
    name = Column(String(500), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    properties_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeGraphRelationship(Base):
    """Knowledge graph relationship"""
    __tablename__ = "knowledge_graph_relationships"

    id = Column(String(255), primary_key=True)
    source_id = Column(String(255), ForeignKey('knowledge_graph_entities.id'), nullable=False, index=True)
    target_id = Column(String(255), ForeignKey('knowledge_graph_entities.id'), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False, index=True)
    properties_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class MemoryRecord(Base):
    """Memory storage record"""
    __tablename__ = "memory_records"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    memory_type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    importance = Column(Float, default=0.5)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)


class ConversationRecord(Base):
    """Conversation history record"""
    __tablename__ = "conversation_records"

    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class SearchLog(Base):
    """Search query log"""
    __tablename__ = "search_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=False)
    total_results = Column(Integer, default=0)
    time_ms = Column(Float, nullable=True)
    user_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class FailureRecord(Base):
    """Track all failures with recovery info"""
    __tablename__ = "failure_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String(36), ForeignKey('workflows.id'), nullable=False, index=True)
    
    failure_type = Column(Enum(FailureType), nullable=False, index=True)
    description = Column(Text, nullable=False)
    error_details = Column(JSON, nullable=False)
    
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    recovery_attempted = Column(Boolean, default=False)
    recovery_strategy = Column(String(100), nullable=True)
    recovery_success = Column(Boolean, nullable=True)
    recovery_details = Column(JSON, nullable=True)
    recovery_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_failure_type_time', 'failure_type', 'detected_at'),
    )
