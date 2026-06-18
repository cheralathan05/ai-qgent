"""Layer 15: Plugin Framework - extensible app integrations."""

from .plugin_base import PluginBase, PluginMetadata, PluginResult
from .plugin_registry import PluginRegistry, get_plugin_registry
from .builtin_plugins import (
    InstagramPlugin, WhatsAppPlugin, ChromePlugin,
    YouTubePlugin, SettingsPlugin,
)

__all__ = [
    "PluginBase", "PluginMetadata", "PluginResult",
    "PluginRegistry", "get_plugin_registry",
    "InstagramPlugin", "WhatsAppPlugin", "ChromePlugin",
    "YouTubePlugin", "SettingsPlugin",
]
