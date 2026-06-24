"""
APA-OS Agent Runtime
Multi-agent system: Voice, OCR, Navigation, Memory, Automation, Notification agents
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    VOICE = "voice"
    OCR = "ocr"
    NAVIGATION = "navigation"
    MEMORY = "memory"
    AUTOMATION = "automation"
    NOTIFICATION = "notification"
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"


@dataclass
class AgentStatus:
    """Agent status info"""
    agent_type: str
    agent_name: str
    status: str  # running, stopped, error
    device_id: str = ""
    last_heartbeat: Optional[datetime] = None
    error_message: str = ""
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCommand:
    """Command to execute on an agent"""
    agent_type: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    device_id: str = ""
    user_id: str = ""


@dataclass
class AgentResponse:
    """Agent execution response"""
    success: bool
    agent_type: str
    result: Any = None
    error: str = ""
    duration_ms: float = 0.0


class BaseAgent:
    """Base class for all agents"""

    def __init__(self, agent_type: str, agent_name: str):
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.status = "stopped"
        self._config: Dict[str, Any] = {}

    async def start(self, device_id: str, config: Dict[str, Any] = None):
        """Start the agent"""
        self.status = "running"
        self._config = config or {}
        logger.info(f"Agent started: {self.agent_name} on {device_id}")

    async def stop(self):
        """Stop the agent"""
        self.status = "stopped"
        logger.info(f"Agent stopped: {self.agent_name}")

    async def execute(self, command: AgentCommand) -> AgentResponse:
        """Execute a command"""
        raise NotImplementedError

    def get_status(self) -> AgentStatus:
        return AgentStatus(
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            status=self.status,
            config=self._config,
        )


class VoiceAgent(BaseAgent):
    """Voice command processing agent"""

    def __init__(self):
        super().__init__("voice", "Voice Agent")
        self._whisper_model = None

    async def start(self, device_id: str, config: Dict[str, Any] = None):
        await super().start(device_id, config)
        # Initialize Whisper model if available
        try:
            import whisper
            self._whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded for Voice Agent")
        except Exception:
            logger.info("Voice Agent running without local Whisper")

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            if command.action == "transcribe":
                # Transcribe audio file
                audio_path = command.params.get("audio_path", "")
                if self._whisper_model and audio_path:
                    result = self._whisper_model.transcribe(audio_path)
                    return AgentResponse(
                        success=True,
                        agent_type="voice",
                        result={"text": result["text"], "language": result.get("language")},
                        duration_ms=(time.time() - start) * 1000,
                    )
                # Fallback to API
                from services.voice_service import get_voice_service
                voice = get_voice_service()
                text = await voice.transcribe_audio(audio_path)
                return AgentResponse(
                    success=True,
                    agent_type="voice",
                    result={"text": text},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif command.action == "speak":
                # Text to speech
                text = command.params.get("text", "")
                return AgentResponse(
                    success=True,
                    agent_type="voice",
                    result={"spoken": True, "text": text},
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="voice",
                error=f"Unknown action: {command.action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="voice",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


class NavigationAgent(BaseAgent):
    """UI navigation and app control agent"""

    def __init__(self, adb_service=None):
        super().__init__("navigation", "Navigation Agent")
        self._adb = adb_service

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            if not self._adb:
                from services.adb_service import get_adb_service, find_adb_binary
                self._adb = get_adb_service(find_adb_binary())

            device_id = command.device_id
            action = command.action

            if action == "launch_app":
                app = command.params.get("app", "")
                await self._adb.shell(device_id, f"monkey -p {app} 1")
                await asyncio.sleep(2)
                fg = await self._adb.get_foreground_app(device_id)
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"app": app, "foreground": fg},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "tap":
                x = command.params.get("x", 0)
                y = command.params.get("y", 0)
                await self._adb.shell(device_id, f"input tap {x} {y}")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"tapped": True, "x": x, "y": y},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "type":
                text = command.params.get("text", "")
                safe = text.replace(" ", "%s").replace("'", "")
                await self._adb.shell(device_id, f"input text '{safe}'")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"typed": True, "text": text[:50]},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "swipe":
                direction = command.params.get("direction", "down")
                if direction == "down":
                    await self._adb.shell(device_id, "input swipe 500 1000 500 200")
                else:
                    await self._adb.shell(device_id, "input swipe 500 200 500 1000")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"swiped": direction},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "press_key":
                keycode = command.params.get("keycode", 3)
                await self._adb.shell(device_id, f"input keyevent {keycode}")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"key_pressed": keycode},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "go_home":
                await self._adb.shell(device_id, "input keyevent 3")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"home": True},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif action == "go_back":
                await self._adb.shell(device_id, "input keyevent 4")
                return AgentResponse(
                    success=True,
                    agent_type="navigation",
                    result={"back": True},
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="navigation",
                error=f"Unknown action: {action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="navigation",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


class OCRAgent(BaseAgent):
    """OCR and screen understanding agent"""

    def __init__(self, adb_service=None):
        super().__init__("ocr", "OCR Agent")
        self._adb = adb_service

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            device_id = command.device_id

            if command.action == "screenshot_and_ocr":
                from vision.screen_capture import get_screen_capture_service
                from vision.ocr_service import get_ocr_service

                capture = await get_screen_capture_service().capture_from_adb(device_id)
                if not capture.success:
                    return AgentResponse(success=False, agent_type="ocr", error=capture.error)

                ocr = await get_ocr_service().extract_text(capture.image)
                return AgentResponse(
                    success=True,
                    agent_type="ocr",
                    result={
                        "text": ocr.full_text,
                        "elements": len(ocr.texts),
                        "filepath": capture.filepath,
                    },
                    duration_ms=(time.time() - start) * 1000,
                )

            elif command.action == "find_text":
                # Find specific text on screen
                from vision.screen_capture import get_screen_capture_service
                from vision.ocr_service import get_ocr_service

                target = command.params.get("text", "")
                capture = await get_screen_capture_service().capture_from_adb(device_id)
                if not capture.success:
                    return AgentResponse(success=False, agent_type="ocr", error=capture.error)

                ocr = await get_ocr_service().extract_text(capture.image)
                found = [t for t in ocr.texts if target.lower() in t.text.lower()]
                return AgentResponse(
                    success=True,
                    agent_type="ocr",
                    result={"found": bool(found), "matches": [{"text": t.text, "x": t.x, "y": t.y} for t in found]},
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="ocr",
                error=f"Unknown action: {command.action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="ocr",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


class MemoryAgent(BaseAgent):
    """Memory and context agent"""

    def __init__(self):
        super().__init__("memory", "Memory Agent")

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            from memory.engine import get_memory_engine
            engine = get_memory_engine()

            if command.action == "store":
                content = command.params.get("content", "")
                memory_type = command.params.get("type", "general")
                engine.store_memory(
                    user_id=command.user_id,
                    content=content,
                    memory_type=memory_type,
                )
                return AgentResponse(
                    success=True,
                    agent_type="memory",
                    result={"stored": True},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif command.action == "recall":
                query = command.params.get("query", "")
                results = engine.search(query, user_id=command.user_id)
                return AgentResponse(
                    success=True,
                    agent_type="memory",
                    result={"results": results},
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="memory",
                error=f"Unknown action: {command.action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="memory",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


class AutomationAgent(BaseAgent):
    """Automation workflow agent"""

    def __init__(self):
        super().__init__("automation", "Automation Agent")

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            if command.action == "run_rule":
                rule_id = command.params.get("rule_id", "")
                from services.automation_engine import get_automation_engine
                engine = get_automation_engine()
                result = await engine.execute_rule(rule_id, command.user_id, command.device_id)
                return AgentResponse(
                    success=result.get("success", False),
                    agent_type="automation",
                    result=result,
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="automation",
                error=f"Unknown action: {command.action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="automation",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


class NotificationAgent(BaseAgent):
    """Notification management agent"""

    def __init__(self):
        super().__init__("notification", "Notification Agent")

    async def execute(self, command: AgentCommand) -> AgentResponse:
        import time
        start = time.time()

        try:
            if command.action == "send":
                title = command.params.get("title", "")
                body = command.params.get("body", "")
                ntype = command.params.get("type", "info")
                from services.notification_service import get_notification_service
                service = get_notification_service()
                notif_id = service.create_notification(
                    user_id=command.user_id,
                    device_id=command.device_id,
                    title=title,
                    body=body,
                    notification_type=ntype,
                )
                return AgentResponse(
                    success=True,
                    agent_type="notification",
                    result={"notification_id": notif_id},
                    duration_ms=(time.time() - start) * 1000,
                )

            elif command.action == "list":
                from services.notification_service import get_notification_service
                service = get_notification_service()
                notifs = service.get_notifications(command.user_id)
                return AgentResponse(
                    success=True,
                    agent_type="notification",
                    result={"notifications": notifs},
                    duration_ms=(time.time() - start) * 1000,
                )

            return AgentResponse(
                success=False,
                agent_type="notification",
                error=f"Unknown action: {command.action}",
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="notification",
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )


# ==================== Agent Runtime ====================

class AgentRuntime:
    """Manages all agents across devices"""

    def __init__(self, adb_service=None):
        self._adb = adb_service
        self._agents: Dict[str, BaseAgent] = {}
        self._device_agents: Dict[str, List[str]] = {}  # device_id -> [agent_ids]

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    def initialize_agents(self):
        """Initialize all available agents"""
        agent_classes = {
            "voice": VoiceAgent,
            "navigation": lambda: NavigationAgent(self._adb),
            "ocr": lambda: OCRAgent(self._adb),
            "memory": MemoryAgent,
            "automation": AutomationAgent,
            "notification": NotificationAgent,
        }

        for agent_type, cls in agent_classes.items():
            agent = cls() if callable(cls) and not isinstance(cls, type) else cls()
            self._agents[agent_type] = agent

        logger.info(f"Agent runtime initialized with {len(self._agents)} agents")

    async def start_agents_for_device(self, device_id: str, user_id: str, agent_types: List[str] = None):
        """Start agents for a specific device"""
        if not self._agents:
            self.initialize_agents()

        types_to_start = agent_types or list(self._agents.keys())
        started = []

        for agent_type in types_to_start:
            agent = self._agents.get(agent_type)
            if agent:
                try:
                    await agent.start(device_id)
                    started.append(agent_type)
                    self._device_agents.setdefault(device_id, []).append(agent_type)

                    # Store in database
                    self._store_agent_record(device_id, user_id, agent_type, "running")
                except Exception as e:
                    logger.error(f"Failed to start {agent_type} agent: {e}")

        logger.info(f"Started agents for {device_id}: {started}")
        return started

    async def stop_agents_for_device(self, device_id: str):
        """Stop all agents for a device"""
        agent_types = self._device_agents.get(device_id, [])
        for agent_type in agent_types:
            agent = self._agents.get(agent_type)
            if agent:
                await agent.stop()
                self._update_agent_status(device_id, agent_type, "stopped")

        self._device_agents.pop(device_id, None)

    async def execute_on_agent(self, command: AgentCommand) -> AgentResponse:
        """Execute a command on a specific agent"""
        agent = self._agents.get(command.agent_type)
        if not agent:
            return AgentResponse(
                success=False,
                agent_type=command.agent_type,
                error=f"Agent not found: {command.agent_type}",
            )

        return await agent.execute(command)

    def get_all_status(self) -> List[AgentStatus]:
        """Get status of all agents"""
        return [agent.get_status() for agent in self._agents.values()]

    def get_device_agents(self, device_id: str) -> List[AgentStatus]:
        """Get agents running on a specific device"""
        agent_types = self._device_agents.get(device_id, [])
        return [
            self._agents[at].get_status()
            for at in agent_types
            if at in self._agents
        ]

    def _store_agent_record(self, device_id: str, user_id: str, agent_type: str, status: str):
        """Store agent record in database"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceAgent
            agent = DeviceAgent(
                device_id=device_id,
                user_id=user_id,
                agent_type=agent_type,
                agent_name=f"{agent_type.title()} Agent",
                status=status,
                started_at=datetime.utcnow(),
            )
            db.add(agent)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to store agent record: {e}")
            db.rollback()
        finally:
            db.close()

    def _update_agent_status(self, device_id: str, agent_type: str, status: str):
        """Update agent status in database"""
        db = self._get_db()
        try:
            from database.auth_models import DeviceAgent
            agent = db.query(DeviceAgent).filter(
                DeviceAgent.device_id == device_id,
                DeviceAgent.agent_type == agent_type,
                DeviceAgent.status == "running",
            ).first()
            if agent:
                agent.status = status
                agent.stopped_at = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


# ==================== Singleton ====================

_agent_runtime: Optional[AgentRuntime] = None


def get_agent_runtime(adb_service=None) -> AgentRuntime:
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime(adb_service)
    return _agent_runtime
