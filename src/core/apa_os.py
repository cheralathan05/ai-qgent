"""
APA-OS Core Engine (Layer 0-15 Integrated)

The brain that understands, plans, executes, verifies, learns, and responds.

User Input
    ↓
Conversation Manager (Layer 1)
    ↓
Intent Understanding (Layer 1)
    ↓
Entity Extraction (Layer 1)
    ↓
Context Engine (Layer 7)
    ↓
Memory Engine (Layer 6)
    ↓
Planner Agent (Layer 8)
    ↓
Workflow Generator (Layer 8)
    ↓
Execution Engine (Layer 2/4)
    ↓
Verification Engine (Layer 9)
    ↓
Recovery Engine (Layer 14)
    ↓
Knowledge Engine (Layer 5)
    ↓
Learning Engine (Layer 10)
    ↓
Event Bus (Layer 12)
    ↓
Response Generator
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .intent_engine import UniversalIntentEngine, IntentResult, IntentCategory
from .workflow_generator import DynamicWorkflowGenerator, Workflow
from .execution_engine import ExecutionEngine, ExecutionResult
from .knowledge_engine import KnowledgeOperationsEngine, KnowledgeResult
from .memory_engine import MemoryEngine
from .verification_engine import VerificationEngine, VerificationType, VerificationStatus
from .event_bus import EventBus, EventType
from .recovery_engine import RecoveryEngine, FailureType
from .learning_engine import LearningEngine
from .conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


@dataclass
class APAOSResponse:
    """Complete response from APA-OS."""
    success: bool
    message: str
    intent: str
    target: Optional[str] = None
    workflow_id: str = ""
    execution_result: Optional[ExecutionResult] = None
    knowledge_result: Optional[KnowledgeResult] = None
    duration_ms: float = 0
    verification_passed: bool = False
    recovery_attempted: bool = False
    events_emitted: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class APAOS:
    """
    APA-OS Core Engine - Full Layer Integration
    
    Layers:
    - Layer 0: Foundation (Event Bus)
    - Layer 1: Conversation Manager + Intent Understanding
    - Layer 2: Device Operating Layer (Execution Engine)
    - Layer 5: Knowledge Engine
    - Layer 6: Memory Engine
    - Layer 7: Context Engine
    - Layer 8: Planning Engine (Workflow Generator)
    - Layer 9: Verification Engine
    - Layer 10: Learning Engine
    - Layer 12: Event Bus
    - Layer 14: Recovery Engine
    """

    def __init__(self):
        # Layer 1: Conversation + Intent
        self.conversation = ConversationManager()
        self.intent_engine = UniversalIntentEngine()
        
        # Layer 2/4: Execution
        self.execution_engine = ExecutionEngine()
        
        # Layer 5: Knowledge
        self.knowledge_engine = KnowledgeOperationsEngine()
        
        # Layer 6: Memory
        self.memory = MemoryEngine()
        
        # Layer 8: Planning
        self.workflow_generator = DynamicWorkflowGenerator()
        
        # Layer 9: Verification
        self.verification = VerificationEngine()
        
        # Layer 10: Learning
        self.learning = LearningEngine()
        
        # Layer 12: Event Bus
        self.events = EventBus()
        
        # Layer 14: Recovery
        self.recovery = RecoveryEngine()

    async def process(
        self,
        command: str,
        user_id: str = "default",
        device_id: Optional[str] = None,
    ) -> APAOSResponse:
        """
        Process any user command through all layers.
        
        Pipeline:
        1. Emit CommandReceived event
        2. Add to conversation
        3. Understand intent
        4. Extract entities
        5. Load context/memory
        6. Generate workflow
        7. Execute (if device action needed)
        8. Verify
        9. Handle recovery if failed
        10. Knowledge operations (if knowledge needed)
        11. Record learning
        12. Remember
        13. Emit completion event
        14. Respond
        """
        start_time = time.time()
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        events_count = 0

        # Layer 12: Emit CommandReceived
        await self.events.emit(
            EventType.COMMAND_RECEIVED,
            source="apa_os",
            data={"command": command, "user_id": user_id},
        )
        events_count += 1

        # Layer 1: Add to conversation
        self.conversation.add_user_message(
            content=command,
            metadata={"user_id": user_id, "device_id": device_id},
        )

        # Layer 1: Intent Understanding
        context = await self._build_context(user_id, device_id)
        
        intent_result = await self.intent_engine.understand(command, context)
        
        # Layer 12: Emit IntentDetected
        await self.events.emit(
            EventType.INTENT_DETECTED,
            source="intent_engine",
            data={
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "slots": intent_result.slots,
            },
        )
        events_count += 1

        # Layer 10: Record learning
        self.learning.record_interaction(
            "command",
            command,
            {"intent": intent_result.intent.value},
        )

        # Layer 7: Load context
        await self.events.emit(
            EventType.CONTEXT_LOADED,
            source="context_engine",
            data=context,
        )
        events_count += 1

        logger.info(
            f"Intent: {intent_result.intent.value} | "
            f"confidence={intent_result.confidence:.2f} | "
            f"phases=[P1={intent_result.requires_phase1},"
            f"P2={intent_result.requires_phase2},"
            f"P3={intent_result.requires_phase3}]"
        )

        # Route based on phases needed
        execution_result = None
        knowledge_result = None
        verification_passed = False
        recovery_attempted = False

        # Phase 3: Knowledge operations
        if intent_result.requires_phase3 and not intent_result.requires_phase1:
            knowledge_result = await self._handle_knowledge(intent_result)
            
            # Layer 9: Verify knowledge
            if knowledge_result and knowledge_result.success:
                vr = await self.verification.verify_knowledge_found(
                    intent_result.slots.get("query", ""),
                    context={"sources": knowledge_result.sources},
                )
                verification_passed = vr.status == VerificationStatus.PASSED
        
        # Phase 1+2: Device operations
        elif intent_result.requires_phase1:
            # Get device ID
            if not device_id:
                device_id = await self._get_device_id()
            
            if device_id:
                # Layer 12: Emit PlanCreated
                workflow = self.workflow_generator.generate(intent_result)
                await self.events.emit(
                    EventType.PLAN_CREATED,
                    source="workflow_generator",
                    data={
                        "workflow_id": workflow_id,
                        "steps": len(workflow.steps),
                        "description": workflow.description,
                    },
                )
                events_count += 1

                # Record in memory
                self.memory.record_workflow(
                    workflow_id=workflow_id,
                    intent=intent_result.intent.value,
                    description=workflow.description,
                )

                # Layer 12: Emit ExecutionStarted
                await self.events.emit(
                    EventType.EXECUTION_STARTED,
                    source="execution_engine",
                    data={"workflow_id": workflow_id},
                )
                events_count += 1

                # Execute workflow
                execution_result = await self.execution_engine.execute(
                    workflow, device_id
                )

                # Layer 12: Emit ExecutionCompleted
                await self.events.emit(
                    EventType.EXECUTION_COMPLETED if execution_result.success else EventType.EXECUTION_FAILED,
                    source="execution_engine",
                    data={
                        "workflow_id": workflow_id,
                        "success": execution_result.success,
                        "message": execution_result.message,
                    },
                )
                events_count += 1

                # Layer 9: Verify execution
                if execution_result.success:
                    vr = await self._verify_execution(
                        intent_result, execution_result, device_id
                    )
                    verification_passed = vr.status == VerificationStatus.PASSED

                    # Layer 14: Recovery if verification failed
                    if not verification_passed:
                        recovery_attempted = True
                        recovery_result = await self.recovery.recover(
                            FailureType.ELEMENT_NOT_FOUND,
                            context={"device_id": device_id},
                        )
                        if recovery_result.success:
                            # Retry execution
                            execution_result = await self.execution_engine.execute(
                                workflow, device_id
                            )
                            vr = await self._verify_execution(
                                intent_result, execution_result, device_id
                            )
                            verification_passed = vr.status == VerificationStatus.PASSED

                # Layer 12: Emit VerificationPassed/Failed
                await self.events.emit(
                    EventType.VERIFICATION_PASSED if verification_passed else EventType.VERIFICATION_FAILED,
                    source="verification_engine",
                    data={"workflow_id": workflow_id, "passed": verification_passed},
                )
                events_count += 1

                # Also handle knowledge if needed
                if intent_result.requires_phase3:
                    knowledge_result = await self._handle_knowledge(intent_result)
            else:
                execution_result = ExecutionResult(
                    workflow_id=workflow_id,
                    success=False,
                    message="No Android device connected",
                    steps=[],
                )

        # Build response
        duration_ms = (time.time() - start_time) * 1000

        # Layer 6: Record in memory
        self.memory.record_command(
            command=intent_result.raw_command,
            intent=intent_result.intent.value,
            success=(
                execution_result.success if execution_result else
                (knowledge_result.success if knowledge_result else False)
            ),
        )

        # Record app usage
        if "app" in intent_result.slots:
            self.memory.record_app(intent_result.slots["app"])
            self.learning.record_interaction("app_usage", intent_result.slots["app"])

        # Record contact usage
        if "recipient" in intent_result.slots:
            self.memory.record_contact(intent_result.slots["recipient"])
            self.learning.record_interaction(
                "contact_frequency", intent_result.slots["recipient"]
            )

        # Record search
        if "query" in intent_result.slots:
            self.memory.record_search(intent_result.slots["query"])

        # Build final message
        message = self._build_response_message(
            intent_result, execution_result, knowledge_result
        )

        # Layer 1: Add assistant response to conversation
        self.conversation.add_assistant_message(
            content=message,
            metadata={"intent": intent_result.intent.value},
        )

        # Layer 12: Emit WorkflowCompleted
        await self.events.emit(
            EventType.WORKFLOW_COMPLETED,
            source="apa_os",
            data={
                "workflow_id": workflow_id,
                "success": True,
                "duration_ms": duration_ms,
            },
        )
        events_count += 1

        return APAOSResponse(
            success=(
                execution_result.success if execution_result else
                (knowledge_result.success if knowledge_result else False)
            ),
            message=message,
            intent=intent_result.intent.value,
            target=intent_result.slots.get("app") or intent_result.slots.get("recipient"),
            workflow_id=workflow_id,
            execution_result=execution_result,
            knowledge_result=knowledge_result,
            duration_ms=duration_ms,
            verification_passed=verification_passed,
            recovery_attempted=recovery_attempted,
            events_emitted=events_count,
            metadata={
                "confidence": intent_result.confidence,
                "slots": intent_result.slots,
                "requires_phase1": intent_result.requires_phase1,
                "requires_phase2": intent_result.requires_phase2,
                "requires_phase3": intent_result.requires_phase3,
                "conversation_id": self.conversation.get_active_conversation().id if self.conversation.get_active_conversation() else None,
            },
        )

    async def _build_context(
        self, user_id: str, device_id: Optional[str]
    ) -> Dict[str, Any]:
        """Build context from memory, conversation, and learning."""
        context = {
            "user_id": user_id,
            "device_id": device_id,
            "recent_commands": self.memory.get_state().recent_commands[-5:],
            "current_app": self.memory.get_state().current_app,
            "conversation_context": self.conversation.get_context(),
            "frequent_apps": [
                p.key for p in self.learning.get_frequent_apps(5)
            ],
            "frequent_contacts": [
                p.key for p in self.learning.get_frequent_contacts(5)
            ],
        }
        return context

    async def _get_device_id(self) -> Optional[str]:
        """Get connected device ID."""
        try:
            from services.adb_service import get_adb_service, find_adb_binary
            adb = get_adb_service(find_adb_binary())
            devices = await adb.list_devices()
            if devices:
                return devices[0]["serial"]
        except Exception:
            pass
        return None

    async def _verify_execution(
        self,
        intent_result: IntentResult,
        execution_result: ExecutionResult,
        device_id: str,
    ) -> Any:
        """Verify execution results."""
        intent = intent_result.intent
        slots = intent_result.slots

        if intent == IntentCategory.OPEN_APP:
            package = slots.get("package") or slots.get("app", "")
            return await self.verification.verify_app_foreground(package)

        elif intent == IntentCategory.SEND_MESSAGE:
            return await self.verification.verify_message_sent(
                slots.get("message", "")
            )

        elif intent == IntentCategory.BATTERY_STATUS:
            return await self.verification.verify_screen_state("battery")

        elif intent == IntentCategory.TAKE_SCREENSHOT:
            return await self.verification.verify_action_completed(
                "screenshot", {"success": execution_result.success}
            )

        elif intent in (IntentCategory.WEB_SEARCH, IntentCategory.IN_APP_SEARCH):
            return await self.verification.verify_search_results(
                slots.get("query", "")
            )

        # Default: action completed
        return await self.verification.verify_action_completed(
            intent.value, {"success": execution_result.success}
        )

    async def _handle_knowledge(self, intent_result: IntentResult) -> KnowledgeResult:
        """Handle knowledge-based operations."""
        intent = intent_result.intent
        slots = intent_result.slots
        query = slots.get("query") or slots.get("file") or slots.get("topic", "")

        # Layer 12: Emit knowledge event
        await self.events.emit(
            EventType.KNOWLEDGE_SEARCH_STARTED,
            source="knowledge_engine",
            data={"query": query, "intent": intent.value},
        )

        if intent == IntentCategory.SUMMARIZE:
            result = await self.knowledge_engine.summarize(query)
        elif intent == IntentCategory.EXPLAIN:
            result = await self.knowledge_engine.explain(query)
        elif intent == IntentCategory.GENERATE_ASSIGNMENT:
            result = await self.knowledge_engine.generate_assignment(query)
        elif intent == IntentCategory.GENERATE_MCQ:
            count = int(slots.get("count", 10))
            result = await self.knowledge_engine.generate_mcq(query, count)
        elif intent == IntentCategory.GENERATE_QUESTIONS:
            count = int(slots.get("count", 20))
            result = await self.knowledge_engine.generate_questions(query, count)
        elif intent == IntentCategory.GENERATE_NOTES:
            result = await self.knowledge_engine.generate_notes(query)
        elif intent in (IntentCategory.FIND_FILE, IntentCategory.SEARCH_FILES, IntentCategory.FIND_KNOWLEDGE):
            result = await self.knowledge_engine.search_files(query)
        else:
            result = await self.knowledge_engine.find_knowledge(query)

        # Layer 10: Record learning
        if result.success:
            self.learning.record_interaction("topic_interest", query)

        # Layer 12: Emit knowledge completed
        await self.events.emit(
            EventType.KNOWLEDGE_SEARCH_COMPLETED,
            source="knowledge_engine",
            data={"query": query, "success": result.success},
        )

        return result

    def _build_response_message(
        self,
        intent_result: IntentResult,
        execution_result: Optional[ExecutionResult],
        knowledge_result: Optional[KnowledgeResult],
    ) -> str:
        """Build user-friendly response message."""
        intent = intent_result.intent
        slots = intent_result.slots

        # Knowledge response
        if knowledge_result and knowledge_result.success:
            return knowledge_result.answer

        # Execution response
        if execution_result:
            if execution_result.success:
                return execution_result.message
            else:
                return execution_result.message or "Could not complete the request"

        # Default responses based on intent
        if intent == IntentCategory.OPEN_APP:
            app = slots.get("app", "the app")
            return f"Opening {app}."
        elif intent == IntentCategory.CLOSE_APP:
            app = slots.get("app", "the app")
            return f"Closing {app}."
        elif intent == IntentCategory.SEND_MESSAGE:
            recipient = slots.get("recipient", "your contact")
            return f"Sending message to {recipient}."
        elif intent == IntentCategory.CALL_CONTACT:
            contact = slots.get("recipient", "your contact")
            return f"Calling {contact}."
        elif intent == IntentCategory.BATTERY_STATUS:
            return "Checking battery level."
        elif intent == IntentCategory.TAKE_SCREENSHOT:
            return "Taking screenshot."
        elif intent == IntentCategory.WEB_SEARCH:
            query = slots.get("query", "")
            return f"Searching for {query}."
        elif intent == IntentCategory.UNKNOWN:
            return "I'm not sure what you want me to do. Can you rephrase that?"
        
        return "Processing your request."

    def get_status(self) -> Dict[str, Any]:
        """Get full system status."""
        return {
            "apa_os": "running",
            "layers": {
                "conversation": self.conversation.get_status(),
                "intent_engine": "active",
                "execution_engine": "active",
                "knowledge_engine": "active",
                "memory": self.memory.get_state().recent_commands[-5:] if self.memory.get_state() else [],
                "verification": self.verification.get_status(),
                "learning": self.learning.get_status(),
                "event_bus": self.events.get_status(),
                "recovery": self.recovery.get_status(),
            },
        }


# Singleton
_apa_os = None


def get_apa_os() -> APAOS:
    global _apa_os
    if _apa_os is None:
        _apa_os = APAOS()
    return _apa_os
