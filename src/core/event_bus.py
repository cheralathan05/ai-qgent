"""
APA-OS Event Bus (Layer 12)

Every action emits events.

Events:
- CommandReceived
- IntentDetected
- ContextLoaded
- PlanCreated
- ExecutionStarted
- ExecutionStepStarted
- ExecutionStepCompleted
- ExecutionStepFailed
- VerificationStarted
- VerificationPassed
- VerificationFailed
- WorkflowCompleted
- WorkflowFailed
- ErrorOccurred
- RecoveryAttempted
- LearningRecorded
"""

import logging
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    # Conversation events
    COMMAND_RECEIVED = "command_received"
    INTENT_DETECTED = "intent_detected"
    ENTITIES_EXTRACTED = "entities_extracted"
    
    # Context events
    CONTEXT_LOADED = "context_loaded"
    CONTEXT_UPDATED = "context_updated"
    
    # Planning events
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    
    # Execution events
    EXECUTION_STARTED = "execution_started"
    EXECUTION_STEP_STARTED = "execution_step_started"
    EXECUTION_STEP_COMPLETED = "execution_step_completed"
    EXECUTION_STEP_FAILED = "execution_step_failed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    
    # Verification events
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    
    # Knowledge events
    KNOWLEDGE_SEARCH_STARTED = "knowledge_search_started"
    KNOWLEDGE_SEARCH_COMPLETED = "knowledge_search_completed"
    KNOWLEDGE_GENERATION_STARTED = "knowledge_generation_started"
    KNOWLEDGE_GENERATION_COMPLETED = "knowledge_generation_completed"
    
    # Memory events
    MEMORY_STORED = "memory_stored"
    MEMORY_RETRIEVED = "memory_retrieved"
    
    # Learning events
    LEARNING_RECORDED = "learning_recorded"
    PATTERN_DETECTED = "pattern_detected"
    
    # Recovery events
    RECOVERY_ATTEMPTED = "recovery_attempted"
    RECOVERY_SUCCEEDED = "recovery_succeeded"
    RECOVERY_FAILED = "recovery_failed"
    
    # System events
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_READY = "system_ready"
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"


@dataclass
class Event:
    """An event emitted by the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.COMMAND_RECEIVED
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""


class EventBus:
    """
    Event bus for system-wide event emission and handling.
    
    Every action emits events for observability.
    Components can subscribe to events for real-time updates.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._event_stats: Dict[str, int] = {}

    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable):
        """Subscribe to all events."""
        self._wildcard_subscribers.append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    async def emit(
        self,
        event_type: EventType,
        source: str = "",
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        success: bool = True,
        error: str = "",
    ) -> Event:
        """Emit an event."""
        event = Event(
            event_type=event_type,
            source=source,
            data=data or {},
            metadata=metadata or {},
            duration_ms=duration_ms,
            success=success,
            error=error,
        )

        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        # Update stats
        key = event_type.value
        self._event_stats[key] = self._event_stats.get(key, 0) + 1

        # Notify specific subscribers
        for callback in self._subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")

        # Notify wildcard subscribers
        for callback in self._wildcard_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Wildcard subscriber error: {e}")

        return event

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
        source: Optional[str] = None,
    ) -> List[Event]:
        """Get event history with optional filters."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_stats(self) -> Dict[str, int]:
        """Get event statistics."""
        return dict(self._event_stats)

    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        self._event_stats.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get event bus status."""
        return {
            "type": "event_bus",
            "total_events": len(self._event_history),
            "subscribers": {
                et.value: len(cbs) for et, cbs in self._subscribers.items()
            },
            "wildcard_subscribers": len(self._wildcard_subscribers),
            "stats": self.get_stats(),
        }


# Singleton
_event_bus = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
