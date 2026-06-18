"""Plugin registry that manages all app plugins."""

import logging
from typing import Dict, Any, Optional, List, Type

from plugin_framework.plugin_base import PluginBase, PluginMetadata, PluginResult

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for all app plugins."""

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}

    def register(self, plugin: PluginBase) -> None:
        meta = plugin.metadata
        self._plugins[meta.name.lower()] = plugin
        logger.info(f"Plugin registered: {meta.name} v{meta.version}")

    def unregister(self, name: str) -> None:
        self._plugins.pop(name.lower(), None)

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name.lower())

    def get_plugin_for_app(self, app_name: str) -> Optional[PluginBase]:
        for plugin in self._plugins.values():
            if app_name.lower() in plugin.metadata.name.lower() or app_name.lower() in plugin.metadata.package_name.lower():
                return plugin
            if hasattr(plugin.metadata, "aliases"):
                if app_name.lower() in [a.lower() for a in plugin.metadata.aliases]:
                    return plugin
        return None

    def list_plugins(self) -> List[PluginMetadata]:
        return [p.metadata for p in self._plugins.values()]

    async def execute_action(self, app_name: str, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        plugin = self.get_plugin_for_app(app_name)
        if not plugin:
            return PluginResult(success=False, error=f"No plugin found for {app_name}")
        return await plugin.execute(action, params, device_id)


_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry
