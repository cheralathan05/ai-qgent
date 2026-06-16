"""Windows device implementation for APA-OS."""
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus

logger = logging.getLogger(__name__)


class WindowsDevice(Device):
    """Control Windows machine functionality."""

    def __init__(self, device_id: str, **kwargs):
        super().__init__(device_id)
        self.windows_user = kwargs.get("windows_user")

    async def get_info(self) -> DeviceInfo:
        """Return basic Windows device info."""
        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED,
            is_locked=False,
            battery_level=None,
            foreground_app=None,
            installed_apps=set(),
            capabilities={"browser", "file_system", "applications"},
            model_name="Windows Laptop",
            os_version="Windows",
            additional={"user": self.windows_user},
        )

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch a desktop application or URL."""
        app_command = self._resolve_app_command(app_name)

        if app_command is None:
            return {"status": "error", "message": f"Unknown windows app: {app_name}"}

        try:
            subprocess.Popen(app_command, shell=True)
            await asyncio.sleep(1)
            return {"status": "success", "app": app_name}
        except Exception as exc:
            logger.error(f"Error launching {app_name}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "send_text not supported for WindowsDevice"}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        return {
            "status": "success",
            "app": app_name,
            "verification": "not_implemented",
        }

    def _resolve_app_command(self, app_name: str):
        app_name_lower = app_name.lower()

        commands = {
            "chrome": "start chrome",
            "edge": "start msedge",
            "vs code": "start code",
            "vscode": "start code",
            "file explorer": "start explorer",
            "explorer": "start explorer",
            "notepad": "start notepad",
            "code": "start code",
            "instagram": "start chrome https://www.instagram.com",
            "gmail": "start chrome https://mail.google.com",
            "whatsapp": "start chrome https://web.whatsapp.com",
        }

        return commands.get(app_name_lower)
