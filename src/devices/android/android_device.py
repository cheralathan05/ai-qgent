"""Android device abstraction for APA-OS."""

import asyncio
import logging
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus

logger = logging.getLogger(__name__)


class AndroidDevice(Device):
    """Android device abstraction for ADB-driven control."""

    APP_PACKAGE_MAP = {
        "chrome": "com.android.chrome",
        "instagram": "com.instagram.android",
        "whatsapp": "com.whatsapp",
        "youtube": "com.google.android.youtube",
        "maps": "com.google.android.apps.maps",
        "gmail": "com.google.android.gm",
    }

    APP_MAIN_ACTIVITY = {
        "com.android.chrome": "com.google.android.apps.chrome.Main",
        "com.instagram.android": "com.instagram.mainactivity.MainActivity",
        "com.whatsapp": "com.whatsapp.Main",
        "com.google.android.youtube": "com.google.android.youtube.HomeActivity",
        "com.google.android.apps.maps": "com.google.android.maps.MapsActivity",
        "com.google.android.gm": "com.google.android.gm.ConversationListActivityGmail",
    }

    def __init__(self, device_id: str, adb_client=None, **kwargs):
        super().__init__(device_id)
        self.adb = adb_client

    async def get_info(self) -> DeviceInfo:
        if not self.adb:
            return DeviceInfo(
                device_id=self.device_id,
                status=DeviceStatus.DISCONNECTED,
                is_locked=False,
                battery_level=None,
                foreground_app=None,
                installed_apps=set(),
                capabilities={"android"},
                model_name="Android Device",
                os_version="Android",
                additional={"adb_available": False},
            )

        if not await self._is_connected():
            return DeviceInfo(
                device_id=self.device_id,
                status=DeviceStatus.DISCONNECTED,
                is_locked=False,
                battery_level=None,
                foreground_app=None,
                installed_apps=set(),
                capabilities={"android"},
                model_name="Android Device",
                os_version="Android",
                additional={"adb_available": True},
            )

        installed_apps = await self._get_installed_apps()
        foreground_app = await self._get_foreground_app()
        is_locked = await self._is_locked()
        battery_level = await self._get_battery_level()
        android_version = await self._get_android_version()
        model_name = await self._get_model_name()

        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED,
            is_locked=is_locked,
            battery_level=battery_level,
            foreground_app=foreground_app,
            installed_apps=installed_apps,
            capabilities={"android", "touch"},
            model_name=model_name,
            os_version=android_version,
            additional={"adb_available": True},
        )

    async def _is_connected(self) -> bool:
        try:
            devices = await self.adb.list_devices()
            return self.device_id in [device["serial"] for device in devices]
        except Exception:
            return False

    async def _get_installed_apps(self) -> Set[str]:
        try:
            result = await self.adb.shell(self.device_id, "pm list packages")
            return {line.replace("package:", "").strip() for line in result.splitlines() if line.strip()}
        except Exception:
            return set()

    async def _get_foreground_app(self) -> Optional[str]:
        try:
            result = await self.adb.shell(
                self.device_id,
                "dumpsys window windows | grep 'mCurrentFocus' | head -1"
            )
            if "/" in result:
                return result.split("/")[0].split()[-1]
            return None
        except Exception:
            return None

    async def _is_locked(self) -> bool:
        try:
            result = await self.adb.shell(self.device_id, "dumpsys window policy | grep isStatusBarKeyguard")
            return "true" in result.lower()
        except Exception:
            return False

    async def _get_battery_level(self) -> Optional[int]:
        try:
            result = await self.adb.shell(self.device_id, "dumpsys battery | grep level")
            return int(result.split(":")[-1].strip())
        except Exception:
            return None

    async def _get_android_version(self) -> str:
        try:
            return (await self.adb.shell(self.device_id, "getprop ro.build.version.release")).strip()
        except Exception:
            return ""

    async def _get_model_name(self) -> str:
        try:
            return (await self.adb.shell(self.device_id, "getprop ro.product.model")).strip()
        except Exception:
            return ""

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        package_name = self.APP_PACKAGE_MAP.get(app_name.lower(), app_name)
        activity = self.APP_MAIN_ACTIVITY.get(package_name)

        try:
            if activity:
                await self.adb.start_activity(self.device_id, package_name, activity)
            else:
                await self.adb.monkey_launch(self.device_id, package_name)

            await asyncio.sleep(2)
            return {"status": "success", "app": package_name}

        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        try:
            await self.adb.input_text(self.device_id, text)
            return {"status": "success", "text": text}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        package_name = self.APP_PACKAGE_MAP.get(app_name.lower(), app_name)
        for _ in range(timeout_seconds):
            current = await self._get_foreground_app()
            if current == package_name:
                return {"status": "success", "app": package_name, "verification": "opened"}
            await asyncio.sleep(1)

        return {
            "status": "failure",
            "app": package_name,
            "verification": "timeout",
            "foreground_app": await self._get_foreground_app(),
        }
