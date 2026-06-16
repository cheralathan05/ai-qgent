"""Device manager for APA-OS."""
import logging
from typing import Dict, Optional

from .device import Device
from .android.android_device import AndroidDevice
from .windows.windows_device import WindowsDevice
from .browser.browser_device import BrowserDevice
from .drive.drive_device import DriveDevice
from .calendar.calendar_device import CalendarDevice

logger = logging.getLogger(__name__)


class DeviceManager:
    """Registry and factory for devices."""

    def __init__(self):
        self.devices: Dict[str, Device] = {}

    def register_device(self, device: Device) -> None:
        logger.info(f"Registering device: {device.device_id}")
        self.devices[device.device_id] = device

    def get_device(self, device_id: str) -> Optional[Device]:
        return self.devices.get(device_id)

    def list_devices(self):
        return list(self.devices.values())

    def unregister_device(self, device_id: str) -> None:
        if device_id in self.devices:
            del self.devices[device_id]

    def create_device(self, device_type: str, device_id: str, **kwargs) -> Device:
        if device_type == "android":
            return AndroidDevice(device_id, **kwargs)
        if device_type == "windows":
            return WindowsDevice(device_id, **kwargs)
        if device_type == "browser":
            return BrowserDevice(device_id, **kwargs)
        if device_type == "drive":
            return DriveDevice(device_id, **kwargs)
        if device_type == "calendar":
            return CalendarDevice(device_id, **kwargs)

        raise ValueError(f"Unsupported device type: {device_type}")
