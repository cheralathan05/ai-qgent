"""
APA-OS Heartbeat Service
Manages device heartbeat monitoring, live state tracking, and disconnect detection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatData:
    device_id: str
    battery_level: int = 0
    battery_charging: bool = False
    foreground_app: str = ""
    foreground_package: str = ""
    current_activity: str = ""
    screen_state: str = ""
    lock_state: str = ""
    network_type: str = ""
    network_strength: int = 0
    memory_usage_mb: int = 0
    cpu_usage_percent: float = 0.0
    storage_free_gb: float = 0.0
    storage_total_gb: float = 0.0
    uptime_seconds: int = 0
    agent_version: str = ""
    accessibility_active: bool = False


class HeartbeatService:
    def __init__(self):
        self._device_last_heartbeat: Dict[str, datetime] = {}
        self._device_data: Dict[str, HeartbeatData] = {}
        self._disconnect_threshold_seconds = 15  # Consider disconnected after 15s without heartbeat
        self._running = False
        self._monitor_task = None

    def start_monitoring(self):
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Heartbeat monitoring started")

    async def stop_monitoring(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat monitoring stopped")

    def record_heartbeat(self, device_id: str, data: HeartbeatData) -> bool:
        """Record a heartbeat from device. Returns True if device was previously disconnected."""
        was_disconnected = False
        if device_id in self._device_last_heartbeat:
            elapsed = (datetime.utcnow() - self._device_last_heartbeat[device_id]).total_seconds()
            if elapsed > self._disconnect_threshold_seconds:
                was_disconnected = True

        self._device_last_heartbeat[device_id] = datetime.utcnow()
        self._device_data[device_id] = data

        self._persist_heartbeat(device_id, data)
        return was_disconnected

    def is_device_online(self, device_id: str) -> bool:
        if device_id not in self._device_last_heartbeat:
            return False
        elapsed = (datetime.utcnow() - self._device_last_heartbeat[device_id]).total_seconds()
        return elapsed < self._disconnect_threshold_seconds

    def get_device_data(self, device_id: str) -> Optional[HeartbeatData]:
        if not self.is_device_online(device_id):
            return None
        return self._device_data.get(device_id)

    def get_all_online_devices(self) -> list:
        online = []
        for device_id, last_seen in self._device_last_heartbeat.items():
            if (datetime.utcnow() - last_seen).total_seconds() < self._disconnect_threshold_seconds:
                online.append(device_id)
        return online

    def get_disconnected_devices(self) -> list:
        disconnected = []
        for device_id, last_seen in self._device_last_heartbeat.items():
            if (datetime.utcnow() - last_seen).total_seconds() >= self._disconnect_threshold_seconds:
                disconnected.append(device_id)
        return disconnected

    def _persist_heartbeat(self, device_id: str, data: HeartbeatData):
        """Persist heartbeat to database"""
        try:
            from database.connection import get_db_session
            from database.auth_models import DeviceHeartbeat, RegisteredDevice

            db = get_db_session()
            try:
                heartbeat = DeviceHeartbeat(
                    device_id=device_id,
                    battery_level=data.battery_level,
                    battery_charging=data.battery_charging,
                    foreground_app=data.foreground_app,
                    foreground_package=data.foreground_package,
                    current_activity=data.current_activity,
                    screen_state=data.screen_state,
                    lock_state=data.lock_state,
                    network_type=data.network_type,
                    network_strength=data.network_strength,
                    memory_usage_mb=data.memory_usage_mb,
                    cpu_usage_percent=data.cpu_usage_percent,
                    storage_free_gb=data.storage_free_gb,
                    storage_total_gb=data.storage_total_gb,
                    uptime_seconds=data.uptime_seconds,
                    agent_version=data.agent_version,
                    accessibility_active=data.accessibility_active,
                    recorded_at=datetime.utcnow(),
                )
                db.add(heartbeat)

                # Update device online status
                device = db.query(RegisteredDevice).filter(
                    RegisteredDevice.id == device_id
                ).first()
                if device:
                    device.is_online = True
                    device.battery_level = data.battery_level
                    device.last_seen = datetime.utcnow()

                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to persist heartbeat for {device_id}: {e}")

    def mark_device_disconnected(self, device_id: str):
        """Mark device as disconnected in database"""
        try:
            from database.connection import get_db_session
            from database.auth_models import RegisteredDevice

            db = get_db_session()
            try:
                device = db.query(RegisteredDevice).filter(
                    RegisteredDevice.id == device_id
                ).first()
                if device:
                    device.is_online = False
                    device.updated_at = datetime.utcnow()
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to mark device {device_id} disconnected: {e}")

        if device_id in self._device_last_heartbeat:
            del self._device_last_heartbeat[device_id]
        if device_id in self._device_data:
            del self._device_data[device_id]

    async def _monitor_loop(self):
        """Monitor for disconnected devices every 5 seconds"""
        while self._running:
            try:
                await asyncio.sleep(5)
                now = datetime.utcnow()
                for device_id in list(self._device_last_heartbeat.keys()):
                    last = self._device_last_heartbeat[device_id]
                    if (now - last).total_seconds() >= self._disconnect_threshold_seconds:
                        logger.warning(f"Device {device_id} heartbeat lost")
                        self.mark_device_disconnected(device_id)
                        # Emit disconnect event
                        self._emit_event("DEVICE_DISCONNECTED", {
                            "device_id": device_id,
                            "reason": "heartbeat_lost",
                            "last_seen": last.isoformat(),
                        })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")

    def _emit_event(self, event_type: str, data: dict):
        """Emit event through websocket"""
        try:
            from services.websocket_service import get_websocket_manager
            import json
            mgr = get_websocket_manager()
            asyncio.ensure_future(mgr.broadcast({
                "event": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }))
        except Exception:
            pass


_heartbeat_service: Optional[HeartbeatService] = None


def get_heartbeat_service() -> HeartbeatService:
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service
