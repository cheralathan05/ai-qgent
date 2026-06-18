"""Visual Navigation Engine: plans and executes multi-step navigation across screens."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from screen_memory import get_screen_memory, ScreenSnapshot
from app_knowledge import get_app_knowledge
from visual_understanding import get_visual_understanding, ScreenType, DetectedElement

logger = logging.getLogger(__name__)


class NavigationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NavigationStep:
    action: str
    target: str
    description: str = ""
    status: NavigationStatus = NavigationStatus.PENDING
    result: Optional[Dict[str, Any]] = None


@dataclass
class NavigationPlan:
    goal: str
    steps: List[NavigationStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    total_steps: int = 0


class NavigationEngine:
    """Plans and executes visual navigation across app screens."""

    def __init__(self):
        self.screen_memory = get_screen_memory()
        self.app_knowledge = get_app_knowledge()
        self.visual_understanding = get_visual_understanding()

    def create_workflow_steps(self, intent_result) -> List[Dict[str, Any]]:
        intent = intent_result.intent.value
        slots = intent_result.slots
        steps = []

        if intent == "open_app":
            app = slots.get("app")
            if app:
                steps.append({"type": "launch_app", "app": app, "description": f"Launch {app}"})
                steps.append({"type": "verify_app", "app": app, "description": f"Verify {app} opened"})

        elif intent == "send_message":
            recipient = slots.get("recipient")
            message = slots.get("message")
            app = slots.get("app") or "whatsapp"

            if recipient and message:
                steps.append({"type": "launch_app", "app": app, "description": f"Open {app}"})
                steps.append({"type": "navigate_to_chat", "recipient": recipient, "app": app, "description": f"Find {recipient} in {app}"})
                steps.append({"type": "type_message", "message": message, "description": f"Type message"})
                steps.append({"type": "send_message", "description": "Send message"})
                steps.append({"type": "verify_sent", "description": "Verify message sent"})

        elif intent == "navigate":
            target = slots.get("target")
            app = slots.get("app")
            if target and app:
                steps.append({"type": "launch_app", "app": app, "description": f"Open {app}"})
                steps.append({"type": "navigate", "target": target, "app": app, "description": f"Navigate to {target}"})

        elif intent == "get_info":
            target = slots.get("target")
            if target == "battery":
                steps.append({"type": "get_battery", "description": "Get battery level"})
            elif target == "foreground_app":
                steps.append({"type": "get_foreground_app", "description": "Get current app"})
            else:
                steps.append({"type": "get_screenshot", "description": "Take screenshot"})

        elif intent == "search":
            query = slots.get("query")
            app = slots.get("app") or "chrome"
            if query:
                steps.append({"type": "launch_app", "app": app, "description": f"Open {app}"})
                steps.append({"type": "search", "query": query, "description": f"Search for {query}"})

        return steps

    def plan_navigation(self, goal: str, app_name: str, target_screen: str) -> NavigationPlan:
        steps = []
        known_workflow = self.app_knowledge.resolve_workflow(app_name, goal)
        if known_workflow:
            for i, step in enumerate(known_workflow):
                steps.append(NavigationStep(
                    action=step.get("action", "unknown"),
                    target=step.get("target", ""),
                    description=step.get("description") or f"Step {i+1}: {step.get('action', 'unknown')}",
                ))
        else:
            current = self.screen_memory.get_current_screen(app_name)
            if current:
                path = self.app_knowledge.get_navigation_path(app_name, current.screen_name, target_screen)
                if path:
                    for i, step in enumerate(path.steps):
                        steps.append(NavigationStep(
                            action=step.get("action", "click"),
                            target=step.get("target", ""),
                            description=f"Navigate: {step.get('action')} {step.get('target')}",
                        ))

            if not steps:
                steps.append(NavigationStep(
                    action="open_app",
                    target=app_name,
                    description=f"Open {app_name}",
                ))

        return NavigationPlan(goal=goal, steps=steps, total_steps=len(steps))

    def update_screen_context(self, device_id: str, app_name: str, screen_name: str, text_content: str = "", elements: Optional[List[DetectedElement]] = None) -> None:
        snapshot = ScreenSnapshot(
            device_id=device_id,
            screen_name=screen_name,
            app_name=app_name,
            text_content=text_content,
            elements=[e.__dict__ if hasattr(e, "__dict__") else {"type": e.element_type, "text": e.text} for e in (elements or [])],
        )
        self.screen_memory.record_screen(device_id, snapshot)

    def get_context_summary(self, device_id: str) -> Dict[str, Any]:
        current = self.screen_memory.get_current_screen(device_id)
        previous = self.screen_memory.get_previous_screen(device_id)
        history = self.screen_memory.get_navigation_history(device_id)
        changes = self.screen_memory.get_screen_changes(device_id)

        return {
            "current_screen": current.to_dict() if current else None,
            "previous_screen": previous.to_dict() if previous else None,
            "history_count": len(history),
            "recent_changes": changes[-5:] if changes else [],
        }


_navigation_engine: Optional[NavigationEngine] = None


def get_navigation_engine() -> NavigationEngine:
    global _navigation_engine
    if _navigation_engine is None:
        _navigation_engine = NavigationEngine()
    return _navigation_engine
