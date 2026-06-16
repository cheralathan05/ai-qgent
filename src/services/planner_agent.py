"""Planner agent that converts intent results into executable workflows."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Generates ordered workflow steps from intent results."""

    def __init__(self):
        self.package_map = {
            "chrome": "chrome",
            "instagram": "instagram",
            "whatsapp": "whatsapp",
            "youtube": "youtube",
            "maps": "maps",
            "gmail": "gmail",
        }

    def plan(self, intent_result) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []

        if intent_result.intent.value == "open_app":
            app_name = intent_result.slots.get("app") or intent_result.slots.get("target")
            if app_name:
                steps.append({
                    "step": 1,
                    "type": "check_device",
                    "description": f"Check that device is connected and ready.",
                })
                steps.append({
                    "step": 2,
                    "type": "launch_app",
                    "description": f"Launch {app_name} on the device.",
                    "app": app_name,
                })
                steps.append({
                    "step": 3,
                    "type": "verify_app",
                    "description": f"Verify that {app_name} is now in the foreground.",
                    "app": app_name,
                })

        return steps


planner_agent = None


def get_planner_agent() -> PlannerAgent:
    global planner_agent
    if planner_agent is None:
        planner_agent = PlannerAgent()
    return planner_agent
