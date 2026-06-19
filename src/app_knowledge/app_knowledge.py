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
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
        },
        navigation_paths=[
            NavigationPath(from_screen="feed", to_screen="dm_inbox", steps=[{"action": "click", "target": "DM", "description": "Tap DM icon"}]),
            NavigationPath(from_screen="dm_inbox", to_screen="dm_chat", steps=[{"action": "click", "target": "chat_item", "description": "Tap chat"}]),
            NavigationPath(from_screen="dm_inbox", to_screen="search", steps=[{"action": "click", "target": "search", "description": "Tap search"}]),
            NavigationPath(from_screen="feed", to_screen="profile", steps=[{"action": "click", "target": "profile_icon", "description": "Tap profile"}]),
        ],
        known_workflows=[
            {"name": "open_dm", "steps": [{"action": "open_app", "app": "instagram"}, {"action": "click", "target": "DM"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}]},
            {"name": "open_chat", "steps": [{"action": "open_app", "app": "instagram"}, {"action": "click", "target": "DM"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}]},
            {"name": "send_message", "steps": [{"action": "open_app", "app": "instagram"}, {"action": "click", "target": "DM"}, {"action": "click", "target": "chat"}, {"action": "type", "target": "message_input"}, {"action": "send"}]},
        ],
    ),
    "whatsapp": AppDefinition(
        package_name="com.whatsapp",
        display_name="WhatsApp",
        screens={
            "chat_list": ScreenDef(name="chat_list", buttons=[{"text": "New Chat", "description": "Start new chat"}, {"text": "Search", "description": "Search chats"}]),
            "chat": ScreenDef(name="chat", elements=[{"type": "input", "id": "message_input"}], buttons=[{"text": "Send", "description": "Send message"}, {"text": "Attach", "description": "Attach file"}]),
            "settings": ScreenDef(name="settings"),
            "calls": ScreenDef(name="calls"),
            "status": ScreenDef(name="status"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
        },
        navigation_paths=[
            NavigationPath(from_screen="chat_list", to_screen="chat", steps=[{"action": "click", "target": "chat_item", "description": "Tap chat"}]),
            NavigationPath(from_screen="chat_list", to_screen="search", steps=[{"action": "click", "target": "search", "description": "Tap search icon"}]),
            NavigationPath(from_screen="chat_list", to_screen="settings", steps=[{"action": "click", "target": "menu", "description": "Open menu"}, {"action": "click", "target": "settings", "description": "Tap settings"}]),
            NavigationPath(from_screen="chat_list", to_screen="calls", steps=[{"action": "click", "target": "calls_tab", "description": "Tap calls tab"}]),
            NavigationPath(from_screen="chat_list", to_screen="status", steps=[{"action": "click", "target": "status_tab", "description": "Tap status tab"}]),
        ],
        known_workflows=[
            {"name": "open_chat", "steps": [{"action": "open_app", "app": "whatsapp"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}]},
            {"name": "send_message", "steps": [{"action": "open_app", "app": "whatsapp"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}, {"action": "type", "target": "message_input"}, {"action": "click", "target": "Send"}]},
            {"name": "new_chat", "steps": [{"action": "open_app", "app": "whatsapp"}, {"action": "click", "target": "New Chat"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "contact_result"}]},
        ],
    ),
    "chrome": AppDefinition(
        package_name="com.android.chrome",
        display_name="Chrome",
        screens={
            "browser": ScreenDef(name="browser", elements=[{"type": "input", "id": "url_bar"}]),
            "tab_switcher": ScreenDef(name="tab_switcher"),
            "settings": ScreenDef(name="settings"),
            "new_tab": ScreenDef(name="new_tab"),
            "bookmarks": ScreenDef(name="bookmarks"),
            "history": ScreenDef(name="history"),
        },
        navigation_paths=[
            NavigationPath(from_screen="browser", to_screen="tab_switcher", steps=[{"action": "click", "target": "tabs", "description": "Tap tabs icon"}]),
            NavigationPath(from_screen="browser", to_screen="settings", steps=[{"action": "click", "target": "menu", "description": "Open menu"}, {"action": "click", "target": "settings", "description": "Tap settings"}]),
            NavigationPath(from_screen="browser", to_screen="bookmarks", steps=[{"action": "click", "target": "menu", "description": "Open menu"}, {"action": "click", "target": "bookmarks", "description": "Tap bookmarks"}]),
            NavigationPath(from_screen="new_tab", to_screen="browser", steps=[{"action": "click", "target": "url_bar", "description": "Tap URL bar"}, {"action": "type", "target": "url_bar"}]),
        ],
        known_workflows=[
            {"name": "search", "steps": [{"action": "open_app", "app": "chrome"}, {"action": "click", "target": "url_bar"}, {"action": "type", "target": "url_bar"}]},
            {"name": "open_tabs", "steps": [{"action": "open_app", "app": "chrome"}, {"action": "click", "target": "tabs"}]},
        ],
    ),
    "youtube": AppDefinition(
        package_name="com.google.android.youtube",
        display_name="YouTube",
        screens={
            "home": ScreenDef(name="home"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "video_player": ScreenDef(name="video_player"),
            "subscriptions": ScreenDef(name="subscriptions"),
            "library": ScreenDef(name="library"),
            "trending": ScreenDef(name="trending"),
        },
        navigation_paths=[
            NavigationPath(from_screen="home", to_screen="search", steps=[{"action": "click", "target": "search_icon", "description": "Tap search"}]),
            NavigationPath(from_screen="home", to_screen="subscriptions", steps=[{"action": "click", "target": "subscriptions_tab", "description": "Tap subscriptions"}]),
            NavigationPath(from_screen="home", to_screen="library", steps=[{"action": "click", "target": "library_tab", "description": "Tap library"}]),
            NavigationPath(from_screen="home", to_screen="trending", steps=[{"action": "click", "target": "trending_tab", "description": "Tap trending"}]),
            NavigationPath(from_screen="search", to_screen="video_player", steps=[{"action": "click", "target": "video_result", "description": "Tap video"}]),
            NavigationPath(from_screen="subscriptions", to_screen="video_player", steps=[{"action": "click", "target": "video_thumbnail", "description": "Tap video"}]),
        ],
        known_workflows=[
            {"name": "search_video", "steps": [{"action": "open_app", "app": "youtube"}, {"action": "click", "target": "search_box"}, {"action": "type", "target": "search_box"}]},
            {"name": "play_video", "steps": [{"action": "open_app", "app": "youtube"}, {"action": "click", "target": "search_box"}, {"action": "type", "target": "search_box"}, {"action": "click", "target": "video_result"}]},
        ],
    ),
    "telegram": AppDefinition(
        package_name="org.telegram.messenger",
        display_name="Telegram",
        screens={
            "chat_list": ScreenDef(name="chat_list", buttons=[{"text": "Search", "description": "Search chats"}]),
            "chat": ScreenDef(name="chat", elements=[{"type": "input", "id": "message_input"}], buttons=[{"text": "Send", "description": "Send message"}]),
            "settings": ScreenDef(name="settings"),
            "contacts": ScreenDef(name="contacts"),
            "calls": ScreenDef(name="calls"),
        },
        navigation_paths=[
            NavigationPath(from_screen="chat_list", to_screen="chat", steps=[{"action": "click", "target": "chat_item", "description": "Tap chat"}]),
            NavigationPath(from_screen="chat_list", to_screen="settings", steps=[{"action": "click", "target": "menu", "description": "Open menu"}, {"action": "click", "target": "settings", "description": "Tap settings"}]),
            NavigationPath(from_screen="chat_list", to_screen="contacts", steps=[{"action": "click", "target": "contacts_tab", "description": "Tap contacts"}]),
        ],
        known_workflows=[
            {"name": "open_chat", "steps": [{"action": "open_app", "app": "telegram"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}]},
            {"name": "send_message", "steps": [{"action": "open_app", "app": "telegram"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}, {"action": "type", "target": "message_input"}, {"action": "click", "target": "Send"}]},
        ],
    ),
    "discord": AppDefinition(
        package_name="com.discord",
        display_name="Discord",
        screens={
            "channel_list": ScreenDef(name="channel_list", buttons=[{"text": "Search", "description": "Search"}]),
            "chat": ScreenDef(name="chat", elements=[{"type": "input", "id": "message_input"}], buttons=[{"text": "Send", "description": "Send message"}]),
            "settings": ScreenDef(name="settings"),
            "dm_list": ScreenDef(name="dm_list"),
        },
        navigation_paths=[
            NavigationPath(from_screen="channel_list", to_screen="chat", steps=[{"action": "click", "target": "channel_item", "description": "Tap channel"}]),
            NavigationPath(from_screen="dm_list", to_screen="chat", steps=[{"action": "click", "target": "dm_item", "description": "Tap DM"}]),
        ],
        known_workflows=[
            {"name": "send_message", "steps": [{"action": "open_app", "app": "discord"}, {"action": "click", "target": "channel_item"}, {"action": "type", "target": "message_input"}, {"action": "click", "target": "Send"}]},
        ],
    ),
    "messenger": AppDefinition(
        package_name="com.facebook.orca",
        display_name="Messenger",
        screens={
            "inbox": ScreenDef(name="inbox", buttons=[{"text": "Search", "description": "Search chats"}]),
            "chat": ScreenDef(name="chat", elements=[{"type": "input", "id": "message_input"}], buttons=[{"text": "Send", "description": "Send message"}]),
            "settings": ScreenDef(name="settings"),
            "stories": ScreenDef(name="stories"),
        },
        navigation_paths=[
            NavigationPath(from_screen="inbox", to_screen="chat", steps=[{"action": "click", "target": "chat_item", "description": "Tap chat"}]),
            NavigationPath(from_screen="inbox", to_screen="search", steps=[{"action": "click", "target": "search", "description": "Tap search"}]),
        ],
        known_workflows=[
            {"name": "send_message", "steps": [{"action": "open_app", "app": "messenger"}, {"action": "click", "target": "search"}, {"action": "type", "target": "search_input"}, {"action": "click", "target": "chat_result"}, {"action": "type", "target": "message_input"}, {"action": "click", "target": "Send"}]},
        ],
    ),
    "gmail": AppDefinition(
        package_name="com.google.android.gm",
        display_name="Gmail",
        screens={
            "inbox": ScreenDef(name="inbox"),
            "email_view": ScreenDef(name="email_view"),
            "compose": ScreenDef(name="compose", elements=[{"type": "input", "id": "to_field"}, {"type": "input", "id": "subject_field"}, {"type": "input", "id": "body_field"}]),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "settings": ScreenDef(name="settings"),
        },
        navigation_paths=[
            NavigationPath(from_screen="inbox", to_screen="email_view", steps=[{"action": "click", "target": "email_item", "description": "Tap email"}]),
            NavigationPath(from_screen="inbox", to_screen="compose", steps=[{"action": "click", "target": "compose", "description": "Tap compose"}]),
            NavigationPath(from_screen="inbox", to_screen="search", steps=[{"action": "click", "target": "search", "description": "Tap search"}]),
        ],
        known_workflows=[
            {"name": "send_email", "steps": [{"action": "open_app", "app": "gmail"}, {"action": "click", "target": "compose"}, {"action": "type", "target": "to_field"}, {"action": "type", "target": "subject_field"}, {"action": "type", "target": "body_field"}, {"action": "click", "target": "send"}]},
        ],
    ),
    "maps": AppDefinition(
        package_name="com.google.android.apps.maps",
        display_name="Maps",
        screens={
            "map_view": ScreenDef(name="map_view"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "directions": ScreenDef(name="directions"),
            "settings": ScreenDef(name="settings"),
            "explore": ScreenDef(name="explore"),
        },
        navigation_paths=[
            NavigationPath(from_screen="map_view", to_screen="search", steps=[{"action": "click", "target": "search_box", "description": "Tap search"}]),
            NavigationPath(from_screen="search", to_screen="directions", steps=[{"action": "click", "target": "directions", "description": "Tap directions"}]),
            NavigationPath(from_screen="map_view", to_screen="explore", steps=[{"action": "click", "target": "explore", "description": "Tap explore"}]),
        ],
        known_workflows=[
            {"name": "search_location", "steps": [{"action": "open_app", "app": "maps"}, {"action": "click", "target": "search_box"}, {"action": "type", "target": "search_box"}]},
            {"name": "get_directions", "steps": [{"action": "open_app", "app": "maps"}, {"action": "click", "target": "search_box"}, {"action": "type", "target": "search_box"}, {"action": "click", "target": "directions"}]},
        ],
    ),
    "twitter": AppDefinition(
        package_name="com.twitter.android",
        display_name="Twitter",
        screens={
            "timeline": ScreenDef(name="timeline"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "notifications": ScreenDef(name="notifications"),
            "messages": ScreenDef(name="messages"),
            "profile": ScreenDef(name="profile"),
            "compose": ScreenDef(name="compose", elements=[{"type": "input", "id": "tweet_input"}]),
        },
        navigation_paths=[
            NavigationPath(from_screen="timeline", to_screen="search", steps=[{"action": "click", "target": "search_icon", "description": "Tap search"}]),
            NavigationPath(from_screen="timeline", to_screen="notifications", steps=[{"action": "click", "target": "bell_icon", "description": "Tap notifications"}]),
            NavigationPath(from_screen="timeline", to_screen="messages", steps=[{"action": "click", "target": "dm_icon", "description": "Tap messages"}]),
            NavigationPath(from_screen="timeline", to_screen="compose", steps=[{"action": "click", "target": "compose", "description": "Tap compose"}]),
            NavigationPath(from_screen="timeline", to_screen="profile", steps=[{"action": "click", "target": "profile_icon", "description": "Tap profile"}]),
        ],
        known_workflows=[
            {"name": "send_tweet", "steps": [{"action": "open_app", "app": "twitter"}, {"action": "click", "target": "compose"}, {"action": "type", "target": "tweet_input"}, {"action": "click", "target": "tweet"}]},
            {"name": "search", "steps": [{"action": "open_app", "app": "twitter"}, {"action": "click", "target": "search_icon"}, {"action": "type", "target": "search_box"}]},
        ],
    ),
    "linkedin": AppDefinition(
        package_name="com.linkedin.android",
        display_name="LinkedIn",
        screens={
            "feed": ScreenDef(name="feed"),
            "search": ScreenDef(name="search", elements=[{"type": "input", "id": "search_box"}]),
            "messages": ScreenDef(name="messages"),
            "notifications": ScreenDef(name="notifications"),
            "profile": ScreenDef(name="profile"),
            "jobs": ScreenDef(name="jobs"),
        },
        navigation_paths=[
            NavigationPath(from_screen="feed", to_screen="search", steps=[{"action": "click", "target": "search_icon", "description": "Tap search"}]),
            NavigationPath(from_screen="feed", to_screen="messages", steps=[{"action": "click", "target": "messaging_icon", "description": "Tap messages"}]),
            NavigationPath(from_screen="feed", to_screen="notifications", steps=[{"action": "click", "target": "bell_icon", "description": "Tap notifications"}]),
            NavigationPath(from_screen="feed", to_screen="jobs", steps=[{"action": "click", "target": "jobs_tab", "description": "Tap jobs"}]),
        ],
        known_workflows=[
            {"name": "search_people", "steps": [{"action": "open_app", "app": "linkedin"}, {"action": "click", "target": "search_icon"}, {"action": "type", "target": "search_box"}]},
        ],
    ),
    "settings": AppDefinition(
        package_name="com.android.settings",
        display_name="Settings",
        screens={
            "main": ScreenDef(name="main"),
            "wifi": ScreenDef(name="wifi"),
            "bluetooth": ScreenDef(name="bluetooth"),
            "display": ScreenDef(name="display"),
            "sound": ScreenDef(name="sound"),
            "battery": ScreenDef(name="battery"),
            "apps": ScreenDef(name="apps"),
            "storage": ScreenDef(name="storage"),
        },
        navigation_paths=[
            NavigationPath(from_screen="main", to_screen="wifi", steps=[{"action": "click", "target": "Wi-Fi", "description": "Tap Wi-Fi"}]),
            NavigationPath(from_screen="main", to_screen="bluetooth", steps=[{"action": "click", "target": "Bluetooth", "description": "Tap Bluetooth"}]),
            NavigationPath(from_screen="main", to_screen="display", steps=[{"action": "click", "target": "Display", "description": "Tap Display"}]),
            NavigationPath(from_screen="main", to_screen="sound", steps=[{"action": "click", "target": "Sound", "description": "Tap Sound"}]),
            NavigationPath(from_screen="main", to_screen="battery", steps=[{"action": "click", "target": "Battery", "description": "Tap Battery"}]),
            NavigationPath(from_screen="main", to_screen="apps", steps=[{"action": "click", "target": "Apps", "description": "Tap Apps"}]),
            NavigationPath(from_screen="main", to_screen="storage", steps=[{"action": "click", "target": "Storage", "description": "Tap Storage"}]),
        ],
        known_workflows=[
            {"name": "open_wifi", "steps": [{"action": "open_app", "app": "settings"}, {"action": "click", "target": "Wi-Fi"}]},
            {"name": "check_battery", "steps": [{"action": "open_app", "app": "settings"}, {"action": "click", "target": "Battery"}]},
        ],
    ),
    "phone": AppDefinition(
        package_name="com.android.dialer",
        display_name="Phone",
        screens={
            "dialer": ScreenDef(name="dialer"),
            "recents": ScreenDef(name="recents"),
            "contacts": ScreenDef(name="contacts"),
            "call_active": ScreenDef(name="call_active"),
            "voicemail": ScreenDef(name="voicemail"),
        },
        navigation_paths=[
            NavigationPath(from_screen="dialer", to_screen="recents", steps=[{"action": "click", "target": "recents_tab", "description": "Tap recents"}]),
            NavigationPath(from_screen="dialer", to_screen="contacts", steps=[{"action": "click", "target": "contacts_tab", "description": "Tap contacts"}]),
            NavigationPath(from_screen="recents", to_screen="call_active", steps=[{"action": "click", "target": "recent_item", "description": "Tap recent call"}, {"action": "click", "target": "call_button", "description": "Tap call"}]),
        ],
        known_workflows=[
            {"name": "make_call", "steps": [{"action": "open_app", "app": "phone"}, {"action": "click", "target": "contacts_tab"}, {"action": "click", "target": "contact_item"}, {"action": "click", "target": "call_button"}]},
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
