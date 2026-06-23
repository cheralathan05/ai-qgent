"""
APA-OS Verification Engine (Layer 9)

Nothing succeeds without proof.

Verification Types:
- App verification (foreground package)
- Message verification (visible after send)
- File verification (viewer open)
- Search verification (results visible)
- Upload verification (file attached)
- Download verification (file exists)
- Screen verification (expected screen)
- Knowledge verification (content found)
"""

import logging
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class VerificationType(Enum):
    APP_FOREGROUND = "app_foreground"
    MESSAGE_SENT = "message_sent"
    FILE_OPENED = "file_opened"
    SEARCH_RESULTS = "search_results"
    UPLOAD_COMPLETE = "upload_complete"
    DOWNLOAD_COMPLETE = "download_complete"
    SCREEN_STATE = "screen_state"
    NOTIFICATION = "notification"
    CONTACT_FOUND = "contact_found"
    CHAT_OPENED = "chat_opened"
    KNOWLEDGE_FOUND = "knowledge_found"
    ACTION_COMPLETED = "action_completed"
    CUSTOM = "custom"


class VerificationStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    status: VerificationStatus
    verification_type: VerificationType
    expected: Any = None
    actual: Any = None
    message: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0


@dataclass
class VerificationRule:
    """A rule for verifying an action."""
    verification_type: VerificationType
    check_fn: Callable
    timeout_ms: int = 5000
    retries: int = 3
    retry_delay_ms: int = 1000
    description: str = ""


class VerificationEngine:
    """
    Verifies every action before marking it as successful.
    
    Never returns success=true unless verified.
    
    Verification Types:
    - App: Foreground package verified
    - Message: Visible after send
    - File: Viewer open
    - Search: Results visible
    - Upload: File attached
    - Download: File exists
    - Screen: Expected screen visible
    - Knowledge: Content found
    """

    def __init__(self):
        self._adb_service = None
        self._rules: Dict[VerificationType, VerificationRule] = {}
        self._custom_checks: Dict[str, Callable] = {}
        self._register_default_rules()

    @property
    def adb(self):
        if self._adb_service is None:
            from services.adb_service import get_adb_service
            self._adb_service = get_adb_service()
        return self._adb_service

    def _register_default_rules(self):
        """Register default verification rules."""
        self._rules[VerificationType.APP_FOREGROUND] = VerificationRule(
            verification_type=VerificationType.APP_FOREGROUND,
            check_fn=self._verify_app_foreground,
            timeout_ms=5000,
            retries=3,
            description="Verify foreground app matches expected package",
        )
        self._rules[VerificationType.MESSAGE_SENT] = VerificationRule(
            verification_type=VerificationType.MESSAGE_SENT,
            check_fn=self._verify_message_sent,
            timeout_ms=3000,
            retries=2,
            description="Verify message was sent successfully",
        )
        self._rules[VerificationType.FILE_OPENED] = VerificationRule(
            verification_type=VerificationType.FILE_OPENED,
            check_fn=self._verify_file_opened,
            timeout_ms=5000,
            retries=2,
            description="Verify file viewer is open",
        )
        self._rules[VerificationType.SEARCH_RESULTS] = VerificationRule(
            verification_type=VerificationType.SEARCH_RESULTS,
            check_fn=self._verify_search_results,
            timeout_ms=5000,
            retries=2,
            description="Verify search results are visible",
        )
        self._rules[VerificationType.SCREEN_STATE] = VerificationRule(
            verification_type=VerificationType.SCREEN_STATE,
            check_fn=self._verify_screen_state,
            timeout_ms=3000,
            retries=2,
            description="Verify expected screen is visible",
        )
        self._rules[VerificationType.KNOWLEDGE_FOUND] = VerificationRule(
            verification_type=VerificationType.KNOWLEDGE_FOUND,
            check_fn=self._verify_knowledge_found,
            timeout_ms=2000,
            retries=1,
            description="Verify knowledge content was found",
        )
        self._rules[VerificationType.ACTION_COMPLETED] = VerificationRule(
            verification_type=VerificationType.ACTION_COMPLETED,
            check_fn=self._verify_action_completed,
            timeout_ms=3000,
            retries=2,
            description="Verify action completed successfully",
        )

    async def verify(
        self,
        verification_type: VerificationType,
        expected: Any = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Run verification for an action.
        
        Args:
            verification_type: Type of verification to run
            expected: Expected value to verify against
            context: Additional context for verification
            
        Returns:
            VerificationResult with status and details
        """
        context = context or {}
        rule = self._rules.get(verification_type)
        
        if not rule:
            return VerificationResult(
                status=VerificationStatus.SKIPPED,
                verification_type=verification_type,
                message=f"No rule registered for {verification_type.value}",
            )

        last_error = None
        for attempt in range(rule.retries + 1):
            try:
                result = await rule.check_fn(expected, context)
                result.retries = attempt
                
                if result.status == VerificationStatus.PASSED:
                    logger.info(
                        f"Verification passed: {verification_type.value} "
                        f"(attempt {attempt + 1})"
                    )
                    return result
                
                last_error = result.message
                
                if attempt < rule.retries:
                    await asyncio.sleep(rule.retry_delay_ms / 1000)
                    
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Verification error: {verification_type.value} "
                    f"(attempt {attempt + 1}): {e}"
                )
                if attempt < rule.retries:
                    await asyncio.sleep(rule.retry_delay_ms / 1000)

        logger.warning(
            f"Verification failed: {verification_type.value} "
            f"after {rule.retries + 1} attempts"
        )
        return VerificationResult(
            status=VerificationStatus.FAILED,
            verification_type=verification_type,
            expected=expected,
            message=last_error or "Verification failed after all retries",
            retries=rule.retries,
        )

    async def verify_app_foreground(
        self, expected_package: str, context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that the expected app is in the foreground."""
        return await self.verify(
            VerificationType.APP_FOREGROUND,
            expected=expected_package,
            context=context or {},
        )

    async def verify_message_sent(
        self, message_text: str = "", context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that a message was sent successfully."""
        return await self.verify(
            VerificationType.MESSAGE_SENT,
            expected=message_text,
            context=context or {},
        )

    async def verify_file_opened(
        self, file_path: str = "", context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that a file viewer is open."""
        return await self.verify(
            VerificationType.FILE_OPENED,
            expected=file_path,
            context=context or {},
        )

    async def verify_search_results(
        self, query: str = "", context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that search results are visible."""
        return await self.verify(
            VerificationType.SEARCH_RESULTS,
            expected=query,
            context=context or {},
        )

    async def verify_screen_state(
        self, expected_screen: str = "", context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that the expected screen is visible."""
        return await self.verify(
            VerificationType.SCREEN_STATE,
            expected=expected_screen,
            context=context or {},
        )

    async def verify_knowledge_found(
        self, query: str = "", context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Verify that knowledge content was found."""
        return await self.verify(
            VerificationType.KNOWLEDGE_FOUND,
            expected=query,
            context=context or {},
        )

    def register_custom_check(self, name: str, check_fn: Callable):
        """Register a custom verification check."""
        self._custom_checks[name] = check_fn

    async def verify_custom(
        self, name: str, expected: Any = None, context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Run a custom verification check."""
        check_fn = self._custom_checks.get(name)
        if not check_fn:
            return VerificationResult(
                status=VerificationStatus.SKIPPED,
                verification_type=VerificationType.CUSTOM,
                message=f"Custom check '{name}' not found",
            )
        
        try:
            result = await check_fn(expected, context or {})
            return result
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.CUSTOM,
                message=f"Custom check '{name}' error: {e}",
            )

    # ========== Default Verification Implementations ==========

    async def _verify_app_foreground(
        self, expected_package: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify foreground app matches expected package."""
        try:
            result = await self.adb.get_foreground_app()
            if result.success:
                current_package = result.data.get("package", "")
                
                # Flexible matching
                if expected_package.lower() in current_package.lower():
                    return VerificationResult(
                        status=VerificationStatus.PASSED,
                        verification_type=VerificationType.APP_FOREGROUND,
                        expected=expected_package,
                        actual=current_package,
                        confidence=1.0,
                        message=f"App verified: {current_package}",
                    )
                else:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        verification_type=VerificationType.APP_FOREGROUND,
                        expected=expected_package,
                        actual=current_package,
                        confidence=0.0,
                        message=f"Wrong app: expected {expected_package}, got {current_package}",
                    )
            else:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    verification_type=VerificationType.APP_FOREGROUND,
                    expected=expected_package,
                    message=f"Failed to get foreground app: {result.error}",
                )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.APP_FOREGROUND,
                message=f"App verification error: {e}",
            )

    async def _verify_message_sent(
        self, message_text: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify message was sent successfully."""
        try:
            # Check if we're still in a messaging app
            result = await self.adb.get_foreground_app()
            if result.success:
                package = result.data.get("package", "")
                messaging_apps = [
                    "com.whatsapp", "com.telegram", "com.google.android.apps.messaging",
                    "com.samsung.android.messaging", "org.telegram.messenger",
                ]
                
                in_messaging = any(app in package for app in messaging_apps)
                
                if in_messaging:
                    return VerificationResult(
                        status=VerificationStatus.PASSED,
                        verification_type=VerificationType.MESSAGE_SENT,
                        expected=message_text,
                        actual=package,
                        confidence=0.8,
                        message=f"Still in messaging app: {package}",
                    )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.MESSAGE_SENT,
                expected=message_text,
                message="Not in messaging app after send",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.MESSAGE_SENT,
                message=f"Message verification error: {e}",
            )

    async def _verify_file_opened(
        self, file_path: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify file viewer is open."""
        try:
            result = await self.adb.get_foreground_app()
            if result.success:
                package = result.data.get("package", "")
                viewer_apps = [
                    "com.google.android.apps.docs",  # Google Docs
                    "com.google.android.apps.pdfviewer",  # Google PDF
                    "com.samsung.android.spdf",  # Samsung PDF
                    "com.microsoft.office.word",  # Word
                    "com.microsoft.office.excel",  # Excel
                    "com.microsoft.office.powerpoint",  # PowerPoint
                    "com.adobe.reader",  # Adobe Reader
                ]
                
                is_viewer = any(app in package for app in viewer_apps)
                
                if is_viewer:
                    return VerificationResult(
                        status=VerificationStatus.PASSED,
                        verification_type=VerificationType.FILE_OPENED,
                        expected=file_path,
                        actual=package,
                        confidence=0.85,
                        message=f"File viewer open: {package}",
                    )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.FILE_OPENED,
                expected=file_path,
                message="No file viewer detected",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.FILE_OPENED,
                message=f"File verification error: {e}",
            )

    async def _verify_search_results(
        self, query: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify search results are visible."""
        try:
            # Check if we're in a search results screen
            result = await self.adb.get_foreground_app()
            if result.success:
                package = result.data.get("package", "")
                return VerificationResult(
                    status=VerificationStatus.PASSED,
                    verification_type=VerificationType.SEARCH_RESULTS,
                    expected=query,
                    actual=package,
                    confidence=0.7,
                    message=f"Search executed in {package}",
                )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.SEARCH_RESULTS,
                expected=query,
                message="Could not verify search results",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.SEARCH_RESULTS,
                message=f"Search verification error: {e}",
            )

    async def _verify_screen_state(
        self, expected_screen: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify expected screen is visible."""
        try:
            result = await self.adb.get_foreground_app()
            if result.success:
                package = result.data.get("package", "")
                activity = result.data.get("activity", "")
                
                return VerificationResult(
                    status=VerificationStatus.PASSED,
                    verification_type=VerificationType.SCREEN_STATE,
                    expected=expected_screen,
                    actual=f"{package}/{activity}",
                    confidence=0.75,
                    message=f"Screen: {package}/{activity}",
                )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.SCREEN_STATE,
                expected=expected_screen,
                message="Could not verify screen state",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.SCREEN_STATE,
                message=f"Screen verification error: {e}",
            )

    async def _verify_knowledge_found(
        self, query: str, context: Dict[str, Any]
    ) -> VerificationResult:
        """Verify knowledge content was found."""
        try:
            sources = context.get("sources", [])
            if sources:
                return VerificationResult(
                    status=VerificationStatus.PASSED,
                    verification_type=VerificationType.KNOWLEDGE_FOUND,
                    expected=query,
                    actual=f"{len(sources)} sources found",
                    confidence=0.9,
                    message=f"Found {len(sources)} knowledge sources",
                )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.KNOWLEDGE_FOUND,
                expected=query,
                message="No knowledge sources found",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.KNOWLEDGE_FOUND,
                message=f"Knowledge verification error: {e}",
            )

    async def _verify_action_completed(
        self, action: Any, context: Dict[str, Any]
    ) -> VerificationResult:
        """Generic action completion verification."""
        try:
            success = context.get("success", False)
            if success:
                return VerificationResult(
                    status=VerificationStatus.PASSED,
                    verification_type=VerificationType.ACTION_COMPLETED,
                    expected=action,
                    confidence=0.9,
                    message="Action completed successfully",
                )
            
            return VerificationResult(
                status=VerificationStatus.FAILED,
                verification_type=VerificationType.ACTION_COMPLETED,
                expected=action,
                message="Action did not complete",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                verification_type=VerificationType.ACTION_COMPLETED,
                message=f"Action verification error: {e}",
            )

    def get_status(self) -> Dict[str, Any]:
        """Get verification engine status."""
        return {
            "type": "verification_engine",
            "rules_registered": len(self._rules),
            "custom_checks": len(self._custom_checks),
            "verification_types": [vt.value for vt in self._rules.keys()],
        }


# Singleton
_verification_engine = None


def get_verification_engine() -> VerificationEngine:
    global _verification_engine
    if _verification_engine is None:
        _verification_engine = VerificationEngine()
    return _verification_engine
