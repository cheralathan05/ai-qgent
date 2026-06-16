"""
Execution Verification System
Verifies that actions actually completed successfully
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class VerificationType(str, Enum):
    """Types of verification"""
    APP_OPENED = "app_opened"
    APP_CLOSED = "app_closed"
    SCREEN_CHANGED = "screen_changed"
    STATE_CHANGED = "state_changed"
    TEXT_APPEARED = "text_appeared"
    ELEMENT_EXISTS = "element_exists"
    ACTION_CONFIRMED = "action_confirmed"


@dataclass
class VerificationResult:
    """Result of verification"""
    verification_type: VerificationType
    passed: bool
    message: str
    evidence: Dict[str, Any]
    confidence_score: float
    duration_ms: int
    timestamp: datetime


class ExecutionVerifier:
    """Verifies execution results"""
    
    def __init__(self, adb_client, device_intelligence):
        self.adb = adb_client
        self.device_intel = device_intelligence
    
    async def verify_app_opened(
        self,
        device_id: str,
        package_name: str,
        timeout_seconds: int = 10,
    ) -> VerificationResult:
        """
        Verify that an app opened successfully
        
        Args:
            device_id: Device to check
            package_name: Package name of app
            timeout_seconds: Max time to wait
            
        Returns:
            VerificationResult
        """
        start_time = datetime.utcnow()
        
        try:
            # Poll for app in foreground
            for attempt in range(timeout_seconds):
                device_info = await self.device_intel.get_device_info(device_id)
                
                if device_info.foreground_app == package_name:
                    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    return VerificationResult(
                        verification_type=VerificationType.APP_OPENED,
                        passed=True,
                        message=f"App {package_name} successfully opened",
                        evidence={
                            "package_name": package_name,
                            "foreground_app": device_info.foreground_app,
                            "attempts": attempt + 1,
                        },
                        confidence_score=0.99,
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow(),
                    )
                
                # Invalidate cache and wait before retry
                self.device_intel.invalidate_cache(device_id)
                await asyncio.sleep(1)
            
            # Timeout - app never opened
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            device_info = await self.device_intel.get_device_info(device_id)
            
            return VerificationResult(
                verification_type=VerificationType.APP_OPENED,
                passed=False,
                message=f"App {package_name} did not open within {timeout_seconds}s",
                evidence={
                    "package_name": package_name,
                    "current_app": device_info.foreground_app,
                    "timeout_exceeded": True,
                },
                confidence_score=0.8,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
        
        except Exception as e:
            logger.error(f"Error verifying app opened: {e}")
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return VerificationResult(
                verification_type=VerificationType.APP_OPENED,
                passed=False,
                message=f"Verification failed: {str(e)}",
                evidence={"error": str(e)},
                confidence_score=0.0,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
    
    async def verify_text_appeared(
        self,
        device_id: str,
        text: str,
        timeout_seconds: int = 10,
    ) -> VerificationResult:
        """
        Verify that text appeared on screen
        
        Args:
            device_id: Device to check
            text: Text to search for
            timeout_seconds: Max time to wait
            
        Returns:
            VerificationResult
        """
        start_time = datetime.utcnow()
        
        try:
            # Get accessible text from screen
            for attempt in range(timeout_seconds):
                screen_text = await self.adb.shell(
                    device_id,
                    "dumpsys accessibility | grep -oP '(?<=text=)[^,]*' || echo ''"
                )
                
                if text.lower() in screen_text.lower():
                    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    return VerificationResult(
                        verification_type=VerificationType.TEXT_APPEARED,
                        passed=True,
                        message=f"Text '{text}' found on screen",
                        evidence={
                            "search_text": text,
                            "attempts": attempt + 1,
                        },
                        confidence_score=0.95,
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow(),
                    )
                
                await asyncio.sleep(1)
            
            # Text not found
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return VerificationResult(
                verification_type=VerificationType.TEXT_APPEARED,
                passed=False,
                message=f"Text '{text}' not found on screen",
                evidence={
                    "search_text": text,
                    "timeout_exceeded": True,
                },
                confidence_score=0.7,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
        
        except Exception as e:
            logger.error(f"Error verifying text: {e}")
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return VerificationResult(
                verification_type=VerificationType.TEXT_APPEARED,
                passed=False,
                message=f"Verification failed: {str(e)}",
                evidence={"error": str(e)},
                confidence_score=0.0,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
    
    async def verify_state_changed(
        self,
        device_id: str,
        state_detector: callable,
        expected_state: Any,
        timeout_seconds: int = 10,
    ) -> VerificationResult:
        """
        Verify that device state changed
        
        Args:
            device_id: Device to check
            state_detector: Async function to get current state
            expected_state: Expected state value
            timeout_seconds: Max time to wait
            
        Returns:
            VerificationResult
        """
        start_time = datetime.utcnow()
        
        try:
            for attempt in range(timeout_seconds):
                current_state = await state_detector(device_id)
                
                if current_state == expected_state:
                    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    
                    return VerificationResult(
                        verification_type=VerificationType.STATE_CHANGED,
                        passed=True,
                        message=f"State changed to {expected_state}",
                        evidence={
                            "expected_state": expected_state,
                            "current_state": current_state,
                            "attempts": attempt + 1,
                        },
                        confidence_score=0.98,
                        duration_ms=duration_ms,
                        timestamp=datetime.utcnow(),
                    )
                
                await asyncio.sleep(1)
            
            # State never changed
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            current_state = await state_detector(device_id)
            
            return VerificationResult(
                verification_type=VerificationType.STATE_CHANGED,
                passed=False,
                message=f"State did not change to {expected_state}",
                evidence={
                    "expected_state": expected_state,
                    "current_state": current_state,
                    "timeout_exceeded": True,
                },
                confidence_score=0.6,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
        
        except Exception as e:
            logger.error(f"Error verifying state change: {e}")
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return VerificationResult(
                verification_type=VerificationType.STATE_CHANGED,
                passed=False,
                message=f"Verification failed: {str(e)}",
                evidence={"error": str(e)},
                confidence_score=0.0,
                duration_ms=duration_ms,
                timestamp=datetime.utcnow(),
            )
    
    async def verify_multiple(
        self,
        verifications: List[Dict[str, Any]],
    ) -> List[VerificationResult]:
        """
        Run multiple verifications in parallel
        
        Args:
            verifications: List of verification configs
            
        Returns:
            List of VerificationResults
        """
        tasks = []
        
        for v in verifications:
            if v["type"] == VerificationType.APP_OPENED:
                task = self.verify_app_opened(
                    v["device_id"],
                    v["package_name"],
                    v.get("timeout_seconds", 10)
                )
            elif v["type"] == VerificationType.TEXT_APPEARED:
                task = self.verify_text_appeared(
                    v["device_id"],
                    v["text"],
                    v.get("timeout_seconds", 10)
                )
            else:
                continue
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results


# Global instance
execution_verifier = None


def get_execution_verifier(adb_client=None, device_intelligence=None) -> ExecutionVerifier:
    """Get or create execution verifier"""
    global execution_verifier
    if execution_verifier is None and adb_client and device_intelligence:
        execution_verifier = ExecutionVerifier(adb_client, device_intelligence)
    return execution_verifier
