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
            if not app:
                return [{"step": 1, "type": "unknown", "description": "No app specified to open"}]
            pretty_app = str(app).replace("_", " ").title()
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "launch_app", "description": f"Opening {pretty_app}", "app": app},
                {"step": 3, "type": "verify", "description": f"Confirming {pretty_app} is open", "app": app},
            ]

        elif intent == "close_app":
            app = slots.get("app")
            if not app:
                return [{"step": 1, "type": "unknown", "description": "No app specified to close"}]
            pretty_app = str(app).replace("_", " ").title()
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "close_app", "description": f"Closing {pretty_app}", "app": app},
                {"step": 3, "type": "verify", "description": f"Confirming {pretty_app} is closed", "app": app},
            ]

        elif intent == "send_message":
            recipient = slots.get("recipient")
            message = slots.get("message")
            steps = [{"step": 1, "type": "check_device", "description": "Preparing your device"}]
            app = slots.get("app", "whatsapp")
            pretty_app = str(app).replace("_", " ").title()
            pretty_recip = str(recipient).title() if recipient else "your contact"
            steps.append({
                "step": 2, "type": "open_chat",
                "description": f"Opening {pretty_app} chat with {pretty_recip}",
                "app": app, "recipient": recipient,
            })
            if message:
                steps.append({
                    "step": 3, "type": "type_text",
                    "description": f"Typing your message",
                    "text": message,
                })
                steps.append({
                    "step": 4, "type": "send_message",
                    "description": "Sending the message",
                })
            steps.append({
                "step": len(steps) + 1, "type": "verify",
                "description": "Confirming message sent",
            })

        elif intent == "call_contact":
            recipient = slots.get("recipient")
            pretty_recip = str(recipient).title() if recipient else "your contact"
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "make_call", "description": f"Calling {pretty_recip}", "recipient": recipient},
                {"step": 3, "type": "verify", "description": "Confirming call initiated"},
            ]

        elif intent == "open_chat":
            recipient = slots.get("recipient")
            app = slots.get("app", "instagram")
            pretty_app = str(app).replace("_", " ").title()
            pretty_recip = str(recipient).title() if recipient else "your contact"
            chat_desc = f"Opening {pretty_recip} chat"
            if app:
                chat_desc = f"Opening {pretty_app} chat with {pretty_recip}"
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "open_chat", "description": chat_desc, "app": app, "recipient": recipient},
                {"step": 3, "type": "verify", "description": "Confirming chat opened"},
            ]

        elif intent == "search":
            query = slots.get("query")
            app = slots.get("app")
            steps = [{"step": 1, "type": "check_device", "description": "Preparing your device"}]
            if app and app != "web":
                pretty_app = str(app).replace("_", " ").title()
                steps.append({
                    "step": 2, "type": "launch_app",
                    "description": f"Opening {pretty_app}", "app": app,
                })
                steps.append({
                    "step": 3, "type": "type_text",
                    "description": f"Searching for {query}", "text": query,
                })
            else:
                steps.append({
                    "step": 2, "type": "web_search",
                    "description": f"Searching for {query}", "query": query,
                })
            steps.append({"step": len(steps) + 1, "type": "verify", "description": "Confirming search results"})

        elif intent == "web_search":
            query = slots.get("query")
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "web_search", "description": f"Searching for {query}", "query": query},
                {"step": 3, "type": "verify", "description": "Confirming search results"},
            ]

        elif intent == "battery_status":
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "check_battery", "description": "Reading battery level"},
            ]

        elif intent == "foreground_app":
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "check_foreground_app", "description": "Detecting current app"},
            ]

        elif intent == "take_screenshot":
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "take_screenshot", "description": "Capturing screen"},
            ]

        elif intent == "open_settings":
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "launch_app", "description": "Opening Settings", "app": "settings"},
                {"step": 3, "type": "verify", "description": "Confirming Settings opened"},
            ]

        elif intent == "open_folder":
            folder = slots.get("folder", "downloads")
            pretty_folder = str(folder).replace("_", " ").title()
            steps = [
                {"step": 1, "type": "check_device", "description": "Preparing your device"},
                {"step": 2, "type": "open_folder", "description": f"Opening {pretty_folder} folder", "folder": folder},
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
