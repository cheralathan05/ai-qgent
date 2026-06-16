"""Calendar device abstraction for APA-OS."""
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus


class CalendarDevice(Device):
    """Abstract representation of calendar service."""

    def __init__(self, device_id: str, provider: str = "google_calendar", **kwargs):
        super().__init__(device_id)
        self.provider = provider

    async def get_info(self) -> DeviceInfo:
        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED,
            is_locked=False,
            battery_level=None,
            foreground_app=None,
            installed_apps=set(),
            capabilities={"calendar"},
            device_type="calendar",
            model_name=f"{self.provider} Calendar",
            os_version="cloud",
            additional={"provider": self.provider},
        )

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        return {"status": "pending", "message": "calendar launch not implemented"}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "send_text not supported for CalendarDevice"}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        return {"status": "success", "verification": "calendar_verification_placeholder"}
