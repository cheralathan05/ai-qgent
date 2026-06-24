"""Learning Agent - Success/failure pattern learning.

Records action outcomes and adjusts strategies based on history.
Identifies common failure patterns and suggests improvements.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

LEARNING_DIR = os.path.join(os.path.expanduser("~"), ".apa_os", "learning")


@dataclass
class ActionRecord:
    action_type: str
    target: str
    app_name: str
    success: bool
    confidence: float
    retries: int
    error: str = ""
    execution_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FailurePattern:
    pattern: str
    count: int
    last_seen: float
    apps_affected: List[str] = field(default_factory=list)
    suggested_fix: str = ""


class LearningAgent:
    """Learns from action outcomes to improve future performance."""

    def __init__(self):
        os.makedirs(LEARNING_DIR, exist_ok=True)
        self._records: List[ActionRecord] = []
        self._failure_patterns: Dict[str, FailurePattern] = {}
        self._load_history()

    def _load_history(self):
        try:
            history_file = os.path.join(LEARNING_DIR, "action_history.json")
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    data = json.load(f)
                for r in data.get("records", []):
                    self._records.append(ActionRecord(**r))
                for k, v in data.get("failure_patterns", {}).items():
                    self._failure_patterns[k] = FailurePattern(**v)
                logger.info(f"Loaded {len(self._records)} action records")
        except Exception as e:
            logger.warning(f"Failed to load learning history: {e}")

    def _save_history(self):
        try:
            history_file = os.path.join(LEARNING_DIR, "action_history.json")
            data = {
                "records": [
                    {
                        "action_type": r.action_type,
                        "target": r.target,
                        "app_name": r.app_name,
                        "success": r.success,
                        "confidence": r.confidence,
                        "retries": r.retries,
                        "error": r.error,
                        "execution_time_ms": r.execution_time_ms,
                        "timestamp": r.timestamp,
                    }
                    for r in self._records[-1000:]  # Keep last 1000
                ],
                "failure_patterns": {
                    k: {
                        "pattern": p.pattern,
                        "count": p.count,
                        "last_seen": p.last_seen,
                        "apps_affected": p.apps_affected,
                        "suggested_fix": p.suggested_fix,
                    }
                    for k, p in self._failure_patterns.items()
                },
            }
            with open(history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save learning history: {e}")

    def record_action(self, record: ActionRecord):
        """Record an action outcome."""
        self._records.append(record)

        if not record.success:
            self._update_failure_pattern(record)

        self._save_history()

    def _update_failure_pattern(self, record: ActionRecord):
        key = f"{record.action_type}:{record.target}"
        if key not in self._failure_patterns:
            self._failure_patterns[key] = FailurePattern(
                pattern=key,
                count=0,
                last_seen=time.time(),
                suggested_fix=self._suggest_fix(record),
            )

        pattern = self._failure_patterns[key]
        pattern.count += 1
        pattern.last_seen = time.time()
        if record.app_name and record.app_name not in pattern.apps_affected:
            pattern.apps_affected.append(record.app_name)

    def _suggest_fix(self, record: ActionRecord) -> str:
        if record.error and "not found" in record.error.lower():
            return "Element not detected - try alternative detection or increase wait time"
        if record.retries > 1:
            return "Multiple retries needed - element position may have changed"
        if record.execution_time_ms > 10000:
            return "Slow execution - consider reducing wait times or using cached positions"
        return "Review element detection accuracy"

    def get_success_rate(
        self, action_type: Optional[str] = None, app_name: Optional[str] = None
    ) -> float:
        records = self._records
        if action_type:
            records = [r for r in records if r.action_type == action_type]
        if app_name:
            records = [r for r in records if r.app_name == app_name]
        if not records:
            return 0.0
        return sum(1 for r in records if r.success) / len(records)

    def get_common_failures(
        self, app_name: Optional[str] = None, limit: int = 10
    ) -> List[FailurePattern]:
        patterns = list(self._failure_patterns.values())
        if app_name:
            patterns = [p for p in patterns if app_name in p.apps_affected]
        patterns.sort(key=lambda p: p.count, reverse=True)
        return patterns[:limit]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._records)
        successful = sum(1 for r in self._records if r.success)
        avg_retries = (
            sum(r.retries for r in self._records) / total if total > 0 else 0
        )
        avg_time = (
            sum(r.execution_time_ms for r in self._records) / total if total > 0 else 0
        )

        return {
            "total_actions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_retries": avg_retries,
            "avg_execution_time_ms": avg_time,
            "failure_patterns": len(self._failure_patterns),
        }


_learning_agent: Optional[LearningAgent] = None


def get_learning_agent() -> LearningAgent:
    global _learning_agent
    if _learning_agent is None:
        _learning_agent = LearningAgent()
    return _learning_agent
