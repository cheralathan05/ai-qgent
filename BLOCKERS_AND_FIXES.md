# APA-OS Backend - BLOCKERS & IMMEDIATE FIXES

**Priority:** 🔴 CRITICAL - Fix immediately before any further development

---

## BLOCKER #1: Application Crashes on Startup

### Problem
```
File "main.py", line 68, in lifespan
    app = FastAPI(...)
File "src/api/main.py", line 25, in <module>
    from orchestrator import get_workflow_orchestrator
ImportError: cannot import name 'get_workflow_orchestrator' from 'orchestrator' 
```

### Root Cause
The function `get_workflow_orchestrator()` is imported but never defined.

### Files Affected
- `src/api/main.py` (line 25)
- `src/orchestrator.py` (no singleton implemented)

### Fix (30 mins)
Create a singleton in `src/orchestrator.py`:

```python
# At end of src/orchestrator.py

_orchestrator_instance = None

def get_workflow_orchestrator(
    session=None,
    adb_client=None,
    ollama_client=None,
    contact_db=None,
    app_db=None,
) -> WorkflowOrchestrator:
    """Get or create workflow orchestrator singleton"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = WorkflowOrchestrator(
            session=session,
            adb_client=adb_client,
            ollama_client=ollama_client,
            contact_db=contact_db,
            app_db=app_db,
        )
    
    return _orchestrator_instance
```

---

## BLOCKER #2: Missing Singleton Getters

### Problem
Multiple imports fail with `ImportError`:

```
from reliability.retry_manager import get_retry_manager
from reliability.timeout_manager import get_timeout_manager
from device_intelligence.device_detector import get_device_intelligence
from verification.execution_verifier import get_execution_verifier
from audit.audit_manager import get_audit_manager
from approval_ui.approval_context import get_approval_context_builder
from security.credential_manager import get_credential_manager
from understanding.entity_extractor import get_command_understanding_engine
from console.event_stream import get_event_manager
```

### Root Cause
None of these singleton getters are implemented.

### Files Affected
- `src/reliability/retry_manager.py`
- `src/reliability/timeout_manager.py`
- `src/device_intelligence/device_detector.py`
- `src/verification/execution_verifier.py`
- `src/audit/audit_manager.py`
- `src/approval_ui/approval_context.py`
- `src/security/credential_manager.py`
- `src/understanding/entity_extractor.py`
- `src/console/event_stream.py`

### Fix (2 hours)

**src/reliability/retry_manager.py** - Add at end:
```python
_retry_manager_instance = None

def get_retry_manager() -> RetryManager:
    global _retry_manager_instance
    if _retry_manager_instance is None:
        _retry_manager_instance = RetryManager()
    return _retry_manager_instance
```

**src/reliability/timeout_manager.py** - Add at end:
```python
from config import Config

_timeout_manager_instance = None

def get_timeout_manager() -> TimeoutManager:
    global _timeout_manager_instance
    if _timeout_manager_instance is None:
        config = Config()
        timeout_config = TimeoutConfig(
            intent_detection_timeout=config.INTENT_TIMEOUT,
            planning_timeout=config.PLANNING_TIMEOUT,
            execution_timeout=config.EXECUTION_TIMEOUT,
        )
        _timeout_manager_instance = TimeoutManager(config=timeout_config)
    return _timeout_manager_instance
```

**src/device_intelligence/device_detector.py** - Add at end:
```python
_device_intelligence_instance = None

def get_device_intelligence(adb_client=None) -> DeviceIntelligence:
    global _device_intelligence_instance
    if _device_intelligence_instance is None:
        _device_intelligence_instance = DeviceIntelligence(adb_client=adb_client)
    return _device_intelligence_instance
```

**src/verification/execution_verifier.py** - Add at end:
```python
_execution_verifier_instance = None

def get_execution_verifier(adb_client, device_intelligence) -> ExecutionVerifier:
    global _execution_verifier_instance
    if _execution_verifier_instance is None:
        _execution_verifier_instance = ExecutionVerifier(adb_client, device_intelligence)
    return _execution_verifier_instance
```

**src/audit/audit_manager.py** - Add at end:
```python
_audit_manager_instance = None

def get_audit_manager(session) -> AuditManager:
    global _audit_manager_instance
    if _audit_manager_instance is None:
        _audit_manager_instance = AuditManager(session)
    return _audit_manager_instance
```

**src/approval_ui/approval_context.py** - Add at end:
```python
_approval_context_builder_instance = None

class ApprovalContextBuilder:
    def __init__(self, session):
        self.session = session
    
    # ... existing methods

def get_approval_context_builder(session) -> ApprovalContextBuilder:
    global _approval_context_builder_instance
    if _approval_context_builder_instance is None:
        _approval_context_builder_instance = ApprovalContextBuilder(session)
    return _approval_context_builder_instance
```

**src/security/credential_manager.py** - Add at end:
```python
_credential_manager_instance = None

class CredentialManager:
    def __init__(self, vault_service=None):
        self.secret_manager = SecretManager(vault_service)
    # ... existing methods

def get_credential_manager(vault_service=None) -> CredentialManager:
    global _credential_manager_instance
    if _credential_manager_instance is None:
        _credential_manager_instance = CredentialManager(vault_service)
    return _credential_manager_instance
```

**src/understanding/entity_extractor.py** - Add at end:
```python
_command_understanding_engine_instance = None

class CommandUnderstandingEngine:
    def __init__(self, contact_db=None, app_db=None):
        self.entity_extractor = EntityExtractor()
        self.contact_db = contact_db
        self.app_db = app_db
    
    async def understand(self, command: str) -> IntentResult:
        # Implement full command understanding
        intent = await self._classify_intent(command)
        entities = await self._extract_entities(command)
        return IntentResult(
            intent=intent,
            confidence=0.85,
            entities=entities,
            slots={},
            raw_command=command,
            normalized_command=command.lower(),
        )
    
    # ... other methods

def get_command_understanding_engine(contact_db=None, app_db=None) -> CommandUnderstandingEngine:
    global _command_understanding_engine_instance
    if _command_understanding_engine_instance is None:
        _command_understanding_engine_instance = CommandUnderstandingEngine(contact_db, app_db)
    return _command_understanding_engine_instance
```

**src/console/event_stream.py** - Fix existing:
```python
_event_manager = None

def get_event_manager() -> EventStreamManager:
    global _event_manager
    if _event_manager is None:
        _event_manager = EventStreamManager()
    return _event_manager
```

---

## BLOCKER #3: Database Configuration Missing

### Problem
```
AttributeError: type object 'Config' has no attribute 'get_database_config'
```

### Root Cause
`Config.get_database_config()` is called in `database/connection.py` but the method doesn't exist.

### File Affected
- `src/config.py`
- `src/database/connection.py`

### Fix (15 mins)

**src/config.py** - Add method to Config class:

```python
@classmethod
def get_database_config(cls) -> DatabaseConfig:
    """Get database configuration"""
    if cls.DATABASE_URL:
        return cls.database_config
    
    return DatabaseConfig(
        host=cls.DB_HOST,
        port=cls.DB_PORT,
        user=cls.DB_USER,
        password=cls.DB_PASSWORD,
        database=cls.DB_NAME,
    )
```

Also ensure `DEBUG` flag is set:
```python
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

---

## BLOCKER #4: Missing Orchestrator Execution Method

### Problem
```
AttributeError: 'WorkflowOrchestrator' object has no attribute '_execute_step'
```

### Root Cause
`_execute_step()` method is called at line ~250 but never implemented.

### File Affected
- `src/orchestrator.py` (line 250)

### Fix (4 hours)

Add to WorkflowOrchestrator class:

```python
async def _execute_step(self, step: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """
    Execute a single step
    
    Args:
        step: Step definition
        device_id: Target device
        
    Returns:
        Step result
    """
    step_type = step.get("type", "unknown")
    
    logger.info(f"Executing step: {step_type}")
    
    try:
        if step_type == "open_app":
            return await self._execute_open_app(step, device_id)
        
        elif step_type == "close_app":
            return await self._execute_close_app(step, device_id)
        
        elif step_type == "send_message":
            return await self._execute_send_message(step, device_id)
        
        elif step_type == "verify":
            return await self._execute_verification(step, device_id)
        
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    except Exception as e:
        logger.error(f"Step execution failed: {e}")
        raise


async def _execute_open_app(self, step: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """Execute open app step"""
    app_name = step.get("app_name")
    
    if not app_name:
        raise ValueError("app_name required for open_app step")
    
    device = self.device_manager.get_device(device_id)
    
    if device is None:
        raise RuntimeError(f"Device not found: {device_id}")
    
    result = await device.launch_app(app_name)
    
    return {
        "type": "open_app",
        "app": app_name,
        "status": result.get("status", "unknown"),
        "result": result,
    }


async def _execute_close_app(self, step: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """Execute close app step"""
    app_name = step.get("app_name")
    
    return {
        "type": "close_app",
        "app": app_name,
        "status": "not_implemented",
    }


async def _execute_send_message(self, step: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """Execute send message step"""
    recipient = step.get("recipient")
    message = step.get("message")
    
    return {
        "type": "send_message",
        "recipient": recipient,
        "status": "not_implemented",
    }


async def _execute_verification(self, step: Dict[str, Any], device_id: str) -> Dict[str, Any]:
    """Execute verification step"""
    verification_type = step.get("verification_type")
    
    return {
        "type": "verify",
        "verification_type": verification_type,
        "status": "not_implemented",
    }


def _create_plan_steps(self, intent_result) -> List[Dict[str, Any]]:
    """
    Create execution plan from intent
    
    MVP: Simple pattern-based plan generation
    """
    intent = intent_result.intent
    
    if intent == IntentType.OPEN_APP:
        app_entity = next(
            (e for e in intent_result.entities if e.type == "app"),
            None
        )
        
        if app_entity:
            return [
                {
                    "type": "open_app",
                    "app_name": app_entity.value,
                    "description": f"Launch {app_entity.value}",
                }
            ]
    
    elif intent == IntentType.CLOSE_APP:
        app_entity = next(
            (e for e in intent_result.entities if e.type == "app"),
            None
        )
        
        if app_entity:
            return [
                {
                    "type": "close_app",
                    "app_name": app_entity.value,
                    "description": f"Close {app_entity.value}",
                }
            ]
    
    # Default: return empty plan
    return []
```

---

## BLOCKER #5: Event Manager Not Initialized

### Problem
```
RuntimeError: Event manager not initialized
```

### Root Cause
`get_event_manager()` uses module-level `_event_manager` but it's never created.

### File Affected
- `src/console/event_stream.py`
- `main.py`

### Fix (15 mins)

**main.py** - Fix initialization:

```python
from console.event_stream import (
    get_event_manager,
    EventStreamManager,  # Add import
    ConsoleEventSubscriber,
    DatabaseEventSubscriber,
    WebSocketEventSubscriber,
)

# In lifespan():
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    
    # Initialize event manager BEFORE using it
    from console.event_stream import _event_manager as set_event_manager
    event_manager = EventStreamManager()
    
    # Store in module
    import console.event_stream
    console.event_stream._event_manager = event_manager
    
    # ... rest of startup
```

Or better, fix in `event_stream.py`:

```python
# At module level, after classes
_event_manager: Optional[EventStreamManager] = None

def initialize_event_manager() -> EventStreamManager:
    """Initialize and return event manager singleton"""
    global _event_manager
    if _event_manager is None:
        _event_manager = EventStreamManager()
    return _event_manager

def get_event_manager() -> EventStreamManager:
    """Get event manager (must be initialized first)"""
    global _event_manager
    if _event_manager is None:
        _event_manager = initialize_event_manager()
    return _event_manager
```

Then in `main.py` lifespan:
```python
event_manager = initialize_event_manager()
```

---

## BLOCKER #6: Incomplete Entity Extraction

### Problem
```
AttributeError: 'EntityExtractor' object has no attribute 'understand'
```

### Root Cause
`EntityExtractor.understand()` method doesn't exist; only `extract_app()` stub.

### File Affected
- `src/understanding/entity_extractor.py`

### Fix (2 hours)

Complete the EntityExtractor class:

```python
async def understand(self, command: str) -> IntentResult:
    """Understand user command end-to-end"""
    
    # Normalize
    normalized = command.lower().strip()
    
    # Extract intent
    intent = self._detect_intent(normalized)
    
    # Extract entities
    app_entity = self.extract_app(normalized)
    contact_entity = self._extract_contact(normalized)
    text_entity = self._extract_text(normalized)
    
    entities = []
    if app_entity:
        entities.append(app_entity)
    if contact_entity:
        entities.append(contact_entity)
    if text_entity:
        entities.append(text_entity)
    
    confidence = 0.85 if entities else 0.5
    
    return IntentResult(
        intent=intent,
        confidence=confidence,
        entities=entities,
        slots={
            "app": app_entity.value if app_entity else None,
            "contact": contact_entity.value if contact_entity else None,
            "text": text_entity.value if text_entity else None,
        },
        raw_command=command,
        normalized_command=normalized,
    )


def _detect_intent(self, text: str) -> IntentType:
    """Detect intent from text"""
    
    # Simple pattern matching for MVP
    if any(word in text for word in ["open", "launch", "start", "show"]):
        return IntentType.OPEN_APP
    elif any(word in text for word in ["close", "exit", "quit"]):
        return IntentType.CLOSE_APP
    elif any(word in text for word in ["send", "message", "text"]):
        return IntentType.SEND_MESSAGE
    elif any(word in text for word in ["call", "phone"]):
        return IntentType.MAKE_CALL
    elif any(word in text for word in ["search", "find", "look"]):
        return IntentType.SEARCH
    
    return IntentType.UNKNOWN


def _extract_contact(self, text: str) -> Optional[Entity]:
    """Extract contact name from text"""
    
    # Simple pattern matching
    for pattern in self.CONTACT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            contact_name = match.group(1)
            return Entity(
                type="contact",
                value=contact_name,
                confidence=0.8,
            )
    
    return None


def _extract_text(self, text: str) -> Optional[Entity]:
    """Extract message text from command"""
    
    # Look for quoted text
    quoted = re.search(r'["\']([^"\']+)["\']', text)
    if quoted:
        return Entity(
            type="text",
            value=quoted.group(1),
            confidence=0.95,
        )
    
    return None
```

---

## BLOCKER #7: Missing Android ADB Implementation

### Problem
All AndroidDevice methods return stubs:
```python
async def launch_app(self, app_name: str) -> Dict[str, Any]:
    return {"status": "error", "message": "Android launch not implemented"}
```

### Impact
Any Android workflow will fail immediately.

### Files Affected
- `src/devices/android/android_device.py`
- `src/device_intelligence/device_detector.py` (partially used)

### Fix (8 hours - can delay for MVP)

Create `src/devices/android/adb_manager.py`:

```python
"""ADB Manager - communicates with Android devices via USB"""

import subprocess
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ADBManager:
    """Manages ADB connections and commands"""
    
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path
    
    def get_connected_devices(self) -> List[str]:
        """Get list of connected device serial numbers"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            devices = [
                line.split()[0] for line in lines
                if line.strip() and "device" in line
            ]
            
            return devices
        
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return []
    
    def is_device_connected(self, device_serial: str) -> bool:
        """Check if device is connected"""
        devices = self.get_connected_devices()
        return device_serial in devices
    
    def shell(self, device_serial: str, command: str, timeout: int = 10) -> str:
        """Execute shell command on device"""
        try:
            result = subprocess.run(
                [self.adb_path, "-s", device_serial, "shell", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return result.stdout.strip()
        
        except Exception as e:
            logger.error(f"ADB shell error: {e}")
            raise
    
    def get_package_version(self, device_serial: str, package: str) -> Optional[str]:
        """Get installed app version"""
        try:
            output = self.shell(
                device_serial,
                f"dumpsys package {package} | grep versionName"
            )
            
            if "versionName=" in output:
                return output.split("versionName=")[1]
            
            return None
        
        except Exception:
            return None
    
    def launch_app(self, device_serial: str, package: str, activity: str = ".MainActivity") -> bool:
        """Launch app on device"""
        try:
            intent = f"{package}/{package}{activity}"
            self.shell(device_serial, f"am start -n {intent}")
            return True
        except Exception:
            return False
    
    def close_app(self, device_serial: str, package: str) -> bool:
        """Force close app"""
        try:
            self.shell(device_serial, f"am force-stop {package}")
            return True
        except Exception:
            return False
    
    def get_foreground_app(self, device_serial: str) -> Optional[str]:
        """Get currently focused app package"""
        try:
            output = self.shell(
                device_serial,
                "dumpsys window windows | grep -E 'mFocusedApp'"
            )
            
            if "mFocusedApp" in output:
                # Parse package name
                import re
                match = re.search(r"(\w+\.\w+(?:\.\w+)*)", output)
                if match:
                    return match.group(1)
            
            return None
        
        except Exception:
            return None
    
    def get_battery_level(self, device_serial: str) -> Optional[int]:
        """Get battery percentage"""
        try:
            output = self.shell(device_serial, "dumpsys battery | grep level")
            
            if "level:" in output:
                return int(output.split(":")[1].strip())
            
            return None
        
        except Exception:
            return None
    
    def is_device_locked(self, device_serial: str) -> bool:
        """Check if device screen is locked"""
        try:
            output = self.shell(device_serial, "dumpsys window windows | grep 'mShowingLockscreen'")
            return "true" in output.lower()
        except Exception:
            return False
```

Then update `src/devices/android/android_device.py`:

```python
"""Android device abstraction for APA-OS."""
import logging
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus
from .adb_manager import ADBManager

logger = logging.getLogger(__name__)


class AndroidDevice(Device):
    """Android device abstraction for ADB-driven control."""

    def __init__(self, device_id: str, adb_client: ADBManager = None, **kwargs):
        super().__init__(device_id)
        self.adb = adb_client or ADBManager()

    async def get_info(self) -> DeviceInfo:
        """Return actual Android device info via ADB."""
        try:
            is_connected = self.adb.is_device_connected(self.device_id)
            
            if not is_connected:
                return DeviceInfo(
                    device_id=self.device_id,
                    status=DeviceStatus.DISCONNECTED,
                    is_locked=False,
                    battery_level=None,
                    foreground_app=None,
                    installed_apps=set(),
                    capabilities={"android"},
                )
            
            foreground_app = self.adb.get_foreground_app(self.device_id)
            battery_level = self.adb.get_battery_level(self.device_id)
            is_locked = self.adb.is_device_locked(self.device_id)
            
            return DeviceInfo(
                device_id=self.device_id,
                status=DeviceStatus.CONNECTED,
                is_locked=is_locked,
                battery_level=battery_level,
                foreground_app=foreground_app,
                installed_apps=set(),
                capabilities={"android", "touch", "camera", "microphone"},
                model_name="Android Device",
                os_version="Android",
            )
        
        except Exception as e:
            logger.error(f"Error getting Android device info: {e}")
            return DeviceInfo(
                device_id=self.device_id,
                status=DeviceStatus.DISCONNECTED,
                is_locked=False,
                battery_level=None,
                foreground_app=None,
                installed_apps=set(),
                capabilities={"android"},
            )

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch app using ADB."""
        try:
            # Map app name to package name
            package_name = self._resolve_package(app_name)
            
            if not package_name:
                return {"status": "error", "message": f"Unknown app: {app_name}"}
            
            success = self.adb.launch_app(self.device_id, package_name)
            
            if success:
                return {"status": "success", "app": app_name, "package": package_name}
            else:
                return {"status": "error", "message": f"Failed to launch {app_name}"}
        
        except Exception as e:
            logger.error(f"Error launching app: {e}")
            return {"status": "error", "message": str(e)}

    def _resolve_package(self, app_name: str) -> Optional[str]:
        """Resolve app name to package name"""
        app_packages = {
            "instagram": "com.instagram.android",
            "whatsapp": "com.whatsapp",
            "facebook": "com.facebook.katana",
            "gmail": "com.google.android.gm",
            "maps": "com.google.android.apps.maps",
            "chrome": "com.android.chrome",
            "youtube": "com.google.android.youtube",
        }
        
        return app_packages.get(app_name.lower())
```

---

## BLOCKER #8: Ollama LLM Not Connected

### Problem
No LLM integration; planning uses hardcoded stubs.

### Impact
No intent classification, no dynamic planning.

### File Affected
- `src/config.py` (OllamaConfig defined)
- `src/orchestrator.py` (not used)

### Fix for MVP (4 hours - can use stubs)

Create basic Ollama integration:

```python
# In src/orchestrator.py

async def _call_ollama_for_planning(
    self,
    intent: str,
    entities: List[Entity],
) -> List[Dict[str, Any]]:
    """
    Call Ollama to generate execution plan
    
    MVP: For now, use simple rules instead
    """
    
    # Rule-based planning for MVP
    if intent == IntentType.OPEN_APP.value:
        app_name = next(
            (e.value for e in entities if e.type == "app"),
            "unknown"
        )
        
        return [
            {
                "type": "open_app",
                "app_name": app_name,
                "description": f"Open {app_name}",
            }
        ]
    
    return []
```

For production, integrate Ollama:

```python
from httpx import AsyncClient

class OllamaLLM:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        self.client = AsyncClient(base_url=base_url)
    
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate response from Ollama"""
        response = await self.client.post(
            "/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1,
            }
        )
        
        return response.json().get("response", "")
```

---

## SUMMARY: Priority of Fixes

| Priority | Blocker | Est. Time | Impact |
|----------|---------|-----------|--------|
| 🔴 1 | App crashes on startup (fix #1-2) | 2.5 hrs | CRITICAL |
| 🔴 2 | Database config missing (#3) | 0.25 hrs | CRITICAL |
| 🔴 3 | Event manager init (#5) | 0.25 hrs | CRITICAL |
| 🔴 4 | Orchestrator._execute_step (#4) | 4 hrs | CRITICAL |
| 🔴 5 | Entity extraction (#6) | 2 hrs | CRITICAL |
| 🔴 6 | Android ADB (#7) | 8 hrs | HIGH (can stub) |
| 🟠 7 | Ollama integration (#8) | 4 hrs | MEDIUM (can stub) |

**Total Time to MVP:** ~9 hours (with stubs for ADB/Ollama)

