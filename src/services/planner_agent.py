"""Planner agent that converts intent results into executable workflow steps."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Generates ordered workflow steps from intent results."""

    def plan(self, intent_result) -> List[Dict[str, Any]]:
        intent = intent_result.intent.value if hasattr(intent_result.intent, 'value') else str(intent_result.intent)
        slots = intent_result.slots if hasattr(intent_result, 'slots') else {}
        steps: List[Dict[str, Any]] = []

        if intent == "open_app":
            app = slots.get("app")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "launch_app", "description": f"Open {app}", "app": app},
                {"step": 3, "type": "verify", "description": f"Verify {app} opened", "app": app},
            ]

        elif intent == "close_app":
            app = slots.get("app")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "close_app", "description": f"Close {app}", "app": app},
                {"step": 3, "type": "verify", "description": f"Verify {app} closed", "app": app},
            ]

        elif intent == "send_message":
            recipient = slots.get("recipient")
            message = slots.get("message")
            steps = [{"step": 1, "type": "check_device", "description": "Check device is ready"}]
            app = slots.get("app", "whatsapp")
            steps.append({
                "step": 2, "type": "open_chat",
                "description": f"Open {app} chat with {recipient}",
                "app": app, "recipient": recipient,
            })
            if message:
                steps.append({
                    "step": 3, "type": "type_text",
                    "description": f"Type message: {message}",
                    "text": message,
                })
                steps.append({
                    "step": 4, "type": "send_message",
                    "description": "Send the message",
                })
            steps.append({
                "step": len(steps) + 1, "type": "verify",
                "description": "Verify message sent",
            })

        elif intent == "call_contact":
            recipient = slots.get("recipient")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "make_call", "description": f"Call {recipient}", "recipient": recipient},
                {"step": 3, "type": "verify", "description": "Verify call initiated"},
            ]

        elif intent == "open_chat":
            recipient = slots.get("recipient")
            app = slots.get("app", "instagram")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "open_chat", "description": f"Open {app} chat with {recipient}", "app": app, "recipient": recipient},
                {"step": 3, "type": "verify", "description": "Verify chat opened"},
            ]

        elif intent == "search":
            query = slots.get("query")
            app = slots.get("app")
            steps = [{"step": 1, "type": "check_device", "description": "Check device is ready"}]
            if app and app != "web":
                steps.append({
                    "step": 2, "type": "launch_app",
                    "description": f"Open {app}", "app": app,
                })
                steps.append({
                    "step": 3, "type": "type_text",
                    "description": f"Search for {query}", "text": query,
                })
            else:
                steps.append({
                    "step": 2, "type": "web_search",
                    "description": f"Search web for {query}", "query": query,
                })
            steps.append({"step": len(steps) + 1, "type": "verify", "description": "Verify search completed"})

        elif intent == "web_search":
            query = slots.get("query")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "web_search", "description": f"Search web for {query}", "query": query},
                {"step": 3, "type": "verify", "description": "Verify search completed"},
            ]

        elif intent == "battery_status":
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "check_battery", "description": "Read battery level"},
            ]

        elif intent == "foreground_app":
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "check_foreground_app", "description": "Read foreground app"},
            ]

        elif intent == "take_screenshot":
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "take_screenshot", "description": "Capture screen"},
            ]

        elif intent == "open_settings":
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "launch_app", "description": "Open Settings", "app": "settings"},
                {"step": 3, "type": "verify", "description": "Verify Settings opened"},
            ]

        elif intent == "open_folder":
            folder = slots.get("folder", "downloads")
            steps = [
                {"step": 1, "type": "check_device", "description": "Check device is ready"},
                {"step": 2, "type": "open_folder", "description": f"Open {folder} folder", "folder": folder},
            ]

        else:
            steps = [{"step": 1, "type": "unknown", "description": f"Unrecognized command: {intent}"}]

        return steps


planner_agent = None


def get_planner_agent() -> PlannerAgent:
    global planner_agent
    if planner_agent is None:
        planner_agent = PlannerAgent()
    return planner_agent
