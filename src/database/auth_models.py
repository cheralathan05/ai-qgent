"""
APA-OS Auth & Device Lifecycle Models
Complete schema for authentication, device pairing, trust, permissions, and automation
"""

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    Text, JSON, Enum, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from database.models import Base


# ==================== Auth Enums ====================

class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class DevicePairingStatus(str, enum.Enum):
    PENDING = "pending"
    SCANNED = "scanned"
    PAIRED = "paired"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class TrustLevel(str, enum.Enum):
    NONE = "none"
    PENDING = "pending"
    TRUSTED_ONCE = "trusted_once"
    ALWAYS_TRUSTED = "always_trusted"
    REJECTED = "rejected"


class PermissionStatus(str, enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    NOT_REQUESTED = "not_requested"


class CapabilityStatus(str, enum.Enum):
    READY = "ready"
    NOT_READY = "not_ready"
    ERROR = "error"
    UNKNOWN = "unknown"


class AutomationTriggerType(str, enum.Enum):
    MESSAGE_RECEIVED = "message_received"
    APP_OPENED = "app_opened"
    TIME_BASED = "time_based"
    NOTIFICATION = "notification"
    DEVICE_CONNECTED = "device_connected"
    MANUAL = "manual"
    WEBHOOK = "webhook"


# ==================== Auth Models ====================

class UserSession(Base):
    """Active user session with JWT tracking"""
    __tablename__ = "user_sessions"

    id = Column(String(255), primary_key=True, default=lambda: f"ses_{uuid.uuid4().hex[:16]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    access_token_jti = Column(String(255), nullable=False, unique=True)
    refresh_token_jti = Column(String(255), nullable=False, unique=True)
    device_info = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE, index=True)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_session_user_status", "user_id", "status"),
    )


class EmailVerification(Base):
    """Email verification tokens"""
    __tablename__ = "email_verifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False)
    verified = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PasswordReset(Base):
    """Password reset tokens"""
    __tablename__ = "password_resets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True)
    used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    """Extended user profile"""
    __tablename__ = "user_profiles"

    id = Column(String(255), primary_key=True, default=lambda: f"prf_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, unique=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    timezone = Column(String(100), default="UTC")
    language = Column(String(10), default="en")
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserWorkspace(Base):
    """User workspace for settings and defaults"""
    __tablename__ = "user_workspaces"

    id = Column(String(255), primary_key=True, default=lambda: f"ws_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, unique=True)
    workspace_name = Column(String(255), default="Default Workspace")
    settings = Column(JSON, default=dict)
    ai_profile = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== Device Pairing Models ====================

class DevicePairingSession(Base):
    """QR/USB/Wireless pairing session"""
    __tablename__ = "device_pairing_sessions"

    id = Column(String(255), primary_key=True, default=lambda: f"prs_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    pair_code = Column(String(255), nullable=False, unique=True)
    pairing_type = Column(String(50), nullable=False)  # qr, usb, wireless
    status = Column(Enum(DevicePairingStatus), default=DevicePairingStatus.PENDING, index=True)
    device_ip = Column(String(45), nullable=True)
    device_port = Column(Integer, nullable=True)
    device_serial = Column(String(255), nullable=True)
    device_info = Column(JSON, default=dict)
    trust_code = Column(String(10), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    paired_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_pairing_user_status", "user_id", "status"),
    )


class RegisteredDevice(Base):
    """Complete device record with all metadata"""
    __tablename__ = "registered_devices"

    id = Column(String(255), primary_key=True, default=lambda: f"dev_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)  # android, windows, ios
    serial = Column(String(255), nullable=True, index=True)
    android_version = Column(String(50), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    battery_level = Column(Integer, nullable=True)
    connection_type = Column(String(50), nullable=True)  # usb, wireless, qr
    connection_ip = Column(String(45), nullable=True)
    connection_port = Column(Integer, nullable=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    agent_installed = Column(Boolean, default=False)
    agent_version = Column(String(50), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_device_user_type", "user_id", "device_type"),
    )


# ==================== Trust Models ====================

class TrustedDevice(Base):
    """Device trust binding"""
    __tablename__ = "trusted_devices"

    id = Column(String(255), primary_key=True, default=lambda: f"trt_{uuid.uuid4().hex[:12]}")
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    trust_level = Column(Enum(TrustLevel), default=TrustLevel.PENDING)
    certificate = Column(Text, nullable=True)
    secret_key = Column(String(512), nullable=True)
    trust_token = Column(String(512), nullable=True)
    fingerprint = Column(String(255), nullable=True)
    trusted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("device_id", "user_id", name="uq_trusted_device_user"),
    )


# ==================== Permission Models ====================

class DevicePermission(Base):
    """Device permission state"""
    __tablename__ = "device_permissions"

    id = Column(String(255), primary_key=True, default=lambda: f"prm_{uuid.uuid4().hex[:12]}")
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    permission_name = Column(String(100), nullable=False)  # screen_capture, navigation, notifications, etc.
    status = Column(Enum(PermissionStatus), default=PermissionStatus.NOT_REQUESTED)
    granted_at = Column(DateTime, nullable=True)
    denied_at = Column(DateTime, nullable=True)
    android_permission = Column(String(255), nullable=True)  # actual Android permission string
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("device_id", "permission_name", name="uq_device_permission"),
    )


# ==================== Capability Models ====================

class DeviceCapability(Base):
    """Device AI capability status"""
    __tablename__ = "device_capabilities"

    id = Column(String(255), primary_key=True, default=lambda: f"cap_{uuid.uuid4().hex[:12]}")
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=False, index=True)
    capability_name = Column(String(100), nullable=False)  # adb, ocr, screenshot, navigation, etc.
    status = Column(Enum(CapabilityStatus), default=CapabilityStatus.UNKNOWN)
    score = Column(Float, nullable=True)  # 0.0 to 1.0
    details = Column(JSON, default=dict)
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("device_id", "capability_name", name="uq_device_capability"),
    )


# ==================== Agent Runtime Models ====================

class DeviceAgent(Base):
    """Active agent on a device"""
    __tablename__ = "device_agents"

    id = Column(String(255), primary_key=True, default=lambda: f"agt_{uuid.uuid4().hex[:12]}")
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    agent_type = Column(String(100), nullable=False)  # voice, ocr, navigation, memory, automation, notification
    agent_name = Column(String(255), nullable=False)
    status = Column(String(50), default="stopped")  # running, stopped, error
    config = Column(JSON, default=dict)
    last_heartbeat = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agent_device_type", "device_id", "agent_type"),
    )


# ==================== Automation Models ====================

class AutomationRule(Base):
    """Automation workflow rule"""
    __tablename__ = "automation_rules"

    id = Column(String(255), primary_key=True, default=lambda: f"auto_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    trigger_type = Column(Enum(AutomationTriggerType), nullable=False)
    trigger_config = Column(JSON, nullable=False, default=dict)
    conditions = Column(JSON, default=list)
    actions = Column(JSON, nullable=False, default=list)
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    last_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationRun(Base):
    """Automation execution record"""
    __tablename__ = "automation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(String(255), ForeignKey("automation_rules.id"), nullable=False, index=True)
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False)
    device_id = Column(String(255), nullable=True)
    trigger_data = Column(JSON, default=dict)
    status = Column(String(50), nullable=False)  # running, completed, failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)


# ==================== Notification Models ====================

class NotificationRecord(Base):
    """System notification"""
    __tablename__ = "notification_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(100), nullable=False)  # info, warning, error, success
    category = Column(String(100), nullable=True)  # auth, device, automation, system
    data = Column(JSON, default=dict)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
    )


# ==================== Audit Models ====================

class SystemAuditLog(Base):
    """Complete system audit trail"""
    __tablename__ = "system_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(255), nullable=True)
    device_id = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    result = Column(String(20), nullable=False)  # success, failure
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )


# ==================== Device Heartbeat ====================

class DeviceHeartbeat(Base):
    """Device live heartbeat data"""
    __tablename__ = "device_heartbeats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(255), ForeignKey("registered_devices.id"), nullable=False, index=True)
    battery_level = Column(Integer, nullable=True)
    battery_charging = Column(Boolean, default=False)
    foreground_app = Column(String(255), nullable=True)
    screen_state = Column(String(50), nullable=True)  # on, off, dozing
    lock_state = Column(String(50), nullable=True)  # locked, unlocked
    network_type = Column(String(50), nullable=True)  # wifi, mobile, none
    network_strength = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    storage_free_gb = Column(Float, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_heartbeat_device_time", "device_id", "recorded_at"),
    )
