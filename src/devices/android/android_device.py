"""Android device abstraction for APA-OS."""

import asyncio
import logging
from typing import Dict, Any, Optional, Set

from ..device import Device, DeviceInfo, DeviceStatus

logger = logging.getLogger(__name__)


class AndroidDevice(Device):
    """Android device abstraction for ADB-driven control.

    No hardcoded app mappings. All resolution is dynamic via AppResolver.
    """

    def __init__(self, device_id: str, adb_client=None, **kwargs):
        super().__init__(device_id)
        if adb_client is not None:
            self.adb = adb_client
        else:
            from services.adb_service import get_adb_service
            self.adb = get_adb_service()

    async def _resolve_package_name(self, app_name: str) -> str:
        if app_name is None:
            logger.warning("_resolve_package_name called with None app_name")
            return ""
        from services.app_resolver import get_app_resolver
        resolver = get_app_resolver()
        await resolver.ensure_registry(self.device_id)
        resolved = resolver.resolve(app_name)
        return resolved or app_name.strip().lower()

    async def get_info(self) -> DeviceInfo:
        if not self.adb:
            return DeviceInfo(
                device_id=self.device_id,
                status=DeviceStatus.DISCONNECTED,
                is_locked=False,
                battery_level=None,
                foreground_app=None,
                installed_apps=set(),
                capabilities={"applications", "screenshots", "input", "notifications", "files"},
                device_type="android",
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
                capabilities={"applications", "screenshots", "input", "notifications", "files"},
                device_type="android",
                model_name="Android Device",
                os_version="Android",
                additional={"adb_available": True},
            )

        installed_apps = await self._get_installed_apps()
        foreground_app = await self.get_foreground_app()
        is_locked = await self._is_locked()
        battery_level = await self.get_battery()
        android_version = await self._get_android_version()
        model_name = await self._get_model_name()
        screen_state = await self._get_screen_state()

        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED,
            is_locked=is_locked,
            battery_level=battery_level,
            foreground_app=foreground_app,
            installed_apps=installed_apps,
            capabilities={"applications", "screenshots", "input", "notifications", "files"},
            device_type="android",
            model_name=model_name,
            os_version=f"Android {android_version}".strip(),
            android_version=android_version,
            screen_state=screen_state,
            lock_state=is_locked,
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
        return await self.get_foreground_app()

    async def _is_locked(self) -> bool:
        try:
            result = await self.adb.shell(self.device_id, "dumpsys window policy")
            lowered = result.lower()
            return any(
                token in lowered
                for token in (
                    "mshowinglockscreen=true",
                    "isstatusbarkeyguard=true",
                    "lockscreen",
                    "keyguard showing=true",
                )
            )
        except Exception:
            return False

    async def _get_battery_level(self) -> Optional[int]:
        return await self.get_battery()

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

    async def _get_screen_state(self) -> str:
        try:
            result = await self.adb.shell(self.device_id, "dumpsys display")
            lowered = result.lower()
            if "state=on" in lowered or "mdisplaystate=2" in lowered or "display power: state=on" in lowered:
                return "on"
            if "state=off" in lowered or "mdisplaystate=1" in lowered:
                return "off"
            return "unknown"
        except Exception:
            return "unknown"

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        return await self.open_app(app_name)

    async def open_app(self, app_name: str) -> Dict[str, Any]:
        if not app_name:
            return {"status": "error", "message": "No app name provided"}
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        from services.app_launch import get_app_launch_service
        launch_service = get_app_launch_service(adb_service=self.adb)
        result = await launch_service.launch_app(self.device_id, app_name)
        return result.to_dict()

    async def close_app(self, app_name: str) -> Dict[str, Any]:
        if not app_name:
            return {"status": "error", "message": "No app name provided"}
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        try:
            package_name = await self._resolve_package_name(app_name)
            await self.adb.close_app(self.device_id, package_name)
            return {"status": "success", "app": package_name}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def get_battery(self) -> Optional[int]:
        if not self.adb:
            return None
        return await self.adb.get_battery_level(self.device_id)

    async def get_foreground_app(self) -> Optional[str]:
        if not self.adb:
            return None
        return await self.adb.get_foreground_app(self.device_id)

    async def verify_foreground_app(self, app_name: str) -> Dict[str, Any]:
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        try:
            package_name = await self._resolve_package_name(app_name)
            current_app = await self.get_foreground_app()
            return {
                "status": "success" if current_app == package_name else "failure",
                "expected": package_name,
                "current": current_app,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def get_device_status(self) -> Dict[str, Any]:
        if not self.adb:
            return {
                "device_id": self.device_id,
                "connected": False,
                "status": "disconnected",
                "type": "android",
                "model_name": None,
                "battery_level": None,
                "foreground_app": None,
                "is_locked": False,
                "android_version": None,
                "screen_state": None,
                "lock_state": None,
                "capabilities": ["applications", "screenshots", "input", "notifications", "files"],
            }

        devices = await self.adb.list_devices()
        connected = any(device.get("serial") == self.device_id for device in devices)
        model_name = await self._get_model_name() if connected else None
        android_version = await self._get_android_version() if connected else None
        battery_level = await self.get_battery() if connected else None
        foreground_app = await self.get_foreground_app() if connected else None
        is_locked = await self._is_locked() if connected else False
        screen_state = await self._get_screen_state() if connected else None
        return {
            "device_id": self.device_id,
            "connected": connected,
            "status": "connected" if connected else "disconnected",
            "type": "android",
            "model_name": model_name,
            "battery_level": battery_level,
            "foreground_app": foreground_app,
            "is_locked": is_locked,
            "android_version": android_version,
            "screen_state": screen_state,
            "lock_state": is_locked,
            "capabilities": ["applications", "screenshots", "input", "notifications", "files"],
        }

    async def take_screenshot(self) -> Dict[str, Any]:
        if not self.adb:
            return {"status": "error", "message": "ADB client unavailable"}

        try:
            screenshot = await self.adb.take_screenshot(self.device_id)
            return {"status": "success", "device_id": self.device_id, "screenshot": screenshot}
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

        package_name = await self._resolve_package_name(app_name)
        for _ in range(timeout_seconds):
            current = await self.get_foreground_app()
            if current == package_name:
                return {"status": "success", "app": package_name, "verification": "opened"}
            await asyncio.sleep(1)

        return {
            "status": "failure",
            "app": package_name,
            "verification": "timeout",
            "foreground_app": await self.get_foreground_app(),
        }
