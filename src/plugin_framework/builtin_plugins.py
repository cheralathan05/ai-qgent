"""Built-in plugins for supported apps: Instagram, WhatsApp, Chrome, YouTube, Settings."""

import logging
from typing import Dict, Any, Optional, List

from plugin_framework.plugin_base import PluginBase, PluginMetadata, PluginResult
from app_knowledge import get_app_knowledge

logger = logging.getLogger(__name__)


class InstagramPlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Instagram",
            version="1.0.0",
            description="Control Instagram: feed, DMs, profile, reels, settings",
            package_name="com.instagram.android",
            supported_actions=["open_dm", "send_message", "view_profile", "view_feed", "view_reels", "open_settings"],
            requires_approval=["send_message"],
        )

    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        logger.info(f"Instagram plugin executing: {action}")
        app_knowledge = get_app_knowledge()
        workflows = {
            "open_dm": [{"action": "click", "target": "DM"}],
            "send_message": [{"action": "type", "target": "message_input", "value": params.get("message", "")}, {"action": "send"}],
        }
        if action in workflows:
            return PluginResult(success=True, data={"action": action, "steps": workflows[action]})
        return PluginResult(success=False, error=f"Unknown action: {action}")


class WhatsAppPlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="WhatsApp",
            version="1.0.0",
            description="Control WhatsApp: chats, messages, search",
            package_name="com.whatsapp",
            supported_actions=["open_chat", "send_message", "search_chat"],
            requires_approval=["send_message"],
        )

    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        logger.info(f"WhatsApp plugin executing: {action}")
        workflows = {
            "open_chat": [
                {"action": "click", "target": "search"},
                {"action": "type", "target": "search_input", "value": params.get("recipient", "")},
                {"action": "click", "target": "chat_result"},
            ],
            "send_message": [
                {"action": "type", "target": "message_input", "value": params.get("message", "")},
                {"action": "click", "target": "Send"},
            ],
        }
        if action in workflows:
            return PluginResult(success=True, data={"action": action, "steps": workflows[action]})
        return PluginResult(success=False, error=f"Unknown action: {action}")


class ChromePlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Chrome",
            version="1.0.0",
            description="Control Chrome browser: search, navigate",
            package_name="com.android.chrome",
            supported_actions=["search", "navigate", "open_tab"],
            requires_approval=[],
        )

    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        logger.info(f"Chrome plugin executing: {action}")
        if action == "search":
            return PluginResult(success=True, data={"action": "search", "query": params.get("query", "")})
        if action == "navigate":
            return PluginResult(success=True, data={"action": "navigate", "url": params.get("url", "")})
        return PluginResult(success=False, error=f"Unknown action: {action}")


class YouTubePlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="YouTube",
            version="1.0.0",
            description="Control YouTube: search, play, navigate",
            package_name="com.google.android.youtube",
            supported_actions=["search", "play_video", "open_subscriptions"],
            requires_approval=[],
        )

    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        logger.info(f"YouTube plugin executing: {action}")
        if action == "search":
            return PluginResult(success=True, data={"action": "search", "query": params.get("query", "")})
        if action == "play_video":
            return PluginResult(success=True, data={"action": "play_video", "video_id": params.get("video_id", "")})
        return PluginResult(success=False, error=f"Unknown action: {action}")


class SettingsPlugin(PluginBase):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Settings",
            version="1.0.0",
            description="Access device settings",
            package_name="com.android.settings",
            supported_actions=["open_setting", "toggle_wifi", "toggle_bluetooth"],
            requires_approval=["toggle_wifi", "toggle_bluetooth"],
        )

    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        logger.info(f"Settings plugin executing: {action}")
        return PluginResult(success=True, data={"action": action})


def register_builtin_plugins() -> None:
    from plugin_framework.plugin_registry import get_plugin_registry
    registry = get_plugin_registry()
    for plugin in [InstagramPlugin(), WhatsAppPlugin(), ChromePlugin(), YouTubePlugin(), SettingsPlugin()]:
        registry.register(plugin)
    logger.info("All built-in plugins registered")
