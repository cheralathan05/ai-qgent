import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from vision.phone_memory import PhoneMemory, ScreenRecord, NavigationRecord, AppContext, get_phone_memory
from vision.screen_classifier import ScreenClassifier, ScreenType, get_screen_classifier
from app_knowledge import get_app_knowledge, AppKnowledge
from vision.screen_capture import ScreenCaptureService, get_screen_capture_service
from vision.ui_detector import UIDetector, DetectedUIElement, get_ui_detector
from vision.ocr_service import OCRService, get_ocr_service
from vision.layout_detector import LayoutDetector, get_layout_detector

logger = logging.getLogger(__name__)


class NavigationStepType:
    OPEN_APP = "open_app"
    TAP = "tap"
    TYPE_TEXT = "type_text"
    SWIPE = "swipe"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    VERIFY = "verify"


@dataclass
class NavigationInstruction:
    step_type: str
    target: str = ""
    x: int = 0
    y: int = 0
    text: str = ""
    keycode: str = ""
    duration: float = 0.5
    description: str = ""
    confidence: float = 1.0


@dataclass
class NavigationPath:
    target_screen: str
    target_app: str
    instructions: List[NavigationInstruction] = field(default_factory=list)
    total_steps: int = 0
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "target_screen": self.target_screen,
            "target_app": self.target_app,
            "instructions": [
                {"step_type": i.step_type, "target": i.target, "x": i.x, "y": i.y,
                 "text": i.text, "keycode": i.keycode, "duration": i.duration,
                 "description": i.description, "confidence": i.confidence}
                for i in self.instructions
            ],
            "total_steps": self.total_steps,
            "confidence": self.confidence,
        }


class NavigationIntelligence:
    def __init__(self):
        self._phone_memory = get_phone_memory()
        self._app_knowledge = get_app_knowledge()
        self._classifier = get_screen_classifier()
        self._capture = get_screen_capture_service()
        self._ui_detector = get_ui_detector()
        self._ocr = get_ocr_service()
        self._layout = get_layout_detector()

    def get_current_position(self, device_id: str) -> Optional[ScreenRecord]:
        return self._phone_memory.get_current_screen(device_id)

    def get_navigation_history(self, device_id: str, limit: int = 50) -> List[NavigationRecord]:
        return self._phone_memory.get_navigation_history(device_id, limit)

    def get_screen_history(self, device_id: str, limit: int = 50) -> List[ScreenRecord]:
        return self._phone_memory.get_screen_history(device_id, limit)

    def get_recent_screen_types(self, device_id: str, limit: int = 10) -> List[str]:
        return self._phone_memory.get_recent_screen_types(device_id, limit)

    def get_recent_apps(self, device_id: str, limit: int = 10) -> List[str]:
        return self._phone_memory.get_recent_apps(device_id, limit)

    def get_app_context(self, device_id: str, app_name: str) -> Optional[AppContext]:
        return self._phone_memory.get_app_context(device_id, app_name)

    def plan_path_to_screen(
        self,
        device_id: str,
        target_screen: ScreenType,
        target_app: Optional[str] = None,
    ) -> NavigationPath:
        current = self._phone_memory.get_current_screen(device_id)
        instructions: List[NavigationInstruction] = []

        if current and current.app_name and current.screen_type == target_screen:
            return NavigationPath(
                target_screen=target_screen.value,
                target_app=target_app or "",
                instructions=[],
                total_steps=0,
                confidence=1.0,
            )

        if target_app and current and current.app_name != target_app:
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP,
                target=target_app,
                description=f"Open {target_app}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT,
                duration=3.0,
                description="Wait for app to load",
            ))

        known_nav = self._resolve_known_navigation(target_app or "", current, target_screen)
        if known_nav:
            instructions.extend(known_nav)

        if not known_nav and current:
            screen_history = self._phone_memory.get_screen_history(device_id)
            found_path = self._infer_path_from_history(screen_history, current, target_screen)
            if found_path:
                instructions.extend(found_path)

        if not instructions and target_app:
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP,
                target=target_app,
                description=f"Open {target_app} to reach {target_screen.value}",
            ))

        confidence = 0.7 if instructions else 0.1

        return NavigationPath(
            target_screen=target_screen.value,
            target_app=target_app or "",
            instructions=instructions,
            total_steps=len(instructions),
            confidence=confidence,
        )

    def _resolve_known_navigation(
        self,
        app_name: str,
        current: Optional[ScreenRecord],
        target_screen: ScreenType,
    ) -> Optional[List[NavigationInstruction]]:
        app_def = self._app_knowledge.get_app(app_name) if app_name else None
        if not app_def:
            return None

        known_screens = list(app_def.screens.keys())
        current_screen_name = current.screen_name if current else None

        for path in app_def.navigation_paths:
            if path.to_screen == target_screen.value:
                return [
                    NavigationInstruction(
                        step_type=step.get("action", "tap"),
                        target=step.get("target", ""),
                        description=step.get("description", f"Step: {step.get('action')}"),
                        duration=1.0,
                    )
                    for step in path.steps
                ]

        return None

    def _infer_path_from_history(
        self,
        history: List[ScreenRecord],
        current: ScreenRecord,
        target: ScreenType,
    ) -> Optional[List[NavigationInstruction]]:
        target_reached = False
        target_index = -1

        for i, record in enumerate(history):
            if record.screen_type == target:
                target_reached = True
                target_index = i
                break

        if not target_reached or target_index < 0:
            return None

        current_index = -1
        for i, record in enumerate(history):
            if record.detected_at == current.detected_at:
                current_index = i
                break

        if current_index < 0:
            return None

        if target_index >= current_index:
            return None

        return [
            NavigationInstruction(
                step_type=NavigationStepType.PRESS_KEY,
                keycode="KEYCODE_BACK",
                description="Go back",
                duration=0.5,
            )
            for _ in range(min(5, current_index - target_index))
        ]

    def plan_send_message(
        self,
        device_id: str,
        app: str,
        recipient: str,
        message: str,
    ) -> NavigationPath:
        current = self._phone_memory.get_current_screen(device_id)
        instructions: List[NavigationInstruction] = []

        if not current or current.app_name != app:
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP, target=app,
                description=f"Open {app}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=3.0,
                description="Wait for app to load",
            ))

        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.TAP, target="search",
            description=f"Tap search to find {recipient}",
            confidence=0.7,
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.TYPE_TEXT, text=recipient,
            description=f"Type {recipient}",
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.WAIT, duration=2.0,
            description="Wait for search results",
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.TAP, target=recipient,
            description=f"Tap on {recipient} chat",
            confidence=0.6,
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.WAIT, duration=2.0,
            description="Wait for chat to open",
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.TYPE_TEXT, text=message,
            description=f"Type message: {message[:30]}",
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.TAP, target="Send",
            description="Tap Send button",
        ))
        instructions.append(NavigationInstruction(
            step_type=NavigationStepType.WAIT, duration=1.0,
            description="Wait for message to send",
        ))

        return NavigationPath(
            target_screen=f"{app}_chat",
            target_app=app,
            instructions=instructions,
            total_steps=len(instructions),
            confidence=0.6,
        )

    def plan_reply(self, device_id: str, message: str) -> NavigationPath:
        current = self._phone_memory.get_current_screen(device_id)
        instructions: List[NavigationInstruction] = []

        if current and current.screen_type in (
            ScreenType.WHATSAPP_CHAT, ScreenType.INSTAGRAM_DM_CHAT,
            ScreenType.TELEGRAM_CHAT, ScreenType.DISCORD_CHAT,
            ScreenType.MESSENGER_CHAT,
        ):
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TYPE_TEXT, text=message,
                description=f"Type reply: {message[:30]}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="Send",
                description="Tap Send button",
            ))
            confidence = 0.8
        else:
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=1.0,
                description="Attempt reply in current context",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TYPE_TEXT, text=message,
                description=f"Type: {message[:30]}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="Send",
                description="Tap Send",
            ))
            confidence = 0.4

        return NavigationPath(
            target_screen="reply_sent",
            target_app=current.app_name if current else "",
            instructions=instructions,
            total_steps=len(instructions),
            confidence=confidence,
        )

    def format_instructions_for_adb(self, instructions: List[NavigationInstruction]) -> List[dict]:
        adb_steps = []
        for inst in instructions:
            if inst.step_type == NavigationStepType.OPEN_APP:
                adb_steps.append({"type": "launch_app", "app": inst.target, "description": inst.description})
            elif inst.step_type == NavigationStepType.TAP:
                if inst.x > 0 and inst.y > 0:
                    adb_steps.append({"type": "tap", "x": inst.x, "y": inst.y, "description": inst.description})
                else:
                    adb_steps.append({"type": "tap_target", "target": inst.target, "description": inst.description})
            elif inst.step_type == NavigationStepType.TYPE_TEXT:
                adb_steps.append({"type": "type_text", "text": inst.text, "description": inst.description})
            elif inst.step_type == NavigationStepType.PRESS_KEY:
                adb_steps.append({"type": "press_key", "keycode": inst.keycode, "description": inst.description})
            elif inst.step_type == NavigationStepType.WAIT:
                adb_steps.append({"type": "wait", "duration": inst.duration, "description": inst.description})
            elif inst.step_type == NavigationStepType.SWIPE:
                adb_steps.append({"type": "scroll", "direction": inst.target, "description": inst.description})
        return adb_steps


_navigation_intelligence: Optional[NavigationIntelligence] = None


def get_navigation_intelligence() -> NavigationIntelligence:
    global _navigation_intelligence
    if _navigation_intelligence is None:
        _navigation_intelligence = NavigationIntelligence()
    return _navigation_intelligence
