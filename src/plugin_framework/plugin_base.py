"""Base class and types for all app plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum


class PluginResult:
    def __init__(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error


@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str
    package_name: str
    supported_actions: List[str]
    requires_approval: List[str]


class PluginBase(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any], device_id: Optional[str] = None) -> PluginResult:
        pass

    async def get_known_screens(self) -> Dict[str, Any]:
        return {}

    async def get_workflows(self) -> List[Dict[str, Any]]:
        return []
