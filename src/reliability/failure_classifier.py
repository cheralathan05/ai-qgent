"""
Failure Classification System
Identifies and categorizes all types of failures
"""

from enum import Enum
from typing import Dict, Any, Optional, Type
from dataclasses import dataclass
import traceback
import logging

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """All possible failure types"""
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
    UNKNOWN = "unknown"


@dataclass
class FailureInfo:
    """Complete failure information"""
    failure_type: FailureType
    message: str
    details: Dict[str, Any]
    exception: Optional[Exception] = None
    is_recoverable: bool = False
    suggested_recovery: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_type": self.failure_type.value,
            "message": self.message,
            "details": self.details,
            "is_recoverable": self.is_recoverable,
            "suggested_recovery": self.suggested_recovery,
        }


class FailureClassifier:
    """Classify and analyze failures"""
    
    # Exception -> Failure Type mapping
    EXCEPTION_MAPPING = {
        "ConnectionError": FailureType.NETWORK_FAILURE,
        "TimeoutError": FailureType.WORKFLOW_TIMEOUT,
        "PermissionError": FailureType.PERMISSION_DENIED,
        "ModuleNotFoundError": FailureType.APP_NOT_FOUND,
        "OSError": FailureType.DEVICE_DISCONNECTED,
    }
    
    # Recovery strategies by failure type
    RECOVERY_STRATEGIES = {
        FailureType.DEVICE_DISCONNECTED: "reconnect_device",
        FailureType.NETWORK_FAILURE: "retry_with_backoff",
        FailureType.WORKFLOW_TIMEOUT: "increase_timeout_and_retry",
        FailureType.DEVICE_LOCKED: "prompt_user_unlock",
        FailureType.ADB_FAILURE: "restart_adb_and_retry",
        FailureType.OLLAMA_UNAVAILABLE: "wait_for_ollama_and_retry",
    }
    
    @staticmethod
    def classify(exception: Exception) -> FailureInfo:
        """Classify an exception"""
        exc_type = type(exception).__name__
        exc_message = str(exception)
        traceback_str = traceback.format_exc()
        
        # Check exception type mapping
        failure_type = FailureType.UNKNOWN
        for mapped_type, mapped_failure in FailureClassifier.EXCEPTION_MAPPING.items():
            if mapped_type in exc_type or mapped_type.lower() in exc_message.lower():
                failure_type = mapped_failure
                break
        
        # Check message patterns
        if "ollama" in exc_message.lower():
            failure_type = FailureType.OLLAMA_UNAVAILABLE
        elif "device" in exc_message.lower() and "not" in exc_message.lower():
            failure_type = FailureType.DEVICE_DISCONNECTED
        elif "adb" in exc_message.lower():
            failure_type = FailureType.ADB_FAILURE
        elif "timeout" in exc_message.lower():
            failure_type = FailureType.WORKFLOW_TIMEOUT
        elif "permission" in exc_message.lower():
            failure_type = FailureType.PERMISSION_DENIED
        elif "locked" in exc_message.lower():
            failure_type = FailureType.DEVICE_LOCKED
        
        is_recoverable = failure_type in FailureClassifier.RECOVERY_STRATEGIES
        suggested_recovery = FailureClassifier.RECOVERY_STRATEGIES.get(failure_type)
        
        return FailureInfo(
            failure_type=failure_type,
            message=exc_message,
            details={
                "exception_type": exc_type,
                "traceback": traceback_str,
            },
            exception=exception,
            is_recoverable=is_recoverable,
            suggested_recovery=suggested_recovery,
        )
    
    @staticmethod
    def from_error_code(error_code: int, context: Dict[str, Any]) -> FailureInfo:
        """Classify error from error code and context"""
        # ADB error codes
        if error_code == 127:
            return FailureInfo(
                failure_type=FailureType.ADB_FAILURE,
                message="ADB command not found",
                details={"error_code": error_code, "context": context},
                is_recoverable=True,
                suggested_recovery="restart_adb_and_retry",
            )
        elif error_code == 1:
            return FailureInfo(
                failure_type=FailureType.DEVICE_DISCONNECTED,
                message="Device not found or offline",
                details={"error_code": error_code, "context": context},
                is_recoverable=True,
                suggested_recovery="reconnect_device",
            )
        
        return FailureInfo(
            failure_type=FailureType.UNKNOWN,
            message=f"Unknown error code: {error_code}",
            details={"error_code": error_code, "context": context},
            is_recoverable=False,
        )
    
    @staticmethod
    def is_transient(failure_type: FailureType) -> bool:
        """Check if failure is transient (can be retried)"""
        transient_types = {
            FailureType.NETWORK_FAILURE,
            FailureType.WORKFLOW_TIMEOUT,
            FailureType.ADB_FAILURE,
            FailureType.DEVICE_DISCONNECTED,
            FailureType.OLLAMA_UNAVAILABLE,
        }
        return failure_type in transient_types
    
    @staticmethod
    def is_permanent(failure_type: FailureType) -> bool:
        """Check if failure is permanent (cannot be retried)"""
        permanent_types = {
            FailureType.PERMISSION_DENIED,
            FailureType.APP_NOT_FOUND,
        }
        return failure_type in permanent_types
