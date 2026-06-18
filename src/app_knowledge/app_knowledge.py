"""App Knowledge: known screens, buttons, menus, navigation paths, and workflows per app."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScreenDef:
    name: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    menus: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class NavigationPath:
    from_screen: str
    to_screen: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""


@dataclass
class AppDefinition:
    package_name: str
    display_name: str
    screens: Dict[str, ScreenDef] = field(default_factory=dict)
    navigation_paths: List[NavigationPath] = field(default_factory=list)
    known_workflows: List[Dict[str, Any]] = field(default_factory=list)

    def get_screen(self, name: str) -> Optional[ScreenDef]:
        return self.screens.get(name)

    def find_path(self, from_screen: str, to_screen: str) -> Optional[NavigationPath]:
        for path in self.navigation_paths:
            if path.from_screen == from_screen and path.to_screen == to_screen:
                return path
        return None


BUILTIN_APPS: Dict[str, AppDefinition] = {
    "instagram": AppDefinition(
        package_name="com.instagram.android",
        display_name="Instagram",
        screens={
            "feed": ScreenDef(name="feed", buttons=[{"text": "DM", "description": "Open Direct Messages"}]),
            "dm_inbox": ScreenDef(name="dm_inbox", buttons=[{"text": "Search", "description": "Search chats"}]),
            "dm_chat": ScreenDef(name="dm_chat", buttons=[{"text": "Message Input", "description": "Type message"}], elements=[{"type": "input", "id": "message_input"}]),
            "profile": ScreenDef(name="profile"),
            "reels": ScreenDef(name="reels"),
            "settings": ScreenDef(name="settings"),
        },
        navigation_paths=[
            NavigationPath(from_screen="feed", to_screen="dm_inbox", steps=[{"action": "click", "target": "DM"}]),
            NavigationPath(from_screen="dm_inbox", to_screen="dm_chat", steps=[{"action": "click", "target": "chat_item"}]),
        ],
        known_workflows=[
            {"name": "open_dm", "steps": [{"action": "open_app", "app": "instagram"}, {"action": "click", "target": "DM"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}]},
            {"name": "send_message", "steps": [{"action": "open_app", "app": "instagram"}, {"action": "click", "target": "DM"}, {"action": "click", "target": "chat"}, {"action": "type", "target": "message_input"}, {"action": "send"}]},
        ],
    ),
    "whatsapp": AppDefinition(
        package_name="com.whatsapp",
        display_name="WhatsApp",
        screens={
            "chat_list": ScreenDef(name="chat_list", buttons=[{"text": "Search", "description": "Search chats"}]),
            "chat": ScreenDef(name="chat", elements=[{"type": "input", "id": "message_input"}], buttons=[{"text": "Send", "description": "Send message"}]),
            "settings": ScreenDef(name="settings"),
        },
        navigation_paths=[
            NavigationPath(from_screen="chat_list", to_screen="chat", steps=[{"action": "click", "target": "chat_item"}]),
        ],
        known_workflows=[
            {"name": "open_chat", "steps": [{"action": "open_app", "app": "whatsapp"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}]},
            {"name": "send_message", "steps": [{"action": "open_app", "app": "whatsapp"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}, {"action": "type", "target": "message_input"}, {"action": "click", "target": "Send"}]},
        ],
    ),
    "chrome": AppDefinition(
        package_name="com.android.chrome",
        display_name="Chrome",
        screens={
            "browser": ScreenDef(name="browser", elements=[{"type": "input", "id": "url_bar"}]),
            "tab_switcher": ScreenDef(name="tab_switcher"),
            "settings": ScreenDef(name="settings"),
        },
        known_workflows=[
            {"name": "search", "steps": [{"action": "open_app", "app": "chrome"}, {"action": "click", "target": "url_bar"}, {"action": "type", "target": "url_bar"}]},
        ],
    ),
    "youtube": AppDefinition(
        package_name="com.google.android.youtube",
        display_name="YouTube",
        screens={
            "home": ScreenDef(name="home"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "video_player": ScreenDef(name="video_player"),
        },
        known_workflows=[
            {"name": "search_video", "steps": [{"action": "open_app", "app": "youtube"}, {"action": "click", "target": "search_box"}, {"action": "type", "target": "search_box"}]},
        ],
    ),
}


class AppKnowledge:
    """Central registry of known app structures."""

    def __init__(self):
        self._apps: Dict[str, AppDefinition] = dict(BUILTIN_APPS)

    def register_app(self, app: AppDefinition) -> None:
        self._apps[app.package_name] = app
        self._apps[app.display_name.lower()] = app
        logger.info(f"App registered: {app.display_name}")

    def get_app(self, name: str) -> Optional[AppDefinition]:
        key = name.lower().strip()
        return self._apps.get(key)

    def get_known_screens(self, app_name: str) -> Dict[str, ScreenDef]:
        app = self.get_app(app_name)
        return app.screens if app else {}

    def get_known_workflows(self, app_name: str) -> List[Dict[str, Any]]:
        app = self.get_app(app_name)
        return app.known_workflows if app else []

    def resolve_workflow(self, app_name: str, workflow_name: str) -> Optional[List[Dict[str, Any]]]:
        app = self.get_app(app_name)
        if not app:
            return None
        for wf in app.known_workflows:
            if wf.get("name") == workflow_name:
                return wf.get("steps", [])
        return None

    def get_navigation_path(self, app_name: str, from_screen: str, to_screen: str) -> Optional[NavigationPath]:
        app = self.get_app(app_name)
        if not app:
            return None
        return app.find_path(from_screen, to_screen)


_app_knowledge: Optional[AppKnowledge] = None


def get_app_knowledge() -> AppKnowledge:
    global _app_knowledge
    if _app_knowledge is None:
        _app_knowledge = AppKnowledge()
    return _app_knowledge
