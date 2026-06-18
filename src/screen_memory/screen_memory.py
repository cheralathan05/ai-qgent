"""Screen Memory: stores current screen, navigation history, app state, and changes."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScreenSnapshot:
    device_id: str
    screen_name: str
    app_name: Optional[str] = None
    screen_type: str = "unknown"
    elements: List[Dict[str, Any]] = field(default_factory=list)
    text_content: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "screen_name": self.screen_name,
            "app_name": self.app_name,
            "screen_type": self.screen_type,
            "elements": self.elements,
            "text_content": self.text_content,
            "detected_at": self.detected_at.isoformat(),
            "metadata": self.metadata,
        }


class ScreenMemory:
    """Stores and manages screen navigation history per device."""

    MAX_HISTORY = 100

    def __init__(self):
        self._history: Dict[str, List[ScreenSnapshot]] = {}
        self._current: Dict[str, Optional[ScreenSnapshot]] = {}

    def record_screen(self, device_id: str, snapshot: ScreenSnapshot) -> None:
        if device_id not in self._history:
            self._history[device_id] = []
        self._history[device_id].append(snapshot)
        self._current[device_id] = snapshot
        if len(self._history[device_id]) > self.MAX_HISTORY:
            self._history[device_id] = self._history[device_id][-self.MAX_HISTORY:]
        logger.info(f"Screen recorded for {device_id}: {snapshot.screen_name}")

    def get_current_screen(self, device_id: str) -> Optional[ScreenSnapshot]:
        return self._current.get(device_id)

    def get_previous_screen(self, device_id: str) -> Optional[ScreenSnapshot]:
        history = self._history.get(device_id, [])
        if len(history) >= 2:
            return history[-2]
        return None

    def get_navigation_history(self, device_id: str) -> List[ScreenSnapshot]:
        return list(self._history.get(device_id, []))

    def get_last_app_screen(self, device_id: str, app_name: str) -> Optional[ScreenSnapshot]:
        history = self._history.get(device_id, [])
        for snap in reversed(history):
            if snap.app_name == app_name:
                return snap
        return None

    def clear_history(self, device_id: str) -> None:
        self._history.pop(device_id, None)
        self._current.pop(device_id, None)
        logger.info(f"Screen history cleared for {device_id}")

    def get_screen_changes(self, device_id: str) -> List[Dict[str, Any]]:
        history = self._history.get(device_id, [])
        changes = []
        for i in range(1, len(history)):
            prev = history[i - 1]
            curr = history[i]
            if prev.screen_name != curr.screen_name:
                changes.append({
                    "from_screen": prev.screen_name,
                    "to_screen": curr.screen_name,
                    "from_app": prev.app_name,
                    "to_app": curr.app_name,
                    "detected_at": curr.detected_at.isoformat(),
                })
        return changes


_screen_memory: Optional[ScreenMemory] = None


def get_screen_memory() -> ScreenMemory:
    global _screen_memory
    if _screen_memory is None:
        _screen_memory = ScreenMemory()
    return _screen_memory
