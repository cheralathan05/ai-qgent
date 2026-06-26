"""ADB Service for Android device control."""

import asyncio
import logging
import os
import re
import shutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def find_adb_binary() -> str:
    """Locate the ADB binary on this system.

    Checks (in order):
      1. `ADB_PATH` environment variable
      2. `adb` / `adb.exe` in PATH
      3. ANDROID_HOME/platform-tools/adb.exe
      4. ANDROID_SDK_ROOT/platform-tools/adb.exe
      5. LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe
      6. C:/platform-tools/adb.exe
      7. C:/Android/platform-tools/adb.exe
    """
    # 1. Explicit env var
    env_path = os.environ.get("ADB_PATH", "").strip().strip("\"'")
    if env_path:
        resolved = shutil.which(env_path)
        if resolved:
            return resolved
        if os.path.isfile(env_path):
            return env_path

    # 2. PATH
    resolved = shutil.which("adb")
    if resolved:
        return resolved

    # 3-7. Common Windows SDK locations
    candidates = []
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(var, "")
        if root:
            candidates.append(os.path.join(root, "platform-tools", "adb.exe"))

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        candidates.append(os.path.join(local_appdata, "Android", "Sdk", "platform-tools", "adb.exe"))

    candidates.extend([
        r"C:\platform-tools\adb.exe",
        r"C:\Android\platform-tools\adb.exe",
    ])

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    # Final fallback – let subprocess fail with a clear error later
    logger.warning("ADB binary not found – will fall back to 'adb' (may fail if not in PATH)")
    return "adb"


class ADBCommandError(RuntimeError):
    pass


class ADBService:
    """Wraps adb commands for Android automation."""

    def __init__(self, adb_path: Optional[str] = None, default_timeout: int = 30):
        self.adb_path = adb_path or find_adb_binary()
        self.default_timeout = default_timeout
        self._resolver = None

    def _get_resolver(self):
        if self._resolver is None:
            from .app_resolver import get_app_resolver
            self._resolver = get_app_resolver()
        return self._resolver

    async def _ensure_resolver(self, device_id: str):
        resolver = self._get_resolver()
        await resolver.ensure_registry(device_id)
        return resolver

    async def _run(self, args: List[str], timeout: Optional[int] = None) -> str:
        if not shutil.which(self.adb_path):
            raise ADBCommandError(f"ADB binary not found at {self.adb_path}")

        process = await asyncio.create_subprocess_exec(
            self.adb_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout or self.default_timeout,
        )

        if process.returncode != 0:
            message = stderr.decode(errors="ignore").strip() or stdout.decode(errors="ignore").strip()
            raise ADBCommandError(f"ADB command failed: {message}")

        return stdout.decode(errors="ignore").strip()

    async def list_devices(self) -> List[Dict[str, Any]]:
        output = await self._run(["devices"], timeout=self.default_timeout)
        devices = []
        for line in output.splitlines():
            normalized = line.strip()
            if not normalized or normalized.startswith("List of devices"):
                continue

            parts = normalized.split()
            if len(parts) < 2:
                continue

            serial, state = parts[0], parts[1]
            if state == "device":
                devices.append({"serial": serial, "state": state, "raw": normalized})
        return devices

    async def discover_devices(self) -> List[Dict[str, Any]]:
        devices = []
        for device in await self.list_devices():
            serial = device.get("serial")
            if not serial:
                continue

            devices.append({
                "device_id": serial,
                "type": "android",
                "status": "connected",
                "model_name": await self.get_model_name(serial),
                "manufacturer": await self.get_manufacturer(serial),
                "android_version": await self.get_android_version(serial),
                "battery_level": await self.get_battery_level(serial),
                "foreground_app": await self.get_foreground_app(serial),
                "screen_state": await self.get_screen_state(serial),
                "lock_state": await self.get_lock_state(serial),
                "connected": True,
                "capabilities": ["applications", "screenshots", "input", "notifications", "files"],
            })

        return devices

    def resolve_package_name(self, app_name: str) -> str:
        """Resolve an app name to a package name using known mappings."""
        if not app_name:
            logger.warning("resolve_package_name called with empty/None app_name")
            return ""
        from understanding.entity_extractor import KNOWN_APPS
        search = app_name.strip().lower()
        if search in KNOWN_APPS:
            return KNOWN_APPS[search]
        return search

    async def resolve_package_dynamic(self, device_id: str, app_name: str) -> Optional[str]:
        """Resolve app name to package using the dynamic app resolver, with KNOWN_APPS fallback."""
        # First try the KNOWN_APPS mapping (fast, no ADB needed)
        resolved = self.resolve_package_name(app_name)
        if resolved != app_name.strip().lower():
            return resolved
        # Then try the dynamic resolver
        try:
            resolver = await self._ensure_resolver(device_id)
            resolved = resolver.resolve(app_name)
            if resolved:
                return resolved
        except Exception:
            pass
        logger.warning(f"Dynamic resolution failed for '{app_name}', using raw name")
        return app_name.strip().lower()

    async def start_activity(self, device_id: str, package_name: str, activity: str) -> str:
        return await self.shell(device_id, f"am start -n {package_name}/{activity}")

    async def monkey_launch(self, device_id: str, package_name: str) -> str:
        return await self.shell(device_id, f"monkey -p {package_name} 1")

    async def open_app(self, device_id: str, app_name: str) -> str:
        pkg = self.resolve_package_name(app_name)
        return await self.launch_package(device_id, pkg)

    async def launch_package(self, device_id: str, package: str) -> str:
        """Open an app by package name, trying monkey then am start as fallback."""
        try:
            return await self.monkey_launch(device_id, package)
        except Exception:
            return await self.shell(
                device_id,
                f"am start -p {package} -a android.intent.action.MAIN -c android.intent.category.LAUNCHER",
            )

    async def open_url(self, device_id: str, url: str) -> str:
        """Open a URL in the default browser."""
        return await self.shell(
            device_id,
            f'am start -a android.intent.action.VIEW -d "{url}"',
        )

    async def dial_number(self, device_id: str, number: str) -> str:
        """Open dialer with a number pre-filled."""
        return await self.shell(
            device_id,
            f'am start -a android.intent.action.DIAL -d "tel:{number}"',
        )

    async def press_key(self, device_id: str, keycode: int) -> str:
        """Send a keyevent to the device."""
        return await self.shell(device_id, f"input keyevent {keycode}")

    async def close_app(self, device_id: str, app_name: str) -> str:
        pkg = await self.resolve_package_dynamic(device_id, app_name)
        return await self.shell(device_id, f"am force-stop {pkg}")

    async def input_tap(self, device_id: str, x: int, y: int) -> str:
        return await self.shell(device_id, f"input tap {x} {y}")

    async def input_long_press(self, device_id: str, x: int, y: int, duration_ms: int = 1000) -> str:
        return await self.shell(device_id, f"input swipe {x} {y} {x} {y} {duration_ms}")

    async def input_text(self, device_id: str, text: str) -> str:
        # Use ADB input text with proper escaping
        # Replace spaces with %s for ADB
        escaped = text.replace(" ", "%s")
        # Escape special shell characters
        escaped = escaped.replace("&", "\\&")
        escaped = escaped.replace("<", "\\<")
        escaped = escaped.replace(">", "\\>")
        escaped = escaped.replace("(", "\\(")
        escaped = escaped.replace(")", "\\)")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace(";", "\\;")
        escaped = escaped.replace("|", "\\|")
        escaped = escaped.replace("$", "\\$")
        escaped = escaped.replace("!", "\\!")
        return await self.shell(device_id, f"input text '{escaped}'")

    async def input_keyevent(self, device_id: str, keycode: int) -> str:
        return await self.shell(device_id, f"input keyevent {keycode}")

    async def screencap(self, device_id: str, output_path: str) -> bytes:
        data = await self.shell(device_id, f"screencap -p")
        return data.encode()

    async def dumpsys_window(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys window windows")

    async def dumpsys_battery(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys battery")

    async def dumpsys_display(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys display")

    async def dumpsys_power(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys power")

    async def shell(self, device_id: str, command: str, timeout: Optional[int] = None) -> str:
        return await self._run(
            ["-s", device_id, "shell", command],
            timeout=timeout or self.default_timeout,
        )

    async def get_model_name(self, device_id: str) -> Optional[str]:
        try:
            value = await self.shell(device_id, "getprop ro.product.model")
            return value.strip() or None
        except Exception:
            return None

    async def get_manufacturer(self, device_id: str) -> Optional[str]:
        try:
            value = await self.shell(device_id, "getprop ro.product.manufacturer")
            return value.strip() or None
        except Exception:
            return None

    async def get_android_version(self, device_id: str) -> Optional[str]:
        try:
            value = await self.shell(device_id, "getprop ro.build.version.release")
            return value.strip() or None
        except Exception:
            return None

    async def get_screen_state(self, device_id: str) -> Optional[str]:
        try:
            output = await self.dumpsys_display(device_id)
            lowered = output.lower()
            if any(token in lowered for token in ("state=on", "mdisplaystate=2", "screen state: on")):
                return "on"
            if any(token in lowered for token in ("state=off", "mdisplaystate=1", "screen state: off")):
                return "off"
            power_output = await self.dumpsys_power(device_id)
            power_lowered = power_output.lower()
            if "display power: state=on" in power_lowered or "mholdingdisplaypower=true" in power_lowered:
                return "on"
            if "display power: state=off" in power_lowered:
                return "off"
            return "unknown"
        except Exception:
            return None

    async def get_lock_state(self, device_id: str) -> Optional[bool]:
        try:
            output = await self.shell(device_id, "dumpsys window policy")
            lowered = output.lower()
            if any(token in lowered for token in ("mshowinglockscreen=true", "isstatusbarkeyguard=true", "keyguard showing=true")):
                return True
            if any(token in lowered for token in ("mshowinglockscreen=false", "isstatusbarkeyguard=false")):
                return False
            return False
        except Exception:
            return None

    async def get_foreground_app(self, device_id: str) -> Optional[str]:
        try:
            output = await self.dumpsys_window(device_id)
            match = re.search(r"mCurrentFocus.+?\s([\w\.]+)/", output)
            if match:
                return match.group(1)

            match = re.search(r"mFocusedApp=AppWindowToken\{.*? ([\w\.]+)/", output)
            if match:
                return match.group(1)

            # Fallback: check ResumedActivity (Android 14+)
            act_out = await self.shell(
                device_id,
                "dumpsys activity activities 2>/dev/null | grep ResumedActivity",
            )
            for line in act_out.splitlines():
                m = re.search(r"([\w\.]+)/", line)
                if m:
                    return m.group(1)

            return None
        except Exception:
            return None

    async def get_battery_level(self, device_id: str) -> Optional[int]:
        try:
            output = await self.dumpsys_battery(device_id)
            match = re.search(r"level:\s*(\d+)", output, re.IGNORECASE)
            return int(match.group(1)) if match else None
        except Exception:
            return None

    async def verify_foreground_app(self, device_id: str, app_name: str) -> bool:
        pkg = await self.resolve_package_dynamic(device_id, app_name)
        foreground = await self.get_foreground_app(device_id)
        return foreground == pkg

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        devices = await self.list_devices()
        connected = any(device.get("serial") == device_id for device in devices)
        model_name = await self.get_model_name(device_id) if connected else None
        android_version = await self.get_android_version(device_id) if connected else None
        screen_state = await self.get_screen_state(device_id) if connected else None
        lock_state = await self.get_lock_state(device_id) if connected else None
        return {
            "device_id": device_id,
            "connected": connected,
            "status": "online" if connected else "offline",
            "type": "android",
            "model_name": model_name,
            "manufacturer": await self.get_manufacturer(device_id) if connected else None,
            "battery_level": await self.get_battery_level(device_id) if connected else None,
            "foreground_app": await self.get_foreground_app(device_id) if connected else None,
            "is_locked": bool(lock_state) if lock_state is not None else False,
            "android_version": android_version,
            "screen_state": screen_state,
            "lock_state": lock_state,
            "capabilities": ["applications", "screenshots", "input", "notifications", "files"],
            "adb_path": self.adb_path,
        }

    async def take_screenshot(self, device_id: str) -> bytes:
        if not shutil.which(self.adb_path):
            raise ADBCommandError(f"ADB binary not found at {self.adb_path}")

        process = await asyncio.create_subprocess_exec(
            self.adb_path,
            "-s",
            device_id,
            "exec-out",
            "screencap",
            "-p",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=self.default_timeout,
        )

        if process.returncode != 0:
            message = stderr.decode(errors="ignore").strip() or stdout.decode(errors="ignore").strip()
            raise ADBCommandError(f"ADB screenshot failed: {message}")

        return stdout


adb_service = None


def get_adb_service(adb_path: Optional[str] = None, default_timeout: int = 30) -> ADBService:
    global adb_service
    if adb_service is None:
        adb_service = ADBService(adb_path, default_timeout)
    return adb_service
