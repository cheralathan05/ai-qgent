from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

class ActionType(Enum):
    TAP = "tap"
    TYPE = "type"
    SCROLL = "scroll"
    SWIPE = "swipe"
    BACK = "back"
    HOME = "home"
    RECENT_APPS = "recent_apps"
    WAIT = "wait"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"

@dataclass
class VisualElement:
    label: str
    bbox: List[float]  # [x, y, w, h]
    confidence: float
    element_type: str  # button, input, text, etc.
    source: str  # "yolo", "ocr", "accessibility"
    accessibility_id: Optional[str] = None
    content_description: Optional[str] = None

@dataclass
class PerceivedState:
    """A comprehensive snapshot of the device state."""
    device_id: str
    current_app: Optional[str] = None
    current_activity: Optional[str] = None
    screen_type: str = "unknown"
    elements: List[VisualElement] = field(default_factory=list)
    full_text: str = ""
    confidence: float = 0.0
    timestamp: float = 0.0

@dataclass
class AgenticAction:
    """An abstract action for the agent to perform."""
    action_type: ActionType
    target: str  # Semantic label or coordinates
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

@dataclass
class ActionOutcome:
    """The result of executing an AgenticAction."""
    action: AgenticAction
    success: bool
    state_before: PerceivedState
    state_after: PerceivedState
    error: Optional[str] = None
    verification_result: Optional[bool] = None
