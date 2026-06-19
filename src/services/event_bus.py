from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EventType(Enum):
    COMMAND_RECEIVED = "CommandReceived"
    INTENT_DETECTED = "IntentDetected"
    ENTITY_EXTRACTED = "EntityExtracted"
    DEVICE_SELECTED = "DeviceSelected"
    PLAN_CREATED = "PlanCreated"
    EXECUTION_STARTED = "ExecutionStarted"
    EXECUTION_COMPLETED = "ExecutionCompleted"
    EXECUTION_FAILED = "ExecutionFailed"
    VERIFICATION_PASSED = "VerificationPassed"
    VERIFICATION_FAILED = "VerificationFailed"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_FAILED = "WorkflowFailed"
    SYSTEM_ALERT = "SystemAlert"
    VOICE_WAKEWORD_DETECTED = "VoiceWakeWordDetected"

class Event:
    def __init__(self, event_type: EventType, payload: Any, workflow_id: Optional[str] = None, device_id: Optional[str] = None):
        self.event_type = event_type
        self.payload = payload
        self.workflow_id = workflow_id
        self.device_id = device_id
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "workflow_id": self.workflow_id,
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat()
        }

class EventBus:
    """
    A centralized Event Bus for APA-OS.
    Allows components to emit events and others to subscribe to them.
    """
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {event_type: [] for event_type in EventType}
        self._event_history: List[Event] = []
        self._max_history = 1000

    def subscribe(self, event_type: EventType, callback: Callable[[Event], Any]):
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(callback)

    async def emit(self, event_type: EventType, payload: Any, workflow_id: Optional[str] = None, device_id: Optional[str] = None):
        """Emit an event and notify all subscribers."""
        event = Event(event_type, payload, workflow_id, device_id)

        # Persist to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        logger.info(f"Event Emitted: {event_type.value} | Workflow: {workflow_id} | Payload: {payload}")

        # Notify subscribers
        tasks = []
        for callback in self._subscribers[event_type]:
            if asyncio.iscoroutinefunction(callback):
                tasks.append(callback(event))
            else:
                # Run synchronous callbacks in a thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, callback, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_history(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve event history, optionally filtered by workflow_id."""
        if workflow_id:
            return [e.to_dict() for e in self._event_history if e.workflow_id == workflow_id]
        return [e.to_dict() for e in self._event_history]

# Singleton instance
event_bus = EventBus()
