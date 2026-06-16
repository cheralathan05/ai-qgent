"""Device abstraction layer for APA-OS."""
from .device_manager import DeviceManager
from .device import Device, DeviceInfo, DeviceStatus
from .android.android_device import AndroidDevice
from .windows.windows_device import WindowsDevice
from .browser.browser_device import BrowserDevice
from .drive.drive_device import DriveDevice
from .calendar.calendar_device import CalendarDevice

device_manager = DeviceManager()


def get_device_manager() -> DeviceManager:
    """Get the shared device manager."""
    return device_manager

__all__ = [
    "DeviceManager",
    "Device",
    "DeviceInfo",
    "DeviceStatus",
    "AndroidDevice",
    "WindowsDevice",
    "BrowserDevice",
    "DriveDevice",
    "CalendarDevice",
    "device_manager",
    "get_device_manager",
]
