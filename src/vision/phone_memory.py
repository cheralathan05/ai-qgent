import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from vision.screen_capture import ScreenCaptureResult
from vision.ocr_service import OCRResult
from vision.ui_detector import DetectedUIElement, UIDetectionResult
from vision.screen_classifier import ScreenClassificationResult, ScreenType

logger = logging.getLogger(__name__)


@dataclass
class ScreenRecord:
    device_id: str
    screen_type: ScreenType
    app_name: Optional[str]
    screen_name: Optional[str]
    filepath: Optional[str]
    text_content: str
    elements: List[dict]
    layout_type: str
    detected_at: datetime

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "screen_type": self.screen_type.value if self.screen_type else "unknown",
            "app_name": self.app_name,
            "screen_name": self.screen_name,
            "filepath": self.filepath,
            "text_content": self.text_content[:200],
            "elements_count": len(self.elements),
            "layout_type": self.layout_type,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class NavigationRecord:
    from_screen: Optional[ScreenRecord]
    to_screen: ScreenRecord
    action: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "from_screen": self.from_screen.to_dict() if self.from_screen else None,
            "to_screen": self.to_screen.to_dict(),
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AppContext:
    app_name: str
    current_screen: Optional[str] = None
    last_screen: Optional[str] = None
    last_chat_contact: Optional[str] = None
    last_search_query: Optional[str] = None
    last_action: Optional[str] = None
    last_message: Optional[str] = None
    screen_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "app_name": self.app_name,
            "current_screen": self.current_screen,
            "last_screen": self.last_screen,
            "last_chat_contact": self.last_chat_contact,
            "last_search_query": self.last_search_query,
            "last_action": self.last_action,
            "last_message": self.last_message,
            "screen_count": self.screen_count,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }


@dataclass
class UserContext:
    last_command: Optional[str] = None
    last_intent: Optional[str] = None
    last_app: Optional[str] = None
    last_chat_contact: Optional[str] = None
    last_message_text: Optional[str] = None
    recent_commands: List[str] = field(default_factory=list)
    recent_searches: List[str] = field(default_factory=list)
    recent_contacts: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "last_command": self.last_command,
            "last_intent": self.last_intent,
            "last_app": self.last_app,
            "last_chat_contact": self.last_chat_contact,
            "last_message_text": self.last_message_text,
            "recent_commands": self.recent_commands[-10:],
            "recent_searches": self.recent_searches[-10:],
            "recent_contacts": self.recent_contacts[-10:],
        }


class PhoneMemory:
    MAX_SCREENS_PER_DEVICE = 200
    MAX_NAVIGATIONS_PER_DEVICE = 200

    def __init__(self):
        self._screens: Dict[str, List[ScreenRecord]] = {}
        self._current_screen: Dict[str, Optional[ScreenRecord]] = {}
        self._navigation_history: Dict[str, List[NavigationRecord]] = {}
        self._app_contexts: Dict[str, Dict[str, AppContext]] = {}
        self._user_contexts: Dict[str, UserContext] = {}
        self._screen_changes: Dict[str, List[dict]] = {}

    def record_screen(
        self,
        device_id: str,
        screen_type: ScreenType,
        app_name: Optional[str],
        screen_name: Optional[str],
        filepath: Optional[str],
        text_content: str,
        elements: List[DetectedUIElement],
        layout_type: str = "unknown",
    ) -> ScreenRecord:
        record = ScreenRecord(
            device_id=device_id,
            screen_type=screen_type,
            app_name=app_name,
            screen_name=screen_name,
            filepath=filepath,
            text_content=text_content,
            elements=[e.to_dict() for e in elements],
            layout_type=layout_type,
            detected_at=datetime.utcnow(),
        )

        if device_id not in self._screens:
            self._screens[device_id] = []
            self._navigation_history[device_id] = []
            self._screen_changes[device_id] = []

        prev = self._current_screen.get(device_id)
        self._screens[device_id].append(record)
        self._current_screen[device_id] = record

        if len(self._screens[device_id]) > self.MAX_SCREENS_PER_DEVICE:
            self._screens[device_id] = self._screens[device_id][-self.MAX_SCREENS_PER_DEVICE:]

        if prev and prev.screen_type != screen_type:
            self._screen_changes[device_id].append({
                "from_screen": prev.screen_name or prev.screen_type.value,
                "to_screen": screen_name or screen_type.value,
                "detected_at": record.detected_at.isoformat(),
            })
            nav_record = NavigationRecord(
                from_screen=prev, to_screen=record,
                action=f"{prev.screen_type.value} -> {screen_type.value}",
                timestamp=record.detected_at,
            )
            self._navigation_history[device_id].append(nav_record)
            if len(self._navigation_history[device_id]) > self.MAX_NAVIGATIONS_PER_DEVICE:
                self._navigation_history[device_id] = self._navigation_history[device_id][-self.MAX_NAVIGATIONS_PER_DEVICE:]

        if app_name:
            self._update_app_context(device_id, app_name, screen_name, record)

        logger.info(f"PhoneMemory: recorded {screen_type.value} for {device_id}")
        return record

    def _update_app_context(self, device_id: str, app_name: str, screen_name: Optional[str], record: ScreenRecord):
        if device_id not in self._app_contexts:
            self._app_contexts[device_id] = {}

        contexts = self._app_contexts[device_id]
        if app_name not in contexts:
            contexts[app_name] = AppContext(
                app_name=app_name,
                first_seen=record.detected_at,
            )

        ctx = contexts[app_name]
        ctx.last_screen = ctx.current_screen
        ctx.current_screen = screen_name
        ctx.last_seen = record.detected_at
        ctx.screen_count += 1

    def record_user_action(
        self,
        user_id: str,
        command: Optional[str] = None,
        intent: Optional[str] = None,
        app: Optional[str] = None,
        contact: Optional[str] = None,
        message: Optional[str] = None,
        search_query: Optional[str] = None,
    ):
        if user_id not in self._user_contexts:
            self._user_contexts[user_id] = UserContext()

        ctx = self._user_contexts[user_id]
        if command:
            ctx.last_command = command
            ctx.recent_commands.append(command)
        if intent:
            ctx.last_intent = intent
        if app:
            ctx.last_app = app
            if contact:
                ctx.last_chat_contact = contact
                ctx.recent_contacts.append(contact)
        if message:
            ctx.last_message_text = message
        if search_query:
            ctx.recent_searches.append(search_query)

        if device_id := None:
            pass

    def get_current_screen(self, device_id: str) -> Optional[ScreenRecord]:
        return self._current_screen.get(device_id)

    def get_previous_screen(self, device_id: str) -> Optional[ScreenRecord]:
        screens = self._screens.get(device_id, [])
        if len(screens) >= 2:
            return screens[-2]
        return None

    def get_screen_history(self, device_id: str, limit: int = 50) -> List[ScreenRecord]:
        screens = self._screens.get(device_id, [])
        return screens[-limit:]

    def get_navigation_history(self, device_id: str, limit: int = 50) -> List[NavigationRecord]:
        navs = self._navigation_history.get(device_id, [])
        return navs[-limit:]

    def get_recent_screen_types(self, device_id: str, limit: int = 10) -> List[str]:
        screens = self._screens.get(device_id, [])
        return [s.screen_type.value for s in screens[-limit:]]

    def get_recent_apps(self, device_id: str, limit: int = 10) -> List[str]:
        apps = []
        for s in reversed(self._screens.get(device_id, [])):
            if s.app_name and s.app_name not in apps:
                apps.append(s.app_name)
                if len(apps) >= limit:
                    break
        return apps

    def get_app_context(self, device_id: str, app_name: str) -> Optional[AppContext]:
        return self._app_contexts.get(device_id, {}).get(app_name)

    def get_all_app_contexts(self, device_id: str) -> Dict[str, AppContext]:
        return self._app_contexts.get(device_id, {})

    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        return self._user_contexts.get(user_id)

    def get_screen_changes(self, device_id: str) -> List[dict]:
        return self._screen_changes.get(device_id, [])

    def get_context_summary(self, device_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        current = self.get_current_screen(device_id)
        previous = self.get_previous_screen(device_id)
        recent_apps = self.get_recent_apps(device_id)
        screen_types = self.get_recent_screen_types(device_id)

        summary = {
            "device_id": device_id,
            "current_screen": current.to_dict() if current else None,
            "previous_screen": previous.to_dict() if previous else None,
            "recent_apps": recent_apps,
            "recent_screen_types": screen_types,
            "screen_history_count": len(self._screens.get(device_id, [])),
            "navigation_count": len(self._navigation_history.get(device_id, [])),
            "screen_changes": self.get_screen_changes(device_id)[-10:],
        }

        if user_id:
            summary["user_context"] = self.get_user_context(user_id).to_dict() if self.get_user_context(user_id) else None

        return summary

    def clear_history(self, device_id: str):
        self._screens.pop(device_id, None)
        self._current_screen.pop(device_id, None)
        self._navigation_history.pop(device_id, None)
        self._app_contexts.pop(device_id, None)
        self._screen_changes.pop(device_id, None)
        logger.info(f"PhoneMemory: cleared history for {device_id}")


_phone_memory: Optional[PhoneMemory] = None


def get_phone_memory() -> PhoneMemory:
    global _phone_memory
    if _phone_memory is None:
        _phone_memory = PhoneMemory()
    return _phone_memory
