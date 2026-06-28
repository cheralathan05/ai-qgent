"""
APA-OS USB Discovery Service
Real ADB-based USB device discovery with comprehensive device info extraction
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class USBDeviceInfo:
    serial: str = ""
    manufacturer: str = ""
    brand: str = ""
    model: str = ""
    android_version: str = ""
    sdk_version: int = 0
    build_number: str = ""
    battery_percentage: int = 0
    charging: bool = False
    screen_width: int = 0
    screen_height: int = 0
    cpu_abi: str = ""
    ram_total_kb: int = 0
    storage_total_bytes: int = 0
    foreground_app: str = ""
    screen_on: bool = False
    lock_state: str = ""
    usb_debugging: bool = False
    developer_options: bool = False
    accessibility_service: bool = False
    device_name: str = ""
    adb_authorized: bool = False
    connection_quality: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serial": self.serial,
            "manufacturer": self.manufacturer,
            "brand": self.brand,
            "model": self.model,
            "android_version": self.android_version,
            "sdk_version": self.sdk_version,
            "build_number": self.build_number,
            "battery_percentage": self.battery_percentage,
            "charging": self.charging,
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "cpu_abi": self.cpu_abi,
            "ram_total_kb": self.ram_total_kb,
            "storage_total_bytes": self.storage_total_bytes,
            "foreground_app": self.foreground_app,
            "screen_on": self.screen_on,
            "lock_state": self.lock_state,
            "usb_debugging": self.usb_debugging,
            "developer_options": self.developer_options,
            "accessibility_service": self.accessibility_service,
            "device_name": self.device_name,
            "adb_authorized": self.adb_authorized,
            "connection_quality": self.connection_quality,
        }


class USBDiscoveryEngine:
    def __init__(self, adb_service=None):
        self._adb = adb_service

    def _get_adb(self):
        if not self._adb:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb = get_adb_service(find_adb_binary())
        return self._adb

    async def discover(self) -> List[USBDeviceInfo]:
        """Discover all USB-connected Android devices with full info"""
        adb = self._get_adb()
        results = []
        try:
            devices = await adb.list_devices()
            for dev in devices:
                serial = dev.get("serial", "")
                state = dev.get("state", "unknown")
                if state != "device":
                    continue
                info = await self._extract_full_info(serial)
                info.adb_authorized = True
                results.append(info)
        except Exception as e:
            logger.error(f"USB discovery failed: {e}")
        return results

    async def _extract_full_info(self, serial: str) -> USBDeviceInfo:
        """Extract every piece of device information via real ADB commands"""
        adb = self._get_adb()
        info = USBDeviceInfo(serial=serial)

        commands = {
            "manufacturer": "getprop ro.product.manufacturer",
            "brand": "getprop ro.product.brand",
            "model": "getprop ro.product.model",
            "android_version": "getprop ro.build.version.release",
            "sdk_version": "getprop ro.build.version.sdk",
            "build_number": "getprop ro.build.display.id",
            "cpu_abi": "getprop ro.product.cpu.abi",
            "device_name": "getprop ro.product.name",
            "debugging": "settings get global adb_enabled",
            "developer_options": "settings get global development_settings_enabled",
        }

        results = {}
        for key, cmd in commands.items():
            try:
                raw = await adb.shell(serial, cmd)
                results[key] = (raw or "").strip()
            except Exception:
                results[key] = ""

        info.manufacturer = results.get("manufacturer", "")
        info.brand = results.get("brand", "")
        info.model = results.get("model", "")
        info.android_version = results.get("android_version", "")
        try:
            info.sdk_version = int(results.get("sdk_version", "0"))
        except ValueError:
            info.sdk_version = 0
        info.build_number = results.get("build_number", "")
        info.cpu_abi = results.get("cpu_abi", "")
        info.device_name = results.get("device_name", "") or info.model

        usb_debug = results.get("debugging", "0")
        info.usb_debugging = usb_debug == "1"
        dev_opts = results.get("developer_options", "0")
        info.developer_options = dev_opts == "1"

        try:
            battery_raw = await adb.shell(serial, "dumpsys battery")
            for line in (battery_raw or "").split("\n"):
                stripped = line.strip()
                if "level:" in stripped:
                    try:
                        info.battery_percentage = int(stripped.split(":")[-1].strip())
                    except ValueError:
                        pass
                if "AC powered" in stripped or "USB powered" in stripped:
                    info.charging = "true" in stripped.lower() or "1" in stripped
        except Exception:
            pass

        try:
            wm_size = await adb.shell(serial, "wm size")
            if wm_size and ":" in wm_size:
                size_part = wm_size.split(":")[-1].strip()
                if "x" in size_part:
                    parts = size_part.split("x")
                    try:
                        info.screen_width = int(parts[0])
                        info.screen_height = int(parts[1].split()[0])
                    except ValueError:
                        pass
        except Exception:
            pass

        try:
            meminfo = await adb.shell(serial, "cat /proc/meminfo 2>/dev/null | grep MemTotal")
            match = re.search(r"(\d+)", meminfo or "")
            if match:
                info.ram_total_kb = int(match.group(1))
        except Exception:
            pass

        try:
            storage = await adb.shell(serial, "df /data 2>/dev/null | tail -1")
            parts = (storage or "").split()
            if len(parts) >= 2:
                try:
                    info.storage_total_bytes = int(parts[1]) * 1024
                except ValueError:
                    pass
        except Exception:
            pass

        try:
            foreground = await adb.shell(serial, "dumpsys window windows 2>/dev/null | grep mCurrentFocus")
            match = re.search(r"(\S+)/\S+", foreground or "")
            if match:
                info.foreground_app = match.group(1)
        except Exception:
            pass

        try:
            display = await adb.shell(serial, "dumpsys display 2>/dev/null")
            info.screen_on = "state=on" in (display or "").lower()
        except Exception:
            pass

        try:
            policy = await adb.shell(serial, "dumpsys window policy 2>/dev/null")
            lowered = (policy or "").lower()
            if "mshowinglockscreen=true" in lowered or "isstatusbarkeyguard=true" in lowered:
                info.lock_state = "locked"
            else:
                info.lock_state = "unlocked"
        except Exception:
            info.lock_state = "unknown"

        try:
            accessibility = await adb.shell(serial, "settings get secure accessibility_enabled 2>/dev/null")
            info.accessibility_service = (accessibility or "").strip() == "1"
        except Exception:
            pass

        if info.battery_percentage > 0:
            if info.battery_percentage > 20:
                info.connection_quality = "good"
            elif info.battery_percentage > 10:
                info.connection_quality = "fair"
            else:
                info.connection_quality = "low"
        else:
            info.connection_quality = "unknown"

        return info

    async def verify_device(self, serial: str) -> Dict[str, Any]:
        """Deep verification: collect hardware identifiers for fingerprint generation"""
        adb = self._get_adb()
        fingerprint_data = {}

        props = {
            "android_id": "settings get secure android_id",
            "serial_no": "getprop ro.serialno",
            "board": "getprop ro.product.board",
            "device": "getprop ro.product.device",
            "hardware": "getprop ro.hardware",
            "fingerprint": "getprop ro.build.fingerprint",
            "security_patch": "getprop ro.build.version.security_patch",
            "manufacturer": "getprop ro.product.manufacturer",
            "model": "getprop ro.product.model",
            "brand": "getprop ro.product.brand",
        }

        for key, cmd in props.items():
            try:
                raw = await adb.shell(serial, cmd)
                fingerprint_data[key] = (raw or "").strip()
            except Exception:
                fingerprint_data[key] = ""

        try:
            packages_raw = await adb.shell(serial, "pm list packages 2>/dev/null | wc -l")
            fingerprint_data["installed_packages_count"] = (packages_raw or "0").strip()
        except Exception:
            fingerprint_data["installed_packages_count"] = "0"

        # Generate fingerprint hash
        fingerprint_raw = "|".join([
            fingerprint_data.get("android_id", ""),
            fingerprint_data.get("serial_no", ""),
            fingerprint_data.get("board", ""),
            fingerprint_data.get("hardware", ""),
            fingerprint_data.get("manufacturer", ""),
            fingerprint_data.get("model", ""),
        ])
        import hashlib
        fingerprint = hashlib.sha256(fingerprint_raw.encode()).hexdigest()

        return {
            "fingerprint": fingerprint,
            "fingerprint_data": fingerprint_data,
        }


_discovery_engine: Optional[USBDiscoveryEngine] = None


def get_discovery_engine(adb_service=None) -> USBDiscoveryEngine:
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = USBDiscoveryEngine(adb_service)
    return _discovery_engine
