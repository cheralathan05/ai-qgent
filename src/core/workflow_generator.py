"""
APA-OS Dynamic Workflow Generator

Creates execution workflows on the fly.
No hardcoded workflows. No fixed actions.
Generates steps based on intent and context.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .intent_engine import IntentCategory, IntentResult

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    step_id: int
    step_type: str
    description: str
    phase: str  # phase1, phase2, phase3
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: Optional[int] = None
    verification: Optional[Dict[str, Any]] = None
    retry_on_fail: bool = True
    max_retries: int = 2


@dataclass
class Workflow:
    """A complete execution workflow."""
    workflow_id: str
    intent: IntentCategory
    description: str
    steps: List[WorkflowStep]
    requires_phase1: bool = False
    requires_phase2: bool = False
    requires_phase3: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicWorkflowGenerator:
    """
    Generates workflows dynamically based on intent.
    
    No hardcoded workflows.
    Creates steps based on what the user wants.
    """

    def __init__(self):
        self._step_counter = 0

    def generate(self, intent_result: IntentResult) -> Workflow:
        """Generate a workflow from intent result."""
        self._step_counter = 0
        
        intent = intent_result.intent
        slots = intent_result.slots

        # Route to appropriate workflow builder
        if intent == IntentCategory.OPEN_APP:
            return self._build_open_app(slots)
        elif intent == IntentCategory.CLOSE_APP:
            return self._build_close_app(slots)
        elif intent == IntentCategory.SEND_MESSAGE:
            return self._build_send_message(slots)
        elif intent == IntentCategory.REPLY_MESSAGE:
            return self._build_reply_message(slots)
        elif intent == IntentCategory.OPEN_CHAT:
            return self._build_open_chat(slots)
        elif intent == IntentCategory.CALL_CONTACT:
            return self._build_call(slots)
        elif intent == IntentCategory.SEND_EMAIL:
            return self._build_send_email(slots)
        elif intent == IntentCategory.BATTERY_STATUS:
            return self._build_battery()
        elif intent == IntentCategory.DEVICE_STATUS:
            return self._build_device_status()
        elif intent == IntentCategory.FOREGROUND_APP:
            return self._build_foreground_app()
        elif intent == IntentCategory.TAKE_SCREENSHOT:
            return self._build_screenshot()
        elif intent == IntentCategory.READ_NOTIFICATIONS:
            return self._build_notifications()
        elif intent == IntentCategory.WEB_SEARCH:
            return self._build_web_search(slots)
        elif intent == IntentCategory.IN_APP_SEARCH:
            return self._build_in_app_search(slots)
        elif intent == IntentCategory.FIND_FILE:
            return self._build_find_file(slots)
        elif intent == IntentCategory.OPEN_FILE:
            return self._build_open_file(slots)
        elif intent == IntentCategory.SEARCH_FILES:
            return self._build_search_files(slots)
        elif intent == IntentCategory.SUMMARIZE:
            return self._build_summarize(slots)
        elif intent == IntentCategory.EXPLAIN:
            return self._build_explain(slots)
        elif intent == IntentCategory.GENERATE_ASSIGNMENT:
            return self._build_generate_assignment(slots)
        elif intent == IntentCategory.GENERATE_MCQ:
            return self._build_generate_mcq(slots)
        elif intent == IntentCategory.GENERATE_QUESTIONS:
            return self._build_generate_questions(slots)
        elif intent == IntentCategory.GENERATE_NOTES:
            return self._build_generate_notes(slots)
        elif intent == IntentCategory.FIND_KNOWLEDGE:
            return self._build_find_knowledge(slots)
        elif intent == IntentCategory.GO_BACK:
            return self._build_go_back()
        elif intent == IntentCategory.GO_HOME:
            return self._build_go_home()
        elif intent == IntentCategory.SCROLL:
            return self._build_scroll(slots)
        elif intent == IntentCategory.OPEN_CAMERA:
            return self._build_open_camera()
        elif intent == IntentCategory.PLAY_MUSIC:
            return self._build_play_music(slots)
        elif intent == IntentCategory.OPEN_SETTINGS:
            return self._build_open_settings()
        elif intent == IntentCategory.TOGGLE_WIFI:
            return self._build_toggle_wifi(slots)
        elif intent == IntentCategory.TOGGLE_BLUETOOTH:
            return self._build_toggle_bluetooth(slots)
        elif intent == IntentCategory.TOGGLE_FLASHLIGHT:
            return self._build_toggle_flashlight(slots)
        elif intent == IntentCategory.VOLUME_CONTROL:
            return self._build_volume(slots)
        elif intent == IntentCategory.LOCK_DEVICE:
            return self._build_lock_device()
        elif intent == IntentCategory.CREATE_REMINDER:
            return self._build_reminder(slots)
        elif intent == IntentCategory.SCHEDULE_EVENT:
            return self._build_schedule_event(slots)
        elif intent == IntentCategory.SET_ALARM:
            return self._build_alarm(slots)
        elif intent == IntentCategory.COMPOUND_ACTION:
            return self._build_compound(intent_result)
        else:
            return self._build_unknown(intent_result)

    def _next_step(self) -> int:
        self._step_counter += 1
        return self._step_counter

    # ========== DEVICE CONTROL WORKFLOWS ==========

    def _build_open_app(self, slots: Dict[str, Any]) -> Workflow:
        app = slots.get("app", "unknown")
        steps = [
            WorkflowStep(
                step_id=self._next_step(),
                step_type="resolve_package",
                description=f"Resolve package for {app}",
                phase="phase1",
                action="resolve_package",
                params={"app_name": app},
                verification={"type": "package_found"},
            ),
            WorkflowStep(
                step_id=self._next_step(),
                step_type="launch_app",
                description=f"Launch {app}",
                phase="phase1",
                action="launch_app",
                params={"app_name": app},
                depends_on=self._step_counter - 1,
                verification={"type": "foreground_app", "expected": app},
            ),
        ]
        return Workflow(
            workflow_id=f"wf_open_{app}",
            intent=IntentCategory.OPEN_APP,
            description=f"Open {app}",
            steps=steps,
            requires_phase1=True,
            metadata={"app": app},
        )

    def _build_close_app(self, slots: Dict[str, Any]) -> Workflow:
        app = slots.get("app", "unknown")
        steps = [
            WorkflowStep(
                step_id=self._next_step(),
                step_type="force_stop",
                description=f"Close {app}",
                phase="phase1",
                action="force_stop",
                params={"app_name": app},
                verification={"type": "app_closed", "app": app},
            ),
        ]
        return Workflow(
            workflow_id=f"wf_close_{app}",
            intent=IntentCategory.CLOSE_APP,
            description=f"Close {app}",
            steps=steps,
            requires_phase1=True,
        )

    def _build_send_message(self, slots: Dict[str, Any]) -> Workflow:
        recipient = slots.get("recipient", "unknown")
        message = slots.get("message", "")
        app = slots.get("app", "whatsapp")
        steps = [
            WorkflowStep(
                step_id=self._next_step(),
                step_type="resolve_contact",
                description=f"Find contact {recipient}",
                phase="phase1",
                action="resolve_contact",
                params={"contact_name": recipient},
            ),
            WorkflowStep(
                step_id=self._next_step(),
                step_type="launch_app",
                description=f"Open {app}",
                phase="phase1",
                action="launch_app",
                params={"app_name": app},
                verification={"type": "foreground_app", "expected": app},
            ),
            WorkflowStep(
                step_id=self._next_step(),
                step_type="open_chat",
                description=f"Open chat with {recipient}",
                phase="phase2",
                action="navigate_to_chat",
                params={"contact": recipient, "app": app},
                verification={"type": "chat_opened", "contact": recipient},
            ),
        ]
        if message:
            steps.append(WorkflowStep(
                step_id=self._next_step(),
                step_type="type_message",
                description="Type message",
                phase="phase1",
                action="input_text",
                params={"text": message},
            ))
            steps.append(WorkflowStep(
                step_id=self._next_step(),
                step_type="send_message",
                description="Send message",
                phase="phase1",
                action="press_key",
                params={"keycode": 66},  # Enter
                verification={"type": "message_sent", "text": message},
            ))
        return Workflow(
            workflow_id=f"wf_msg_{recipient}",
            intent=IntentCategory.SEND_MESSAGE,
            description=f"Send message to {recipient}",
            steps=steps,
            requires_phase1=True,
            requires_phase2=True,
            metadata={"recipient": recipient, "message": message, "app": app},
        )

    def _build_reply_message(self, slots: Dict[str, Any]) -> Workflow:
        message = slots.get("message", "")
        steps = [
            WorkflowStep(
                step_id=self._next_step(),
                step_type="detect_chat",
                description="Detect current chat",
                phase="phase2",
                action="detect_current_chat",
                verification={"type": "chat_detected"},
            ),
        ]
        if message:
            steps.extend([
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="type_message",
                    description="Type reply",
                    phase="phase1",
                    action="input_text",
                    params={"text": message},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="send_message",
                    description="Send reply",
                    phase="phase1",
                    action="press_key",
                    params={"keycode": 66},
                    verification={"type": "message_sent"},
                ),
            ])
        return Workflow(
            workflow_id="wf_reply",
            intent=IntentCategory.REPLY_MESSAGE,
            description="Reply to message",
            steps=steps,
            requires_phase1=True,
            requires_phase2=True,
        )

    def _build_open_chat(self, slots: Dict[str, Any]) -> Workflow:
        contact = slots.get("recipient", "unknown")
        app = slots.get("app", "whatsapp")
        return Workflow(
            workflow_id=f"wf_chat_{contact}",
            intent=IntentCategory.OPEN_CHAT,
            description=f"Open chat with {contact}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description=f"Open {app}",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": app},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="open_chat",
                    description=f"Open chat with {contact}",
                    phase="phase2",
                    action="navigate_to_chat",
                    params={"contact": contact, "app": app},
                    verification={"type": "chat_opened", "contact": contact},
                ),
            ],
            requires_phase1=True,
            requires_phase2=True,
        )

    def _build_call(self, slots: Dict[str, Any]) -> Workflow:
        contact = slots.get("recipient", "unknown")
        return Workflow(
            workflow_id=f"wf_call_{contact}",
            intent=IntentCategory.CALL_CONTACT,
            description=f"Call {contact}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="resolve_contact",
                    description=f"Find {contact}'s phone number",
                    phase="phase1",
                    action="resolve_contact",
                    params={"contact_name": contact},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="make_call",
                    description=f"Calling {contact}",
                    phase="phase1",
                    action="dial_number",
                    params={"contact": contact},
                    verification={"type": "call_initiated"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_send_email(self, slots: Dict[str, Any]) -> Workflow:
        recipient = slots.get("recipient", "unknown")
        return Workflow(
            workflow_id=f"wf_email_{recipient}",
            intent=IntentCategory.SEND_EMAIL,
            description=f"Send email to {recipient}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description="Open Gmail",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "gmail"},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="compose_email",
                    description="Compose email",
                    phase="phase2",
                    action="tap_compose",
                    verification={"type": "compose_opened"},
                ),
            ],
            requires_phase1=True,
            requires_phase2=True,
        )

    def _build_battery(self) -> Workflow:
        return Workflow(
            workflow_id="wf_battery",
            intent=IntentCategory.BATTERY_STATUS,
            description="Check battery level",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="check_battery",
                    description="Read battery level",
                    phase="phase1",
                    action="get_battery",
                    verification={"type": "battery_read"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_device_status(self) -> Workflow:
        return Workflow(
            workflow_id="wf_status",
            intent=IntentCategory.DEVICE_STATUS,
            description="Get device status",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="device_status",
                    description="Read device status",
                    phase="phase1",
                    action="get_device_status",
                ),
            ],
            requires_phase1=True,
        )

    def _build_foreground_app(self) -> Workflow:
        return Workflow(
            workflow_id="wf_fg_app",
            intent=IntentCategory.FOREGROUND_APP,
            description="Get current app",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="foreground_app",
                    description="Detect foreground app",
                    phase="phase1",
                    action="get_foreground_app",
                ),
            ],
            requires_phase1=True,
        )

    def _build_screenshot(self) -> Workflow:
        return Workflow(
            workflow_id="wf_screenshot",
            intent=IntentCategory.TAKE_SCREENSHOT,
            description="Take screenshot",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="screenshot",
                    description="Capture screen",
                    phase="phase1",
                    action="take_screenshot",
                    verification={"type": "screenshot_taken"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_notifications(self) -> Workflow:
        return Workflow(
            workflow_id="wf_notifications",
            intent=IntentCategory.READ_NOTIFICATIONS,
            description="Read notifications",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="read_notifications",
                    description="Read notification bar",
                    phase="phase1",
                    action="read_notifications",
                ),
            ],
            requires_phase1=True,
        )

    # ========== SEARCH WORKFLOWS ==========

    def _build_web_search(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("query", "")
        return Workflow(
            workflow_id=f"wf_search_{query[:20]}",
            intent=IntentCategory.WEB_SEARCH,
            description=f"Search: {query}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="open_browser",
                    description="Open Chrome",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "chrome"},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="navigate_url",
                    description=f"Search for {query}",
                    phase="phase1",
                    action="open_url",
                    params={"url": f"https://www.google.com/search?q={query}"},
                    verification={"type": "search_results"},
                ),
            ],
            requires_phase1=True,
            metadata={"query": query},
        )

    def _build_in_app_search(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("query", "")
        app = slots.get("app", "unknown")
        return Workflow(
            workflow_id=f"wf_inapp_{app}",
            intent=IntentCategory.IN_APP_SEARCH,
            description=f"Search {query} in {app}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description=f"Open {app}",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": app},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="find_search",
                    description="Find search bar",
                    phase="phase2",
                    action="find_element",
                    params={"element_type": "search_bar"},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="type_query",
                    description=f"Type {query}",
                    phase="phase1",
                    action="input_text",
                    params={"text": query},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="submit_search",
                    description="Submit search",
                    phase="phase1",
                    action="press_key",
                    params={"keycode": 66},
                    verification={"type": "search_results"},
                ),
            ],
            requires_phase1=True,
            requires_phase2=True,
        )

    # ========== FILE WORKFLOWS ==========

    def _build_find_file(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("file") or slots.get("query", "unknown")
        return Workflow(
            workflow_id=f"wf_find_{query[:20]}",
            intent=IntentCategory.FIND_FILE,
            description=f"Find file: {query}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="search_knowledge",
                    description=f"Search for {query}",
                    phase="phase3",
                    action="search_files",
                    params={"query": query},
                    verification={"type": "file_found"},
                ),
            ],
            requires_phase3=True,
            metadata={"query": query},
        )

    def _build_open_file(self, slots: Dict[str, Any]) -> Workflow:
        filename = slots.get("file", "unknown")
        return Workflow(
            workflow_id=f"wf_openfile_{filename[:20]}",
            intent=IntentCategory.OPEN_FILE,
            description=f"Open file: {filename}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="find_file",
                    description=f"Find {filename}",
                    phase="phase3",
                    action="search_files",
                    params={"query": filename},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="open_file",
                    description="Open file",
                    phase="phase1",
                    action="open_file",
                    params={"filename": filename},
                    verification={"type": "file_opened"},
                ),
            ],
            requires_phase1=True,
            requires_phase3=True,
        )

    def _build_search_files(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("query", "unknown")
        return Workflow(
            workflow_id=f"wf_searchfiles_{query[:20]}",
            intent=IntentCategory.SEARCH_FILES,
            description=f"Search files: {query}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="search_files",
                    description=f"Find files about {query}",
                    phase="phase3",
                    action="search_files",
                    params={"query": query},
                ),
            ],
            requires_phase3=True,
        )

    # ========== KNOWLEDGE WORKFLOWS ==========

    def _build_summarize(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query") or slots.get("file", "unknown")
        return Workflow(
            workflow_id=f"wf_summary_{topic[:20]}",
            intent=IntentCategory.SUMMARIZE,
            description=f"Summarize: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_content",
                    description=f"Retrieve {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_summary",
                    description="Generate summary",
                    phase="phase3",
                    action="generate_summary",
                    params={"topic": topic},
                ),
            ],
            requires_phase3=True,
        )

    def _build_explain(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query", "unknown")
        return Workflow(
            workflow_id=f"wf_explain_{topic[:20]}",
            intent=IntentCategory.EXPLAIN,
            description=f"Explain: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_knowledge",
                    description=f"Find info about {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_explanation",
                    description="Generate explanation",
                    phase="phase3",
                    action="generate_explanation",
                    params={"topic": topic},
                ),
            ],
            requires_phase3=True,
        )

    def _build_generate_assignment(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query") or slots.get("file", "unknown")
        return Workflow(
            workflow_id=f"wf_assign_{topic[:20]}",
            intent=IntentCategory.GENERATE_ASSIGNMENT,
            description=f"Generate assignment: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_notes",
                    description=f"Retrieve notes on {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_assignment",
                    description="Generate assignment",
                    phase="phase3",
                    action="generate_assignment",
                    params={"topic": topic},
                ),
            ],
            requires_phase3=True,
        )

    def _build_generate_mcq(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query", "unknown")
        count = slots.get("count", "10")
        return Workflow(
            workflow_id=f"wf_mcq_{topic[:20]}",
            intent=IntentCategory.GENERATE_MCQ,
            description=f"Generate {count} MCQs: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_notes",
                    description=f"Retrieve notes on {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_mcq",
                    description=f"Generate {count} MCQs",
                    phase="phase3",
                    action="generate_mcq",
                    params={"topic": topic, "count": count},
                ),
            ],
            requires_phase3=True,
        )

    def _build_generate_questions(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query", "unknown")
        count = slots.get("count", "20")
        return Workflow(
            workflow_id=f"wf_questions_{topic[:20]}",
            intent=IntentCategory.GENERATE_QUESTIONS,
            description=f"Generate {count} questions: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_notes",
                    description=f"Retrieve notes on {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_questions",
                    description=f"Generate {count} questions",
                    phase="phase3",
                    action="generate_questions",
                    params={"topic": topic, "count": count},
                ),
            ],
            requires_phase3=True,
        )

    def _build_generate_notes(self, slots: Dict[str, Any]) -> Workflow:
        topic = slots.get("query") or slots.get("file", "unknown")
        return Workflow(
            workflow_id=f"wf_notes_{topic[:20]}",
            intent=IntentCategory.GENERATE_NOTES,
            description=f"Generate notes: {topic}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="retrieve_content",
                    description=f"Retrieve content on {topic}",
                    phase="phase3",
                    action="retrieve_knowledge",
                    params={"query": topic},
                ),
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="generate_notes",
                    description="Generate notes",
                    phase="phase3",
                    action="generate_notes",
                    params={"topic": topic},
                ),
            ],
            requires_phase3=True,
        )

    def _build_find_knowledge(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("query", "unknown")
        return Workflow(
            workflow_id=f"wf_know_{query[:20]}",
            intent=IntentCategory.FIND_KNOWLEDGE,
            description=f"Find knowledge: {query}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="search_knowledge",
                    description=f"Search for {query}",
                    phase="phase3",
                    action="search_knowledge",
                    params={"query": query},
                ),
            ],
            requires_phase3=True,
        )

    # ========== NAVIGATION WORKFLOWS ==========

    def _build_go_back(self) -> Workflow:
        return Workflow(
            workflow_id="wf_back",
            intent=IntentCategory.GO_BACK,
            description="Go back",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="press_back",
                    description="Press back",
                    phase="phase1",
                    action="press_key",
                    params={"keycode": 4},  # KEYCODE_BACK
                ),
            ],
            requires_phase1=True,
        )

    def _build_go_home(self) -> Workflow:
        return Workflow(
            workflow_id="wf_home",
            intent=IntentCategory.GO_HOME,
            description="Go home",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="press_home",
                    description="Press home",
                    phase="phase1",
                    action="press_key",
                    params={"keycode": 3},  # KEYCODE_HOME
                ),
            ],
            requires_phase1=True,
        )

    def _build_scroll(self, slots: Dict[str, Any]) -> Workflow:
        direction = slots.get("direction", "down")
        return Workflow(
            workflow_id=f"wf_scroll_{direction}",
            intent=IntentCategory.SCROLL,
            description=f"Scroll {direction}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="scroll",
                    description=f"Scroll {direction}",
                    phase="phase1",
                    action="swipe",
                    params={"direction": direction},
                ),
            ],
            requires_phase1=True,
        )

    # ========== MEDIA WORKFLOWS ==========

    def _build_open_camera(self) -> Workflow:
        return Workflow(
            workflow_id="wf_camera",
            intent=IntentCategory.OPEN_CAMERA,
            description="Open camera",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description="Open Camera",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "camera"},
                    verification={"type": "foreground_app", "expected": "camera"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_play_music(self, slots: Dict[str, Any]) -> Workflow:
        query = slots.get("query", "")
        return Workflow(
            workflow_id="wf_music",
            intent=IntentCategory.PLAY_MUSIC,
            description=f"Play music: {query}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description="Open Spotify",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "spotify"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_open_settings(self) -> Workflow:
        return Workflow(
            workflow_id="wf_settings",
            intent=IntentCategory.OPEN_SETTINGS,
            description="Open settings",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description="Open Settings",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "settings"},
                    verification={"type": "foreground_app", "expected": "settings"},
                ),
            ],
            requires_phase1=True,
        )

    # ========== SYSTEM WORKFLOWS ==========

    def _build_toggle_wifi(self, slots: Dict[str, Any]) -> Workflow:
        state = slots.get("state", "on")
        return Workflow(
            workflow_id=f"wf_wifi_{state}",
            intent=IntentCategory.TOGGLE_WIFI,
            description=f"Turn WiFi {state}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="toggle_wifi",
                    description=f"WiFi {state}",
                    phase="phase1",
                    action="toggle_setting",
                    params={"setting": "wifi", "state": state},
                ),
            ],
            requires_phase1=True,
        )

    def _build_toggle_bluetooth(self, slots: Dict[str, Any]) -> Workflow:
        state = slots.get("state", "on")
        return Workflow(
            workflow_id=f"wf_bt_{state}",
            intent=IntentCategory.TOGGLE_BLUETOOTH,
            description=f"Turn Bluetooth {state}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="toggle_bluetooth",
                    description=f"Bluetooth {state}",
                    phase="phase1",
                    action="toggle_setting",
                    params={"setting": "bluetooth", "state": state},
                ),
            ],
            requires_phase1=True,
        )

    def _build_toggle_flashlight(self, slots: Dict[str, Any]) -> Workflow:
        state = slots.get("state", "on")
        return Workflow(
            workflow_id=f"wf_flash_{state}",
            intent=IntentCategory.TOGGLE_FLASHLIGHT,
            description=f"Flashlight {state}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="toggle_flash",
                    description=f"Flashlight {state}",
                    phase="phase1",
                    action="toggle_setting",
                    params={"setting": "flashlight", "state": state},
                ),
            ],
            requires_phase1=True,
        )

    def _build_volume(self, slots: Dict[str, Any]) -> Workflow:
        direction = slots.get("direction", "up")
        return Workflow(
            workflow_id=f"wf_vol_{direction}",
            intent=IntentCategory.VOLUME_CONTROL,
            description=f"Volume {direction}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="volume",
                    description=f"Volume {direction}",
                    phase="phase1",
                    action="volume_control",
                    params={"direction": direction},
                ),
            ],
            requires_phase1=True,
        )

    def _build_lock_device(self) -> Workflow:
        return Workflow(
            workflow_id="wf_lock",
            intent=IntentCategory.LOCK_DEVICE,
            description="Lock device",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="lock",
                    description="Lock screen",
                    phase="phase1",
                    action="press_key",
                    params={"keycode": 26},  # KEYCODE_POWER
                ),
            ],
            requires_phase1=True,
        )

    def _build_reminder(self, slots: Dict[str, Any]) -> Workflow:
        message = slots.get("query", "reminder")
        time = slots.get("time", "")
        return Workflow(
            workflow_id="wf_reminder",
            intent=IntentCategory.CREATE_REMINDER,
            description=f"Set reminder: {message}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="create_reminder",
                    description=f"Reminder: {message}",
                    phase="phase1",
                    action="create_reminder",
                    params={"message": message, "time": time},
                ),
            ],
            requires_phase1=True,
        )

    def _build_schedule_event(self, slots: Dict[str, Any]) -> Workflow:
        return Workflow(
            workflow_id="wf_event",
            intent=IntentCategory.SCHEDULE_EVENT,
            description="Schedule event",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="open_calendar",
                    description="Open Calendar",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "calendar"},
                ),
            ],
            requires_phase1=True,
        )

    def _build_alarm(self, slots: Dict[str, Any]) -> Workflow:
        time = slots.get("time", "unknown")
        return Workflow(
            workflow_id="wf_alarm",
            intent=IntentCategory.SET_ALARM,
            description=f"Set alarm for {time}",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="open_clock",
                    description="Open Clock",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": "clock"},
                ),
            ],
            requires_phase1=True,
        )

    # ========== COMPOUND WORKFLOWS ==========

    def _build_compound(self, intent_result: IntentResult) -> Workflow:
        """Build workflow for compound actions."""
        compounds = intent_result.compound_intents
        steps = []
        
        for i, comp in enumerate(compounds):
            if comp.get("type") == "open_and_act":
                app = comp.get("app", "")
                action = comp.get("action", "")
                
                # Open app
                steps.append(WorkflowStep(
                    step_id=self._next_step(),
                    step_type="launch_app",
                    description=f"Open {app}",
                    phase="phase1",
                    action="launch_app",
                    params={"app_name": app},
                ))
                
                # Search in app
                if "search" in action.lower():
                    query = action.replace("search", "").replace("for", "").strip()
                    steps.append(WorkflowStep(
                        step_id=self._next_step(),
                        step_type="search_in_app",
                        description=f"Search {query}",
                        phase="phase2",
                        action="in_app_search",
                        params={"query": query, "app": app},
                    ))
        
        return Workflow(
            workflow_id="wf_compound",
            intent=IntentCategory.COMPOUND_ACTION,
            description="Execute compound action",
            steps=steps or [
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="unknown",
                    description="Processing command",
                    phase="phase1",
                    action="unknown",
                )
            ],
            requires_phase1=True,
            requires_phase2=True,
        )

    def _build_unknown(self, intent_result: IntentResult) -> Workflow:
        """Build workflow for unknown intents."""
        return Workflow(
            workflow_id="wf_unknown",
            intent=IntentCategory.UNKNOWN,
            description="Processing request",
            steps=[
                WorkflowStep(
                    step_id=self._next_step(),
                    step_type="process",
                    description="Understanding request",
                    phase="phase1",
                    action="unknown",
                    params={"raw": intent_result.raw_command},
                ),
            ],
        )


# Singleton
_workflow_generator = None


def get_workflow_generator() -> DynamicWorkflowGenerator:
    global _workflow_generator
    if _workflow_generator is None:
        _workflow_generator = DynamicWorkflowGenerator()
    return _workflow_generator
