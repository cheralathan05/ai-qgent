"""Browser device abstraction for APA-OS."""
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus

logger = logging.getLogger(__name__)


class BrowserDevice(Device):
    """Browser device interface for web-based control."""

    def __init__(self, device_id: str, browser: str = "chrome", **kwargs):
        super().__init__(device_id)
        self.browser = browser

    async def get_info(self) -> DeviceInfo:
        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED,
            is_locked=False,
            battery_level=None,
            foreground_app="browser",
            installed_apps={self.browser},
            capabilities={"browser"},
            model_name="Web Browser",
            os_version="web",
            additional={"browser": self.browser},
        )

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        url = self._resolve_url(app_name)
        if not url:
            return {"status": "error", "message": f"Unknown browser target: {app_name}"}

        try:
            subprocess.Popen(f"start {url}", shell=True)
            await asyncio.sleep(1)
            return {"status": "success", "url": url}
        except Exception as exc:
            logger.error(f"Error opening browser URL {url}: {exc}")
            return {"status": "error", "message": str(exc)}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "send_text not supported for BrowserDevice"}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        return {"status": "success", "app": app_name, "verification": "browser_opened"}

    def _resolve_url(self, target: str) -> Optional[str]:
        target_lower = target.lower()
        urls = {
            "instagram": "https://www.instagram.com",
            "whatsapp": "https://web.whatsapp.com",
            "gmail": "https://mail.google.com",
            "notion": "https://www.notion.so",
            "google": "https://www.google.com",
            "chrome": "https://www.google.com",
        }
        return urls.get(target_lower)
