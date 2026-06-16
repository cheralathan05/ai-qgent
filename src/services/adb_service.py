"""ADB Service for Android device control."""

import asyncio
import json
import logging
import shutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ADBCommandError(RuntimeError):
    pass


class ADBService:
    """Wraps adb commands for Android automation."""

    def __init__(self, adb_path: str = "adb", default_timeout: int = 30):
        self.adb_path = adb_path
        self.default_timeout = default_timeout

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
        output = await self._run(["devices", "-l"], timeout=self.default_timeout)
        devices = []
        for line in output.splitlines():
            if "device" in line and not line.strip().startswith("List of devices"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append({"serial": parts[0], "properties": parts[2:]})
        return devices

    async def shell(self, device_id: str, command: str) -> str:
        return await self._run(["-s", device_id, "shell", command], timeout=self.default_timeout)

    async def start_activity(self, device_id: str, package_name: str, activity: str) -> str:
        return await self.shell(device_id, f"am start -n {package_name}/{activity}")

    async def monkey_launch(self, device_id: str, package_name: str) -> str:
        return await self.shell(device_id, f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")

    async def input_tap(self, device_id: str, x: int, y: int) -> str:
        return await self.shell(device_id, f"input tap {x} {y}")

    async def input_text(self, device_id: str, text: str) -> str:
        escaped = text.replace(" ", "%s")
        return await self.shell(device_id, f"input text {escaped}")

    async def screencap(self, device_id: str, output_path: str) -> bytes:
        data = await self.shell(device_id, f"screencap -p")
        return data.encode()

    async def dumpsys_window(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys window windows")

    async def dumpsys_battery(self, device_id: str) -> str:
        return await self.shell(device_id, "dumpsys battery")


adb_service = None


def get_adb_service(adb_path: str = "adb", default_timeout: int = 30) -> ADBService:
    global adb_service
    if adb_service is None:
        adb_service = ADBService(adb_path, default_timeout)
    return adb_service
