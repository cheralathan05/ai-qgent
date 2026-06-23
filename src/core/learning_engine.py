"""
APA-OS Learning Engine (Layer 10)

Learns:
- Frequently opened apps
- Frequently contacted people
- Frequently accessed files
- Preferred workflows
- Preferred learning topics

Builds personalized automation suggestions.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class UserPattern:
    """A learned user pattern."""
    pattern_type: str  # app_usage, contact_frequency, file_access, workflow, topic
    key: str
    count: int
    last_used: float
    avg_interval_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationSuggestion:
    """A suggested automation based on learned patterns."""
    title: str
    description: str
    workflow: List[Dict[str, Any]]
    confidence: float
    reason: str
    category: str  # frequency, time_based, context_based


class LearningEngine:
    """
    Learns from user behavior and suggests automations.
    
    Tracks:
    - App usage frequency
    - Contact interaction frequency
    - File access patterns
    - Workflow patterns
    - Topic interests
    - Time-based patterns
    """

    def __init__(self):
        self._patterns: Dict[str, List[UserPattern]] = {
            "app_usage": [],
            "contact_frequency": [],
            "file_access": [],
            "workflow": [],
            "topic_interest": [],
            "time_pattern": [],
        }
        self._interaction_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000

    def record_interaction(
        self,
        interaction_type: str,
        key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a user interaction for learning."""
        entry = {
            "type": interaction_type,
            "key": key,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self._interaction_log.append(entry)

        # Trim log if too large
        if len(self._interaction_log) > self._max_log_size:
            self._interaction_log = self._interaction_log[-self._max_log_size:]

        # Update patterns
        self._update_pattern(interaction_type, key, metadata)

    def _update_pattern(
        self,
        pattern_type: str,
        key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Update a learned pattern."""
        patterns = self._patterns.get(pattern_type, [])
        
        # Find existing pattern
        for p in patterns:
            if p.key == key:
                p.count += 1
                now = time.time()
                if p.last_used > 0:
                    interval = now - p.last_used
                    p.avg_interval_ms = (p.avg_interval_ms * (p.count - 1) + interval) / p.count
                p.last_used = now
                if metadata:
                    p.metadata.update(metadata)
                return
        
        # Create new pattern
        patterns.append(UserPattern(
            pattern_type=pattern_type,
            key=key,
            count=1,
            last_used=time.time(),
            metadata=metadata or {},
        ))
        self._patterns[pattern_type] = patterns

    def get_frequent_apps(self, top_n: int = 10) -> List[UserPattern]:
        """Get frequently used apps."""
        patterns = self._patterns.get("app_usage", [])
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:top_n]

    def get_frequent_contacts(self, top_n: int = 10) -> List[UserPattern]:
        """Get frequently contacted people."""
        patterns = self._patterns.get("contact_frequency", [])
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:top_n]

    def get_frequent_files(self, top_n: int = 10) -> List[UserPattern]:
        """Get frequently accessed files."""
        patterns = self._patterns.get("file_access", [])
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:top_n]

    def get_preferred_topics(self, top_n: int = 10) -> List[UserPattern]:
        """Get preferred learning topics."""
        patterns = self._patterns.get("topic_interest", [])
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:top_n]

    def get_common_workflows(self, top_n: int = 5) -> List[UserPattern]:
        """Get common workflow patterns."""
        patterns = self._patterns.get("workflow", [])
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:top_n]

    async def suggest_automations(self) -> List[AutomationSuggestion]:
        """Suggest automations based on learned patterns."""
        suggestions = []

        # Frequency-based suggestions
        frequent_apps = self.get_frequent_apps(5)
        if frequent_apps:
            top_app = frequent_apps[0]
            if top_app.count >= 3:
                suggestions.append(AutomationSuggestion(
                    title=f"Quick open {top_app.key}",
                    description=f"You open {top_app.key} frequently. Create a shortcut?",
                    workflow=[{"action": "open_app", "package": top_app.key}],
                    confidence=min(top_app.count / 10, 1.0),
                    reason=f"Used {top_app.count} times",
                    category="frequency",
                ))

        # Contact-based suggestions
        frequent_contacts = self.get_frequent_contacts(5)
        if frequent_contacts:
            top_contact = frequent_contacts[0]
            if top_contact.count >= 3:
                suggestions.append(AutomationSuggestion(
                    title=f"Quick message {top_contact.key}",
                    description=f"You message {top_contact.key} frequently. Create a shortcut?",
                    workflow=[{"action": "send_message", "contact": top_contact.key}],
                    confidence=min(top_contact.count / 10, 1.0),
                    reason=f"Contacted {top_contact.count} times",
                    category="frequency",
                ))

        # Workflow-based suggestions
        common_workflows = self.get_common_workflows(3)
        for wf in common_workflows:
            if wf.count >= 2:
                suggestions.append(AutomationSuggestion(
                    title=f"Repeat workflow: {wf.key}",
                    description=f"You've done this workflow {wf.count} times. Automate it?",
                    workflow=wf.metadata.get("steps", []),
                    confidence=min(wf.count / 5, 1.0),
                    reason=f"Repeated {wf.count} times",
                    category="frequency",
                ))

        # Time-based suggestions
        time_patterns = self._patterns.get("time_pattern", [])
        morning_apps = [p for p in time_patterns if p.metadata.get("time_of_day") == "morning"]
        if morning_apps:
            suggestions.append(AutomationSuggestion(
                title="Morning routine",
                description="Start your day with your常用 apps?",
                workflow=[{"action": "open_app", "package": p.key} for p in morning_apps[:3]],
                confidence=0.6,
                reason="Based on morning usage patterns",
                category="time_based",
            ))

        return suggestions

    async def analyze_behavior(self) -> Dict[str, Any]:
        """Analyze user behavior and return insights."""
        insights = {
            "total_interactions": len(self._interaction_log),
            "unique_apps": len(self._patterns.get("app_usage", [])),
            "unique_contacts": len(self._patterns.get("contact_frequency", [])),
            "unique_files": len(self._patterns.get("file_access", [])),
            "unique_topics": len(self._patterns.get("topic_interest", [])),
            "frequent_apps": [
                {"name": p.key, "count": p.count}
                for p in self.get_frequent_apps(5)
            ],
            "frequent_contacts": [
                {"name": p.key, "count": p.count}
                for p in self.get_frequent_contacts(5)
            ],
            "suggestions_count": len(await self.suggest_automations()),
        }

        # Calculate usage distribution
        app_patterns = self._patterns.get("app_usage", [])
        if app_patterns:
            total_usage = sum(p.count for p in app_patterns)
            insights["usage_distribution"] = {
                p.key: p.count / total_usage
                for p in app_patterns[:5]
            }

        return insights

    def get_pattern(self, pattern_type: str, key: str) -> Optional[UserPattern]:
        """Get a specific pattern."""
        patterns = self._patterns.get(pattern_type, [])
        for p in patterns:
            if p.key == key:
                return p
        return None

    def get_all_patterns(self) -> Dict[str, List[UserPattern]]:
        """Get all learned patterns."""
        return dict(self._patterns)

    def clear_patterns(self, pattern_type: Optional[str] = None):
        """Clear learned patterns."""
        if pattern_type:
            self._patterns[pattern_type] = []
        else:
            self._patterns = {k: [] for k in self._patterns}

    def get_status(self) -> Dict[str, Any]:
        """Get learning engine status."""
        return {
            "type": "learning_engine",
            "total_interactions": len(self._interaction_log),
            "patterns": {
                k: len(v) for k, v in self._patterns.items()
            },
        }


# Singleton
_learning_engine = None


def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine
