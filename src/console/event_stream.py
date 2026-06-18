"""
Real-time Event Streaming System
Broadcasts all workflow events to console and WebSocket clients
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio
import json
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import uuid
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All possible event types in the system"""
    # Command
    COMMAND_RECEIVED = "command_received"
    
    # Intent Detection
    INTENT_DETECTED = "intent_detected"
    ENTITIES_EXTRACTED = "entities_extracted"
    
    # Device
    DEVICE_SELECTED = "device_selected"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_STATUS_UPDATED = "device_status_updated"
    DEVICE_DISCONNECTED = "device_disconnected"
    DEVICE_LOCKED = "device_locked"
    DEVICE_UNLOCKED = "device_unlocked"
    PHONE_STATE_VERIFIED = "phone_state_verified"
    
    # Planning
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    
    # Execution
    EXECUTION_STARTED = "execution_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    ACTION_EXECUTED = "action_executed"
    APP_OPENED = "app_opened"
    CHAT_OPENED = "chat_opened"
    MESSAGE_SENT = "message_sent"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    
    # Verification
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    VERIFICATION_COMPLETED = "verification_completed"
    
    # Approval
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_EXPIRED = "approval_expired"
    
    # Agents
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    
    # Failures & Recovery
    FAILURE_DETECTED = "failure_detected"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    
    # Screen
    SCREEN_CHANGED = "screen_changed"
    SCREEN_DETECTED = "screen_detected"
    
    # System
    SYSTEM_ALERT = "system_alert"
    SYSTEM_WARNING = "system_warning"
    SYSTEM_INFO = "system_info"


class EventSeverity(str, Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class WorkflowState(str, Enum):
    """Workflow orchestration states"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowEvent:
    """Immutable event record"""
    event_id: str
    workflow_id: str
    event_type: EventType
    severity: EventSeverity
    timestamp: datetime
    payload: Dict[str, Any]
    source: str  # Component that emitted
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict"""
        return {
            "event_id": self.event_id,
            "workflow_id": self.workflow_id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "source": self.source,
            "user_id": self.user_id,
            "device_id": self.device_id,
        }
    
    def to_console_format(self) -> str:
        """Format for console display"""
        icon = self._get_icon()
        timestamp_str = self.timestamp.strftime("%H:%M:%S")
        return f"{icon} [{timestamp_str}] {self.event_type.value.upper()}: {self.payload.get('message', '')}"
    
    def _get_icon(self) -> str:
        """Get console icon based on event type"""
        icons = {
            EventType.COMMAND_RECEIVED: "🎤",
            EventType.INTENT_DETECTED: "🎤",
            EventType.DEVICE_SELECTED: "📱",
            EventType.PLAN_CREATED: "📋",
            EventType.DEVICE_CONNECTED: "📱",
            EventType.EXECUTION_STARTED: "▶️",
            EventType.STEP_COMPLETED: "✅",
            EventType.VERIFICATION_PASSED: "✅",
            EventType.APPROVAL_GRANTED: "👍",
            EventType.RECOVERY_SUCCEEDED: "🔄",
            EventType.EXECUTION_COMPLETED: "🎉",
            EventType.STEP_FAILED: "❌",
            EventType.VERIFICATION_FAILED: "❌",
            EventType.APPROVAL_REJECTED: "👎",
            EventType.FAILURE_DETECTED: "⚠️",
            EventType.EXECUTION_FAILED: "💥",
            EventType.CHAT_OPENED: "💬",
            EventType.MESSAGE_SENT: "✉️",
            EventType.SCREEN_CHANGED: "📺",
            EventType.SCREEN_DETECTED: "🔍",
        }
        return icons.get(self.event_type, "•")


class EventSubscriber(ABC):
    """Abstract base for event subscribers"""
    
    @abstractmethod
    async def on_event(self, event: WorkflowEvent) -> None:
        pass


class ConsoleEventSubscriber(EventSubscriber):
    """Writes events to console"""
    
    async def on_event(self, event: WorkflowEvent) -> None:
        print(event.to_console_format())


class DatabaseEventSubscriber(EventSubscriber):
    """Persists events to database"""
    async def on_event(self, event: WorkflowEvent) -> None:
        from database.connection import get_db_session
        from database.models import EventSnapshot
        
        session = get_db_session()
        try:
            snapshot = EventSnapshot(
                id=event.event_id,
                workflow_id=event.workflow_id,
                event_type=event.event_type.value,
                event_name=event.event_type.value,
                severity=event.severity.value,
                payload=event.payload,
                timestamp=event.timestamp,
            )
            session.add(snapshot)
            session.commit()
        finally:
            session.close()


class WebSocketEventSubscriber(EventSubscriber):
    """Broadcasts events via WebSocket"""
    
    def __init__(self):
        self.clients: Dict[str, asyncio.Queue] = {}
    
    def add_client(self, client_id: str) -> asyncio.Queue:
        """Register a WebSocket client"""
        queue = asyncio.Queue()
        self.clients[client_id] = queue
        return queue
    
    def remove_client(self, client_id: str) -> None:
        """Unregister a WebSocket client"""
        self.clients.pop(client_id, None)
    
    async def on_event(self, event: WorkflowEvent) -> None:
        """Broadcast to all connected clients"""
        message = json.dumps(event.to_dict())
        for queue in list(self.clients.values()):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("WebSocket queue full, dropping event")


class EventQueueSubscriber(EventSubscriber):
    """Delivers workflow events to a local async queue"""

    def __init__(self, workflow_id: Optional[str] = None):
        self.workflow_id = workflow_id
        self.queue: asyncio.Queue = asyncio.Queue()

    async def on_event(self, event: WorkflowEvent) -> None:
        if self.workflow_id is None or self.workflow_id == event.workflow_id:
            await self.queue.put(event.to_dict())


class EventStreamManager:
    """Central event stream coordinator"""
    
    def __init__(self):
        self.subscribers: List[EventSubscriber] = []
        self._lock = asyncio.Lock()
    
    def subscribe(self, subscriber: EventSubscriber) -> None:
        """Register event subscriber"""
        self.subscribers.append(subscriber)
    
    def unsubscribe(self, subscriber: EventSubscriber) -> None:
        """Unregister event subscriber"""
        self.subscribers.remove(subscriber)
    
    async def emit(
        self,
        workflow_id: str,
        event_type: EventType,
        payload: Dict[str, Any],
        source: str,
        severity: EventSeverity = EventSeverity.INFO,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> WorkflowEvent:
        """
        Emit a new event
        
        Args:
            workflow_id: Associated workflow
            event_type: Type of event
            payload: Event data
            source: Component emitting event
            severity: Event severity level
            user_id: Associated user
            device_id: Associated device
            
        Returns:
            Emitted event
        """
        async with self._lock:
            event = WorkflowEvent(
                event_id=str(uuid.uuid4()),
                workflow_id=workflow_id,
                event_type=event_type,
                severity=severity,
                timestamp=datetime.utcnow(),
                payload=payload,
                source=source,
                user_id=user_id,
                device_id=device_id,
            )
            
            # Notify all subscribers
            tasks = [subscriber.on_event(event) for subscriber in self.subscribers]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            return event
    
    async def emit_multiple(self, events_data: List[Dict]) -> List[WorkflowEvent]:
        """Emit multiple events efficiently"""
        events = []
        for data in events_data:
            event = await self.emit(**data)
            events.append(event)
        return events


# Global event manager instance
event_manager = EventStreamManager()


def get_event_manager() -> EventStreamManager:
    """Get global event manager"""
    return event_manager
