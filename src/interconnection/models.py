from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Phase1Result:
    success: bool = False
    action_type: str = ""
    action_target: str = ""
    device_id: str = ""
    status: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class Phase2Result:
    success: bool = False
    device_id: str = ""
    screen_type: str = ""
    app_name: str = ""
    screen_name: str = ""
    full_text: str = ""
    text_count: int = 0
    ui_elements: int = 0
    classification_confidence: float = 0.0
    classification_reason: str = ""
    filepath: str = ""
    has_memory_record: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class Phase3Result:
    success: bool = False
    knowledge_answer: str = ""
    knowledge_confidence: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)
    documents_retrieved: int = 0
    memory_stored: bool = False
    context_updated: bool = False
    reasoning: str = ""
    suggestions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class AssistantContext:
    current_device_id: str = ""
    current_device_type: str = ""
    current_app: str = ""
    current_screen: str = ""
    current_screen_type: str = ""
    current_chat: str = ""
    current_workflow_id: str = ""
    current_workflow_type: str = ""
    current_knowledge_context: str = ""
    current_goal: str = ""
    current_project: str = ""
    current_documents: List[str] = field(default_factory=list)
    last_command: str = ""
    last_intent: str = ""
    last_target: str = ""
    last_assistant_reply: str = ""
    recent_screens: List[str] = field(default_factory=list)
    recent_apps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class AssistantReply:
    message: str = ""
    success: bool = False
    intent: str = ""
    target: str = ""
    phase1_result: Optional[Phase1Result] = None
    phase2_result: Optional[Phase2Result] = None
    phase3_result: Optional[Phase3Result] = None
    assistant_context: Optional[AssistantContext] = None
    duration_ms: float = 0.0
    suggestions: List[str] = field(default_factory=list)


@dataclass
class UnifiedCommandResult:
    workflow_id: str = ""
    success: bool = False
    intent: str = ""
    target: str = ""
    command: str = ""
    status: str = ""
    assistant_reply: str = ""
    phase1: Optional[Phase1Result] = None
    phase2: Optional[Phase2Result] = None
    phase3: Optional[Phase3Result] = None
    context: Optional[AssistantContext] = None
    duration_ms: float = 0.0
