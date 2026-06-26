"""Navigation Agent - Universal app navigation with no hardcoded coordinates.

Plans navigation steps based on actual screen state, not hardcoded positions.
Works across WhatsApp, Telegram, Instagram, Discord, LinkedIn, Messenger, etc.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NavigationAction(str, Enum):
    TAP = "tap"
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    SWIPE = "swipe"
    OPEN_APP = "open_app"


@dataclass
class NavigationStep:
    action: NavigationAction
    target: str = ""
    x: int = 0
    y: int = 0
    text: str = ""
    keycode: str = ""
    duration: float = 0.5
    description: str = ""
    confidence: float = 1.0
    verify_state: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "target": self.target,
            "x": self.x, "y": self.y,
            "text": self.text,
            "keycode": self.keycode,
            "duration": self.duration,
            "description": self.description,
            "confidence": self.confidence,
        }


@dataclass
class NavigationPlan:
    goal: str
    app_name: str
    steps: List[NavigationStep] = field(default_factory=list)
    total_steps: int = 0
    confidence: float = 0.0
    estimated_time_seconds: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "app_name": self.app_name,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": self.total_steps,
            "confidence": self.confidence,
            "estimated_time_seconds": self.estimated_time_seconds,
        }


class NavigationAgent:
    """Universal navigation agent that plans steps based on screen state.

    No hardcoded coordinates - uses detected elements from VisionAgent.
    """

    # App-specific screen mappings
    APP_SCREENS = {
        "whatsapp": {
            "inbox": {"indicators": ["chats", "calls", "status"], "search_position": "top_right"},
            "chat": {"indicators": ["type a message", "send"], "input_position": "bottom"},
            "status": {"indicators": ["my status", "recent updates"]},
        },
        "instagram": {
            "dm": {"indicators": ["direct", "inbox", "message"], "search_position": "top_right"},
            "dm_chat": {"indicators": ["message", "type a message", "send"], "input_position": "bottom"},
            "feed": {"indicators": ["home", "feed", "like", "comment"]},
        },
        "telegram": {
            "inbox": {"indicators": ["chats", "contacts"], "search_position": "top_right"},
            "chat": {"indicators": ["message", "send"], "input_position": "bottom"},
        },
        "discord": {
            "channels": {"indicators": ["channels", "server"], "search_position": "top"},
            "chat": {"indicators": ["message", "send"], "input_position": "bottom"},
        },
        "linkedin": {
            "feed": {"indicators": ["feed", "network", "jobs"], "search_position": "top"},
            "messaging": {"indicators": ["messaging", "message"], "search_position": "top"},
        },
        "messenger": {
            "inbox": {"indicators": ["chats", "people"], "search_position": "top"},
            "chat": {"indicators": ["message", "send"], "input_position": "bottom"},
        },
    }

    def _is_chat_screen(self, screen_type: str) -> bool:
        """Check if the current screen type indicates an active chat."""
        chat_screens = [
            "whatsapp_chat", "telegram_chat", "instagram_dm_chat",
            "discord_chat", "messenger_chat",
        ]
        return screen_type.lower() in chat_screens if screen_type else False

    def plan_send_message(
        self,
        app_name: str,
        recipient: str,
        message: str,
        current_screen_type: str = "",
        current_app: str = "",
    ) -> NavigationPlan:
        """Plan message sending steps based on current screen state.

        Intelligently adapts - if already in a chat screen, skips search/navigation
        and goes directly to typing and sending.
        """
        steps = []
        already_in_chat = self._is_chat_screen(current_screen_type)

        if already_in_chat:
            # Already in a chat screen - just type and send
            confidence = 0.9
            logger.info(f"Already in chat screen ({current_screen_type}), skipping navigation")

            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="input_field",
                description="Tap message input field",
                confidence=0.9,
            ))
            steps.append(NavigationStep(
                action=NavigationAction.TYPE_TEXT,
                text=message,
                description=f"Type message: {message[:30]}...",
                confidence=0.95,
            ))
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=0.5,
                description="Wait for typing",
                confidence=1.0,
            ))
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="send_button",
                description="Tap send button",
                confidence=0.9,
                verify_state="message_sent",
            ))
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=1.0,
                description="Wait for send confirmation",
                confidence=1.0,
            ))
        else:
            # Need to navigate to the chat first
            # Step 1: Open app if not already there
            if current_app != app_name:
                steps.append(NavigationStep(
                    action=NavigationAction.OPEN_APP,
                    target=app_name,
                    description=f"Open {app_name}",
                    confidence=0.95,
                ))
                steps.append(NavigationStep(
                    action=NavigationAction.WAIT,
                    duration=2.0,
                    description="Wait for app to load",
                    confidence=1.0,
                ))
                confidence = 0.7
            else:
                confidence = 0.8

            # Step 2: Find and tap search
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="search_bar",
                description=f"Tap search bar to find {recipient}",
                confidence=0.85,
                verify_state="search_open",
            ))

            # Step 3: Type recipient name
            steps.append(NavigationStep(
                action=NavigationAction.TYPE_TEXT,
                text=recipient,
                description=f"Type contact name: {recipient}",
                confidence=0.9,
            ))

            # Step 4: Wait for results
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=1.5,
                description="Wait for search results",
                confidence=1.0,
            ))

            # Step 5: Tap first result
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target=recipient,
                description=f"Tap {recipient} in search results",
                confidence=0.8,
                verify_state="chat_open",
            ))

            # Step 6: Wait for chat to open
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=2.0,
                description="Wait for chat to fully load",
                confidence=1.0,
            ))

            # Step 7: Tap message input
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="input_field",
                description="Tap message input field",
                confidence=0.85,
            ))

            # Step 8: Type message
            steps.append(NavigationStep(
                action=NavigationAction.TYPE_TEXT,
                text=message,
                description=f"Type message: {message[:30]}...",
                confidence=0.9,
            ))

            # Step 9: Wait for typing
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=0.5,
                description="Wait for message to be entered",
                confidence=1.0,
            ))

            # Step 10: Tap send button
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="send_button",
                description="Tap send button",
                confidence=0.85,
                verify_state="message_sent",
            ))

            # Step 11: Wait for send
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=1.0,
                description="Wait for message to be sent",
                confidence=1.0,
            ))

        estimated_time = sum(
            s.duration if s.action == NavigationAction.WAIT else 1.5
            for s in steps
        )

        return NavigationPlan(
            goal=f"Send message to {recipient} on {app_name}",
            app_name=app_name,
            steps=steps,
            total_steps=len(steps),
            confidence=confidence,
            estimated_time_seconds=estimated_time,
        )

    def plan_navigation(
        self,
        target_screen: str,
        app_name: str,
        current_screen_type: str = "",
        current_app: str = "",
    ) -> NavigationPlan:
        """Plan navigation to a target screen."""
        steps = []

        if current_app != app_name:
            steps.append(NavigationStep(
                action=NavigationAction.OPEN_APP,
                target=app_name,
                description=f"Open {app_name}",
                confidence=0.95,
            ))
            steps.append(NavigationStep(
                action=NavigationAction.WAIT,
                duration=2.0,
                description="Wait for app to load",
                confidence=1.0,
            ))

        # Generic navigation: tap on target screen indicators
        app_screens = self.APP_SCREENS.get(app_name, {})
        screen_info = app_screens.get(target_screen, {})

        if screen_info.get("search_position") == "top_right":
            steps.append(NavigationStep(
                action=NavigationAction.TAP,
                target="search_bar",
                description="Tap search in top right",
                confidence=0.8,
            ))

        estimated_time = sum(
            s.duration if s.action == NavigationAction.WAIT else 1.5
            for s in steps
        )

        return NavigationPlan(
            goal=f"Navigate to {target_screen} in {app_name}",
            app_name=app_name,
            steps=steps,
            total_steps=len(steps),
            confidence=0.6,
            estimated_time_seconds=estimated_time,
        )


_navigation_agent: Optional[NavigationAgent] = None


def get_navigation_agent() -> NavigationAgent:
    global _navigation_agent
    if _navigation_agent is None:
        _navigation_agent = NavigationAgent()
    return _navigation_agent
