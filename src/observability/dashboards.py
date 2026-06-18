"""Dashboard generators for observability data."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from observability.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class DashboardManager:
    """Generates dashboard views from metrics."""

    def __init__(self):
        self.metrics = get_metrics_collector()

    def get_workflow_dashboard(self) -> Dict[str, Any]:
        summary = self.metrics.get_summary()
        return {
            "type": "workflow",
            "title": "Workflow Dashboard",
            "metrics": summary,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_device_dashboard(self) -> Dict[str, Any]:
        return {
            "type": "device",
            "title": "Device Dashboard",
            "metrics": {
                "connected_devices": 0,
                "active_sessions": 0,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_voice_dashboard(self) -> Dict[str, Any]:
        summary = self.metrics.get_summary()
        return {
            "type": "voice",
            "title": "Voice Dashboard",
            "metrics": {
                "voice_accuracy": summary.get("voice_accuracy", 0),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_screen_dashboard(self) -> Dict[str, Any]:
        return {
            "type": "screen",
            "title": "Screen Dashboard",
            "metrics": {},
            "generated_at": datetime.utcnow().isoformat(),
        }


_dashboard_manager: Optional[DashboardManager] = None


def get_dashboard_manager() -> DashboardManager:
    global _dashboard_manager
    if _dashboard_manager is None:
        _dashboard_manager = DashboardManager()
    return _dashboard_manager
