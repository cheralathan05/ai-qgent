"""Metrics collection for all APA-OS operations."""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMetrics:
    workflow_id: str
    intent_detection_ms: float = 0.0
    planning_ms: float = 0.0
    execution_ms: float = 0.0
    verification_ms: float = 0.0
    total_duration_ms: float = 0.0
    step_count: int = 0
    retry_count: int = 0
    success: bool = False


@dataclass
class SystemMetrics:
    commands_executed: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    avg_execution_time_ms: float = 0.0
    voice_accuracy: float = 0.0
    ocr_accuracy: float = 0.0
    uptime_seconds: float = 0.0


@dataclass
class MetricPoint:
    name: str
    value: float
    unit: str
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Collects and aggregates system metrics."""

    def __init__(self):
        self.system = SystemMetrics()
        self._workflows: Dict[str, WorkflowMetrics] = {}
        self._points: list = []
        self._start_time = datetime.utcnow()

    def record_workflow(self, metrics: WorkflowMetrics) -> None:
        self._workflows[metrics.workflow_id] = metrics
        self.system.commands_executed += 1
        if metrics.success:
            self.system.success_count += 1
        else:
            self.system.failure_count += 1
        self.system.retry_count += metrics.retry_count
        self._recalc_averages()

    def _recalc_averages(self) -> None:
        times = [w.total_duration_ms for w in self._workflows.values()]
        if times:
            self.system.avg_execution_time_ms = sum(times) / len(times)

    def record_point(self, name: str, value: float, unit: str = "count", tags: Optional[Dict[str, str]] = None) -> None:
        self._points.append(MetricPoint(name=name, value=value, unit=unit, tags=tags or {}))

    def get_success_rate(self) -> float:
        total = self.system.commands_executed
        if total == 0:
            return 1.0
        return self.system.success_count / total

    def get_failure_rate(self) -> float:
        total = self.system.commands_executed
        if total == 0:
            return 0.0
        return self.system.failure_count / total

    def get_retry_rate(self) -> float:
        total = self.system.commands_executed
        if total == 0:
            return 0.0
        return self.system.retry_count / total

    def get_summary(self) -> Dict[str, Any]:
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        self.system.uptime_seconds = uptime
        return {
            "commands_executed": self.system.commands_executed,
            "success_rate": self.get_success_rate(),
            "failure_rate": self.get_failure_rate(),
            "retry_rate": self.get_retry_rate(),
            "avg_execution_time_ms": round(self.system.avg_execution_time_ms, 2),
            "uptime_seconds": uptime,
            "workflow_count": len(self._workflows),
        }

    def get_workflow_metrics(self, workflow_id: str) -> Optional[WorkflowMetrics]:
        return self._workflows.get(workflow_id)

    def get_recent_points(self, limit: int = 100) -> list:
        return self._points[-limit:]


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
