"""Common device abstractions for APA-OS."""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, Set


class DeviceStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    OBSERVING = "observing"
    CONTROLLING = "controlling"
    EXECUTING = "executing"


@dataclass
class DeviceInfo:
    device_id: str
    status: DeviceStatus
    is_locked: bool
    battery_level: Optional[int]
    foreground_app: Optional[str]
    installed_apps: Set[str]
    capabilities: Set[str]
    device_type: str = "generic"
    model_name: Optional[str] = None
    os_version: Optional[str] = None
    android_version: Optional[str] = None
    screen_state: Optional[str] = None
    lock_state: Optional[bool] = None
    additional: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "connected": self.status == DeviceStatus.CONNECTED,
            "status": self.status.value,
            "type": self.device_type,
            "is_locked": self.is_locked,
            "battery_level": self.battery_level,
            "foreground_app": self.foreground_app,
            "installed_apps": sorted(self.installed_apps),
            "capabilities": sorted(self.capabilities),
            "model_name": self.model_name,
            "os_version": self.os_version,
            "android_version": self.android_version,
            "screen_state": self.screen_state,
            "lock_state": self.lock_state,
            "additional": self.additional or {},
        }


class Device:
    """Base device interface."""

    def __init__(self, device_id: str):
        self.device_id = device_id

    async def get_info(self) -> DeviceInfo:
        raise NotImplementedError()

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        raise NotImplementedError()

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError()

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        raise NotImplementedError()
