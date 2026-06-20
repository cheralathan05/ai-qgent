"""Calendar device abstraction for APA-OS."""
import time
import uuid
from typing import Dict, Any, Optional, List

from ..device import Device, DeviceInfo, DeviceStatus


class CalendarDevice(Device):
    """Abstract representation of calendar service."""

    def __init__(self, device_id: str, provider: str = "google_calendar", **kwargs):
        super().__init__(device_id)
        if provider not in ("google_calendar", "outlook_calendar"):
            raise ValueError(f"Unsupported provider: {provider}")
        self.provider = provider
        self._connected = False
        self._events: Dict[str, dict] = {}

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _now(self) -> float:
        return time.time()

    async def connect(self) -> Dict[str, Any]:
        self._connected = True
        return {"status": "connected", "provider": self.provider, "message": f"Connected to {self.provider}"}

    async def disconnect(self) -> Dict[str, Any]:
        self._connected = False
        return {"status": "disconnected", "provider": self.provider, "message": f"Disconnected from {self.provider}"}

    async def status(self) -> Dict[str, Any]:
        return {"connected": self._connected, "provider": self.provider, "device_id": self.device_id, "event_count": len(self._events)}

    async def capabilities(self) -> List[str]:
        return ["calendar", "event_management", "scheduling"]

    async def get_info(self) -> DeviceInfo:
        return DeviceInfo(
            device_id=self.device_id,
            status=DeviceStatus.CONNECTED if self._connected else DeviceStatus.DISCONNECTED,
            is_locked=False,
            battery_level=None,
            foreground_app=None,
            installed_apps={"calendar"},
            capabilities={"calendar"},
            device_type="calendar",
            model_name=f"{self.provider.replace('_', ' ').title()}",
            os_version="cloud",
            additional={
                "provider": self.provider,
                "connected": self._connected,
                "event_count": len(self._events),
            },
        )

    async def list_events(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        result = []
        for event in self._events.values():
            if start_date <= event["start_time"] <= end_date or start_date <= event["end_time"] <= end_date:
                result.append({
                    "id": event["id"],
                    "summary": event["summary"],
                    "description": event.get("description", ""),
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "location": event.get("location", ""),
                    "attendees": event.get("attendees", []),
                })
        return result

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        event_id = self._generate_id()
        self._events[event_id] = {
            "id": event_id,
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "location": location,
            "attendees": attendees or [],
            "created_time": self._now(),
            "modified_time": self._now(),
        }
        return {"event_id": event_id, "status": "created"}

    async def update_event(self, event_id: str, **updates) -> Dict[str, Any]:
        if event_id not in self._events:
            return {"status": "error", "message": f"Event {event_id} not found"}
        allowed = {"summary", "start_time", "end_time", "description", "location", "attendees"}
        updated_fields = []
        for key, value in updates.items():
            if key in allowed:
                if key == "attendees" and not isinstance(value, list):
                    continue
                self._events[event_id][key] = value
                updated_fields.append(key)
        if updated_fields:
            self._events[event_id]["modified_time"] = self._now()
        return {"event_id": event_id, "status": "updated", "updated_fields": updated_fields}

    async def delete_event(self, event_id: str) -> Dict[str, Any]:
        if event_id not in self._events:
            return {"status": "error", "message": f"Event {event_id} not found"}
        del self._events[event_id]
        return {"status": "deleted", "event_id": event_id}

    async def get_event(self, event_id: str) -> Dict[str, Any]:
        event = self._events.get(event_id)
        if event is None:
            return {"status": "error", "message": f"Event {event_id} not found"}
        return {
            "id": event["id"],
            "summary": event["summary"],
            "description": event.get("description", ""),
            "start_time": event["start_time"],
            "end_time": event["end_time"],
            "location": event.get("location", ""),
            "attendees": event.get("attendees", []),
            "created_time": event.get("created_time"),
            "modified_time": event.get("modified_time"),
        }

    async def search_events(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        result = []
        for event in self._events.values():
            if (
                query_lower in event["summary"].lower()
                or query_lower in event.get("description", "").lower()
                or query_lower in event.get("location", "").lower()
            ):
                result.append({
                    "id": event["id"],
                    "summary": event["summary"],
                    "description": event.get("description", ""),
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "location": event.get("location", ""),
                    "attendees": event.get("attendees", []),
                })
        return result

    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        return {"status": "success", "app": app_name, "message": f"Launched {app_name} on {self.provider}"}

    async def send_text(self, text: str, target: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "send_text not supported for CalendarDevice"}

    async def verify_app_opened(self, app_name: str, timeout_seconds: int = 10) -> Dict[str, Any]:
        return {"status": "success", "verification": f"{app_name} is running", "app": app_name}
