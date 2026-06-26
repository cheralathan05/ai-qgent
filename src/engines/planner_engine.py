import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from .models import AgenticAction, PerceivedState, ActionType
from services.ollama_service import get_ollama_service

logger = logging.getLogger(__name__)

class AgenticPlanner:
    """
    Reasoning core that decides the next action based on the goal and current state.
    """
    def __init__(self):
        self.ollama = get_ollama_service()

    async def plan_next_action(self, goal: str, state: PerceivedState) -> Optional[AgenticAction]:
        """
        Decides the next action to take to achieve the goal.
        Returns None if the goal is already reached.
        """

        # 1. Construct the prompt for the LLM
        prompt = self._build_prompt(goal, state)

        try:
            # 2. Get response from LLM
            response = await self.ollama.chat(prompt)

            # 3. Parse response into AgenticAction
            action = self._parse_response(response)

            if action is None:
                logger.warning(f"Planner could not determine a valid action for goal: {goal}")
                return None

            logger.info(f"Planned next action: {action.action_type} on {action.target}")
            return action

        except Exception as e:
            logger.exception(f"Planning failed: {e}")
            return None

    def _build_prompt(self, goal: str, state: PerceivedState) -> str:
        """
        Builds a detailed prompt including the current perceived state of the device.
        """
        elements_desc = "\n".join([
            f"- {el.label} (type: {el.element_type}, source: {el.source}, bbox: {el.bbox})"
            for el in state.elements
        ])

        prompt = f"""
You are an Android Device Agent. Your goal is to execute a user's request by interacting with the UI.

USER GOAL: {goal}

CURRENT DEVICE STATE:
- App: {state.current_app}
- Screen Type: {state.screen_type}
- Visible Elements:
{elements_desc}

Full Screen Text: {state.full_text}

INSTRUCTIONS:
1. Analyze the current state.
2. If the goal is already achieved (e.g., you are on the target screen and the message is sent), respond with 'GOAL_REACHED'.
3. Otherwise, determine the SINGLE next best action to take.
4. Output your decision as a JSON object with the following keys:
   - 'action_type': One of ['tap', 'type', 'scroll', 'swipe', 'back', 'home', 'open_app']
   - 'target': The label of the element to interact with, or the app name if action_type is 'open_app'.
   - 'params': A dictionary of parameters (e.g., {{'text': 'Hello world'}} for 'type' or {{'direction': 'down'}} for 'scroll').
   - 'description': A brief explanation of why this action is the next step.

Example Output:
{{
  "action_type": "tap",
  "target": "Search",
  "params": {{}},
  "description": "Tapping the search button to find the contact"
}}

Response:
"""
        return prompt

    def _parse_response(self, response: str) -> Optional[AgenticAction]:
        """
        Parses the LLM response into an AgenticAction.
        """
        if "GOAL_REACHED" in response.upper():
            return None

        try:
            # Extract JSON from response (handling potential markdown wrappers)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            return AgenticAction(
                action_type=ActionType(data["action_type"]),
                target=data["target"],
                params=data.get("params", {}),
                description=data.get("description", "")
            )
        except Exception as e:
            logger.error(f"Failed to parse planner response: {e}. Response was: {response}")
            return None

def get_planner_engine() -> AgenticPlanner:
    return AgenticPlanner()
