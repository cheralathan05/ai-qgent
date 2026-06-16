"""
Device Intelligence
Detects device state, capabilities, and requirements
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DeviceCapability(str, Enum):
    """Device capabilities"""
    TOUCH = "touch"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    BLUETOOTH = "bluetooth"
    NFC = "nfc"
    BIOMETRIC = "biometric"
    GPS = "gps"


@dataclass
class DeviceInfo:
    """Complete device information"""
    device_id: str
    is_connected: bool
    is_locked: bool
    battery_level: int
    screen_on: bool
    foreground_app: Optional[str]
    installed_apps: Set[str]
    available_capabilities: Set[DeviceCapability]
    android_version: str
    model_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "is_connected": self.is_connected,
            "is_locked": self.is_locked,
            "battery_level": self.battery_level,
            "screen_on": self.screen_on,
            "foreground_app": self.foreground_app,
            "installed_apps": list(self.installed_apps),
            "available_capabilities": [c.value for c in self.available_capabilities],
            "android_version": self.android_version,
            "model_name": self.model_name,
        }


class DeviceIntelligence:
    """Intelligent device state detection"""
    
    def __init__(self, adb_client):
        self.adb = adb_client
        self.device_cache: Dict[str, DeviceInfo] = {}
        self._lock = asyncio.Lock()
    
    async def get_device_info(self, device_id: str) -> DeviceInfo:
        """
        Get complete device information
        
        Args:
            device_id: Device ID/serial
            
        Returns:
            Complete DeviceInfo
        """
        async with self._lock:
            # Check cache (may be slightly stale but fast)
            if device_id in self.device_cache:
                return self.device_cache[device_id]
            
            # Get fresh device info
            info = await self._fetch_device_info(device_id)
            self.device_cache[device_id] = info
            return info
    
    async def _fetch_device_info(self, device_id: str) -> DeviceInfo:
        """Fetch fresh device information via ADB"""
        try:
            # Check connection
            is_connected = await self._is_connected(device_id)
            
            if not is_connected:
                return DeviceInfo(
                    device_id=device_id,
                    is_connected=False,
                    is_locked=False,
                    battery_level=0,
                    screen_on=False,
                    foreground_app=None,
                    installed_apps=set(),
                    available_capabilities=set(),
                    android_version="",
                    model_name="",
                )
            
            # Fetch all info in parallel
            results = await asyncio.gather(
                self._is_locked(device_id),
                self._get_battery_level(device_id),
                self._is_screen_on(device_id),
                self._get_foreground_app(device_id),
                self._get_installed_apps(device_id),
                self._get_android_version(device_id),
                self._get_model_name(device_id),
                self._detect_capabilities(device_id),
                return_exceptions=True,
            )
            
            is_locked = results[0] if not isinstance(results[0], Exception) else False
            battery = results[1] if not isinstance(results[1], Exception) else 0
            screen_on = results[2] if not isinstance(results[2], Exception) else False
            foreground = results[3] if not isinstance(results[3], Exception) else None
            apps = results[4] if not isinstance(results[4], Exception) else set()
            android = results[5] if not isinstance(results[5], Exception) else ""
            model = results[6] if not isinstance(results[6], Exception) else ""
            caps = results[7] if not isinstance(results[7], Exception) else set()
            
            return DeviceInfo(
                device_id=device_id,
                is_connected=True,
                is_locked=is_locked,
                battery_level=battery,
                screen_on=screen_on,
                foreground_app=foreground,
                installed_apps=apps,
                available_capabilities=caps,
                android_version=android,
                model_name=model,
            )
        
        except Exception as e:
            logger.error(f"Error fetching device info: {e}")
            return DeviceInfo(
                device_id=device_id,
                is_connected=False,
                is_locked=False,
                battery_level=0,
                screen_on=False,
                foreground_app=None,
                installed_apps=set(),
                available_capabilities=set(),
                android_version="",
                model_name="",
            )
    
    async def _is_connected(self, device_id: str) -> bool:
        """Check if device is connected"""
        try:
            devices = await self.adb.list_devices()
            return device_id in [d.get('serial') for d in devices]
        except Exception as e:
            logger.error(f"Error checking device connection: {e}")
            return False
    
    async def _is_locked(self, device_id: str) -> bool:
        """Check if device is locked"""
        try:
            result = await self.adb.shell(device_id, "dumpsys keyguard | grep 'mShowing'")
            return "true" in result.lower()
        except Exception as e:
            logger.warning(f"Error checking lock status: {e}")
            return False
    
    async def _get_battery_level(self, device_id: str) -> int:
        """Get battery level percentage"""
        try:
            result = await self.adb.shell(device_id, "dumpsys battery | grep level")
            level = int(result.split(":")[-1].strip())
            return min(100, max(0, level))
        except Exception as e:
            logger.warning(f"Error getting battery level: {e}")
            return 0
    
    async def _is_screen_on(self, device_id: str) -> bool:
        """Check if screen is on"""
        try:
            result = await self.adb.shell(device_id, "dumpsys display | grep 'mDisplayState'")
            return "on" in result.lower() or "2" in result  # State 2 = ON
        except Exception as e:
            logger.warning(f"Error checking screen state: {e}")
            return False
    
    async def _get_foreground_app(self, device_id: str) -> Optional[str]:
        """Get currently active app"""
        try:
            result = await self.adb.shell(
                device_id,
                "dumpsys window windows | grep 'mCurrentFocus' | head -1"
            )
            # Parse package name from output
            if "/" in result:
                return result.split("/")[0].split()[-1]
            return None
        except Exception as e:
            logger.warning(f"Error getting foreground app: {e}")
            return None
    
    async def _get_installed_apps(self, device_id: str) -> Set[str]:
        """Get list of installed apps"""
        try:
            result = await self.adb.shell(device_id, "pm list packages")
            apps = {line.replace("package:", "").strip() 
                   for line in result.split("\n") if line.strip()}
            return apps
        except Exception as e:
            logger.warning(f"Error getting installed apps: {e}")
            return set()
    
    async def _get_android_version(self, device_id: str) -> str:
        """Get Android version"""
        try:
            result = await self.adb.shell(device_id, "getprop ro.build.version.release")
            return result.strip()
        except Exception as e:
            logger.warning(f"Error getting Android version: {e}")
            return ""
    
    async def _get_model_name(self, device_id: str) -> str:
        """Get device model name"""
        try:
            result = await self.adb.shell(device_id, "getprop ro.product.model")
            return result.strip()
        except Exception as e:
            logger.warning(f"Error getting model name: {e}")
            return ""
    
    async def _detect_capabilities(self, device_id: str) -> Set[DeviceCapability]:
        """Detect device capabilities"""
        capabilities = set()
        
        try:
            # Check capabilities via pm dump
            result = await self.adb.shell(
                device_id,
                "pm dump | grep 'Feature:' | grep -i -E '(camera|microphone|nfc|gps|biometric)'"
            )
            
            if "camera" in result.lower():
                capabilities.add(DeviceCapability.CAMERA)
            if "microphone" in result.lower():
                capabilities.add(DeviceCapability.MICROPHONE)
            if "nfc" in result.lower():
                capabilities.add(DeviceCapability.NFC)
            if "gps" in result.lower():
                capabilities.add(DeviceCapability.GPS)
            if "biometric" in result.lower():
                capabilities.add(DeviceCapability.BIOMETRIC)
            
            # Touch is assumed for all Android devices
            capabilities.add(DeviceCapability.TOUCH)
        
        except Exception as e:
            logger.warning(f"Error detecting capabilities: {e}")
            capabilities.add(DeviceCapability.TOUCH)
        
        return capabilities
    
    async def is_app_installed(self, device_id: str, package_name: str) -> bool:
        """Check if specific app is installed"""
        info = await self.get_device_info(device_id)
        return package_name in info.installed_apps
    
    async def check_permission(self, device_id: str, permission: str) -> bool:
        """Check if permission is granted"""
        try:
            # This would need a package_name to check
            # Simplified implementation
            return True
        except Exception as e:
            logger.warning(f"Error checking permission: {e}")
            return False
    
    def invalidate_cache(self, device_id: str) -> None:
        """Invalidate cached device info"""
        if device_id in self.device_cache:
            del self.device_cache[device_id]
    
    def invalidate_all_cache(self) -> None:
        """Invalidate all cached device info"""
        self.device_cache.clear()


# Global instance
device_intelligence = None


def get_device_intelligence(adb_client=None) -> DeviceIntelligence:
    """Get or create device intelligence instance"""
    global device_intelligence
    if device_intelligence is None and adb_client:
        device_intelligence = DeviceIntelligence(adb_client)
    return device_intelligence
