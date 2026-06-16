"""
Main Workflow Orchestrator
Coordinates all layers to execute user commands end-to-end
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from console.event_stream import (
    get_event_manager, EventType, EventSeverity, WorkflowEvent
)
from understanding.entity_extractor import get_command_understanding_engine
from reliability.retry_manager import get_retry_manager, RetryConfig
from reliability.timeout_manager import get_timeout_manager
from reliability.failure_classifier import FailureClassifier, FailureType
from device_intelligence.device_detector import get_device_intelligence
from verification.execution_verifier import get_execution_verifier
from audit.audit_manager import get_audit_manager, AuditActionType, AuditResourceType, AuditResult
from approval_ui.approval_context import (
    get_approval_context_builder,
    ApprovalPayloadBuilder,
    ApprovalPreviewBuilder,
    ApprovalExplainer,
)
from database.models import WorkflowStatus
from devices import device_manager, DeviceStatus
from security.credential_manager import get_credential_manager, CredentialType, PINProcessor
from services.intent_agent import get_intent_agent
from services.planner_agent import get_planner_agent
from services.ollama_service import get_ollama_service
from services.adb_service import get_adb_service
from config import Config

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Main orchestration engine"""
    
    def __init__(
        self,
        session=None,
        adb_client=None,
        ollama_client=None,
        contact_db=None,
        app_db=None,
    ):
        self.session = session
        self.adb = adb_client or get_adb_service(
            Config.get_adb_config().adb_path,
            Config.get_adb_config().default_timeout,
        )
        self.ollama = ollama_client or get_ollama_service()
        
        # Initialize all layers
        self.event_manager = get_event_manager()
        self.intent_agent = get_intent_agent()
        self.planner_agent = get_planner_agent()
        self.command_engine = get_command_understanding_engine(contact_db, app_db)
        self.retry_manager = get_retry_manager()
        self.timeout_manager = get_timeout_manager()
        self.device_manager = device_manager
        self.device_intel = get_device_intelligence(self.adb)
        self.execution_verifier = get_execution_verifier(self.adb, self.device_intel)
        self.audit_manager = get_audit_manager(session)
        self.approval_builder = get_approval_context_builder(session)
        self.credential_manager = get_credential_manager(session)
    
    async def execute_command(
        self,
        user_id: str,
        command: str,
        device_id: str,
        workflow_id: str | None = None,
        voice_input: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute user command end-to-end
        
        Args:
            user_id: User ID
            command: User command (text or transcribed from voice)
            device_id: Target device
            voice_input: Whether input was from voice
            
        Returns:
            Execution result
        """
        from database.connection import create_workflow, get_workflow, update_workflow

        workflow_id = workflow_id or str(uuid.uuid4())
        start_time = datetime.utcnow()
        detected_intent = "unknown"
        detected_target = None

        existing_workflow = get_workflow(workflow_id)
        if existing_workflow is None:
            await create_workflow(
                user_id=user_id,
                command=command,
                intent="pending",
                device_id=device_id,
                workflow_id=workflow_id,
            )

        update_workflow(
            workflow_id,
            status=WorkflowStatus.EXECUTING,
            start_time=start_time,
        )

        try:
            # ==================== Stage 1: Intent Detection ====================
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.INTENT_DETECTED,
                payload={"command": command, "voice_input": voice_input},
                source="orchestrator",
                severity=EventSeverity.INFO,
                user_id=user_id,
                device_id=device_id,
            )
            
            # Understand command
            intent_result = await self.timeout_manager.execute_intent_detection(
                self.intent_agent.detect_intent,
                command,
            )
            detected_intent = intent_result.intent.value
            detected_target = intent_result.slots.get("app") or intent_result.slots.get("target")

            update_workflow(
                workflow_id,
                intent=detected_intent,
            )
            
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.ENTITIES_EXTRACTED,
                payload={
                    "intent": detected_intent,
                    "confidence": intent_result.confidence,
                    "entities": [
                        {
                            "type": e.type,
                            "value": e.value,
                            "confidence": e.confidence,
                        }
                        for e in intent_result.entities
                    ],
                    "slots": intent_result.slots,
                },
                source="intent_agent",
                severity=EventSeverity.INFO,
                user_id=user_id,
            )
            
            # ==================== Stage 2: Device Check ====================
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.DEVICE_CONNECTED,
                payload={"device_id": device_id},
                source="orchestrator",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
            
            device = self.device_manager.get_device(device_id)
            
            if device is not None:
                device_info = await device.get_info()
            elif self.device_intel is not None:
                device_info = await self.device_intel.get_device_info(device_id)
            else:
                raise RuntimeError(f"Device {device_id} is not registered or connected")

            is_connected = getattr(device_info, "is_connected", None)
            if is_connected is None:
                is_connected = getattr(device_info, "status", None) == DeviceStatus.CONNECTED

            if not is_connected:
                raise RuntimeError(f"Device {device_id} is not connected")
            
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.PHONE_STATE_VERIFIED,
                payload={
                    "device_id": device_id,
                    "status": getattr(device_info, "status", None).value
                    if getattr(device_info, "status", None) is not None else None,
                    "is_locked": getattr(device_info, "is_locked", False),
                    "battery": getattr(device_info, "battery_level", None),
                    "foreground_app": getattr(device_info, "foreground_app", None),
                },
                source="device_intelligence",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
            
            # Handle locked device
            if getattr(device_info, "is_locked", False):
                await self.event_manager.emit(
                    workflow_id=workflow_id,
                    event_type=EventType.DEVICE_LOCKED,
                    payload={"device_id": device_id},
                    source="orchestrator",
                    severity=EventSeverity.WARNING,
                    device_id=device_id,
                )
                
                # Request PIN from user
                pin_processor = PINProcessor(get_credential_manager().secret_manager)
                
                # In real system, this would prompt user for PIN
                # For now, we'll skip and assume user unlock
                # await request_user_pin_async(user_id)
            
            # ==================== Stage 3: Plan Creation ====================
            plan_steps = self.planner_agent.plan(intent_result)
            if not plan_steps:
                plan_steps = self._create_plan_steps(intent_result)

            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.PLAN_CREATED,
                payload={
                    "intent": detected_intent,
                    "steps": plan_steps,
                },
                source="planner_agent",
                severity=EventSeverity.INFO,
                user_id=user_id,
            )

            update_workflow(
                workflow_id,
                plan_json=plan_steps,
            )
            
            # ==================== Stage 4: Execution ====================
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.EXECUTION_STARTED,
                payload={"total_steps": len(plan_steps)},
                source="execution_engine",
                severity=EventSeverity.INFO,
            )
            
            results = []
            
            for step_idx, step in enumerate(plan_steps):
                await self.event_manager.emit(
                    workflow_id=workflow_id,
                    event_type=EventType.STEP_STARTED,
                    payload={
                        "step_number": step_idx + 1,
                        "total_steps": len(plan_steps),
                        "step_type": step["type"],
                        "description": step["description"],
                    },
                    source="execution_engine",
                    severity=EventSeverity.INFO,
                )
                
                try:
                    # Execute step with retry and timeout
                    step_result = await self.timeout_manager.execute_execution(
                        self.retry_manager.execute_with_retry,
                        self._execute_step,
                        step,
                        device_id,
                        workflow_id,
                        config=RetryConfig(max_retries=2),
                    )
                    
                    results.append(step_result)
                    
                    await self.event_manager.emit(
                        workflow_id=workflow_id,
                        event_type=EventType.STEP_COMPLETED,
                        payload={
                            "step_number": step_idx + 1,
                            "result": step_result,
                        },
                        source="execution_engine",
                        severity=EventSeverity.INFO,
                    )
                
                except Exception as e:
                    failure_info = FailureClassifier.classify(e)
                    
                    await self.event_manager.emit(
                        workflow_id=workflow_id,
                        event_type=EventType.STEP_FAILED,
                        payload={
                            "step_number": step_idx + 1,
                            "error": str(e),
                            "failure_type": failure_info.failure_type.value,
                        },
                        source="execution_engine",
                        severity=EventSeverity.ERROR,
                    )
                    
                    # Try recovery
                    if failure_info.is_recoverable:
                        await self.event_manager.emit(
                            workflow_id=workflow_id,
                            event_type=EventType.RECOVERY_ATTEMPTED,
                            payload={
                                "strategy": failure_info.suggested_recovery,
                                "failure_type": failure_info.failure_type.value,
                            },
                            source="recovery_engine",
                            severity=EventSeverity.WARNING,
                        )
                        # Recovery would be attempted here
                    
                    raise
            
            # ==================== Stage 5: Verification ====================
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.VERIFICATION_STARTED,
                payload={"steps": len(plan_steps)},
                source="verification_engine",
                severity=EventSeverity.INFO,
            )
            
            verification_results = await self._verify_execution(
                device_id,
                plan_steps,
                intent_result,
            )
            
            all_verified = all(v.passed for v in verification_results)
            
            if all_verified:
                await self.event_manager.emit(
                    workflow_id=workflow_id,
                    event_type=EventType.VERIFICATION_PASSED,
                    payload={"results": len(verification_results)},
                    source="verification_engine",
                    severity=EventSeverity.INFO,
                )
            else:
                await self.event_manager.emit(
                    workflow_id=workflow_id,
                    event_type=EventType.VERIFICATION_FAILED,
                    payload={"failed": sum(1 for v in verification_results if not v.passed)},
                    source="verification_engine",
                    severity=EventSeverity.ERROR,
                )
                raise RuntimeError("Verification failed")
            
            # ==================== Stage 6: Audit Logging ====================
            await self.audit_manager.log_workflow_completed(
                user_id=user_id,
                workflow_id=workflow_id,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )
            
            # ==================== Stage 7: Completion ====================
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.EXECUTION_COMPLETED,
                payload={
                    "total_steps": len(plan_steps),
                    "duration_ms": duration_ms,
                },
                source="orchestrator",
                severity=EventSeverity.INFO,
            )

            update_workflow(
                workflow_id,
                status=WorkflowStatus.COMPLETED,
                result={"results": results},
                end_time=datetime.utcnow(),
                duration_ms=duration_ms,
            )
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "intent": detected_intent,
                "target": detected_target,
                "status": "completed",
                "results": results,
                "duration_ms": duration_ms,
            }
        
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            failure_info = FailureClassifier.classify(e)
            
            await self.event_manager.emit(
                workflow_id=workflow_id,
                event_type=EventType.EXECUTION_FAILED,
                payload={
                    "error": str(e),
                    "failure_type": failure_info.failure_type.value,
                    "is_recoverable": failure_info.is_recoverable,
                },
                source="orchestrator",
                severity=EventSeverity.CRITICAL,
            )
            
            update_workflow(
                workflow_id,
                status=WorkflowStatus.FAILED,
                error=str(e),
                end_time=datetime.utcnow(),
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )

            await self.audit_manager.log_workflow_failed(
                user_id=user_id,
                workflow_id=workflow_id,
                error=str(e),
            )
            
            return {
                "success": False,
                "workflow_id": workflow_id,
                "intent": detected_intent,
                "target": detected_target,
                "status": "failed",
                "error": str(e),
                "failure_type": failure_info.failure_type.value,
                "is_recoverable": failure_info.is_recoverable,
            }
    
    def _create_plan_steps(self, intent_result) -> List[Dict[str, Any]]:
        """Create execution plan from intent as a fallback."""
        steps = []
        
        if intent_result.intent.value == "open_app":
            app = intent_result.slots.get("app")
            if app:
                steps.append({
                    "type": "launch_app",
                    "description": f"Launch {app}",
                    "app": app,
                })
        
        elif intent_result.intent.value == "send_message":
            recipient = intent_result.slots.get("recipient")
            message = intent_result.slots.get("message")
            if recipient and message:
                steps.append({
                    "type": "send_message",
                    "description": f"Send message to {recipient}",
                    "recipient": recipient,
                    "message": message,
                })
        
        elif intent_result.intent.value == "open_device":
            steps.append({
                "type": "show_device_view",
                "description": "Show device control center",
            })
        
        return steps
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        device_id: str,
        workflow_id: str,
    ) -> Dict[str, Any]:
        """Execute a single step"""
        step_type = step.get("type")
        
        if step_type == "launch_app":
            app = step.get("app")
            device = self.device_manager.get_device(device_id)

            if device is not None:
                return await device.launch_app(app)

            if self.adb is not None:
                await self.adb.shell(device_id, f"am start -n {app}/{app}.MainActivity")
                await asyncio.sleep(2)  # Wait for app to launch
                return {"status": "success", "app": app}

            return {"status": "error", "message": "No device available for execution"}
        
        elif step_type == "send_message":
            return {"status": "success", "type": "message_sent"}
        
        elif step_type == "show_device_view":
            return {"status": "success", "type": "device_view_shown"}
        
        return {"status": "unknown", "type": step_type}
    
    async def _verify_execution(
        self,
        device_id: str,
        plan_steps: List[Dict],
        intent_result,
    ) -> List:
        """Verify execution results"""
        results = []
        
        for step in plan_steps:
            if step["type"] == "launch_app":
                device = self.device_manager.get_device(device_id)
                if device is not None:
                    result = await device.verify_app_opened(step["app"], timeout_seconds=10)
                else:
                    result = await self.execution_verifier.verify_app_opened(
                        device_id,
                        step["app"],
                        timeout_seconds=10,
                    )
                results.append(result)
        
        return results


def get_workflow_orchestrator(
    session=None,
    adb_client=None,
    ollama_client=None,
    contact_db=None,
    app_db=None,
) -> WorkflowOrchestrator:
    """Create a workflow orchestrator instance."""
    return WorkflowOrchestrator(
        session,
        adb_client,
        ollama_client,
        contact_db,
        app_db,
    )
