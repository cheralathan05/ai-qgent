"""Device agent that discovers and controls connected Android devices."""

import logging
from typing import Any, Dict, List, Optional

from console.event_stream import EventSeverity, EventType, get_event_manager
from database.connection import upsert_device_record, update_device_state
from devices import AndroidDevice, DeviceStatus, device_manager
from services.adb_service import get_adb_service
from config import Config

logger = logging.getLogger(__name__)


class DeviceAgent:
    """Coordinates Android discovery, status, and basic app actions."""

    def __init__(self, adb_client=None):
        self.adb = adb_client or get_adb_service(
            Config.get_adb_config().adb_path,
            Config.get_adb_config().default_timeout,
        )
        self.device_manager = device_manager
        self.event_manager = get_event_manager()

    async def discover_devices(self) -> List[AndroidDevice]:
        discovered: List[AndroidDevice] = []
        for device_metadata in await self.adb.discover_devices():
            device_id = device_metadata["device_id"]
            device = self.device_manager.get_device(device_id)
            if not isinstance(device, AndroidDevice):
                device = AndroidDevice(device_id=device_id, adb_client=self.adb)
                self.device_manager.register_device(device)

            info = await device.get_info()
            upsert_device_record(device_id, "android", metadata=info.to_dict(), is_active=True)
            update_device_state(
                device_id,
                is_connected=True,
                is_locked=info.is_locked,
                battery_level=info.battery_level,
                foreground_app=info.foreground_app,
                installed_apps=sorted(info.installed_apps),
                metadata=info.to_dict(),
            )

            await self.event_manager.emit(
                workflow_id="system",
                event_type=EventType.DEVICE_CONNECTED,
                payload=info.to_dict(),
                source="device_agent",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
            await self.event_manager.emit(
                workflow_id="system",
                event_type=EventType.DEVICE_STATUS_UPDATED,
                payload=info.to_dict(),
                source="device_agent",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
            discovered.append(device)

        return discovered

    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            status = await device.get_device_status()
            await self.event_manager.emit(
                workflow_id="system",
                event_type=EventType.DEVICE_STATUS_UPDATED,
                payload=status,
                source="device_agent",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )
            return status

        status = await self.adb.get_device_status(device_id)
        await self.event_manager.emit(
            workflow_id="system",
            event_type=EventType.DEVICE_STATUS_UPDATED,
            payload=status,
            source="device_agent",
            severity=EventSeverity.INFO,
            device_id=device_id,
        )
        return status

    async def open_app(self, device_id: str, app_name: str) -> Dict[str, Any]:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            result = await device.open_app(app_name)
        else:
            result = {"status": "error", "message": f"Android device not registered: {device_id}"}

        if result.get("status") == "success":
            await self.event_manager.emit(
                workflow_id="system",
                event_type=EventType.APP_OPENED,
                payload={"device_id": device_id, "app": app_name, **result},
                source="device_agent",
                severity=EventSeverity.INFO,
                device_id=device_id,
            )

        return result

    async def close_app(self, device_id: str, app_name: str) -> Dict[str, Any]:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            return await device.close_app(app_name)

        return {"status": "error", "message": f"Android device not registered: {device_id}"}

    async def get_foreground_app(self, device_id: str) -> Optional[str]:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            return await device.get_foreground_app()
        return await self.adb.get_foreground_app(device_id)

    async def get_battery(self, device_id: str) -> Optional[int]:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            return await device.get_battery()
        return await self.adb.get_battery_level(device_id)

    async def take_screenshot(self, device_id: str) -> Any:
        device = self.device_manager.get_device(device_id)
        if isinstance(device, AndroidDevice):
            return await device.take_screenshot()
        return {"status": "error", "message": f"Android device not registered: {device_id}"}


device_agent = None


def get_device_agent(adb_client=None) -> DeviceAgent:
    global device_agent
    if device_agent is None:
        device_agent = DeviceAgent(adb_client=adb_client)
    elif adb_client is not None and device_agent.adb is None:
        device_agent.adb = adb_client
    return device_agent