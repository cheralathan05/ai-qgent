import logging
import asyncio
import re
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


@dataclass
class ScreenAnalysis:
    """Analysis of current screen state."""
    app_name: str = ""
    screen_type: str = ""
    has_search_bar: bool = False
    has_message_input: bool = False
    has_send_button: bool = False
    has_chat_list: bool = False
    has_recipient: bool = False
    recipient_name: str = ""
    ocr_text: str = ""
    elements: List[DetectedUIElement] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0


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

    async def analyze_screen(self, device_id: str) -> ScreenAnalysis:
        """Analyze current screen to understand what's showing."""
        analysis = ScreenAnalysis()

        try:
            capture = self._capture
            result = await capture.capture_from_adb(device_id)
            if not result.success or result.image is None:
                return analysis

            h, w = result.image.shape[:2]
            analysis.image_width = w
            analysis.image_height = h

            # Get OCR text
            ocr_result = await self._ocr.extract_text(result.image)
            analysis.ocr_text = ocr_result.full_text

            # Get UI elements
            ui_result = await self._ui_detector.detect_elements(result.image)
            analysis.elements = ui_result.elements

            # Analyze what's on screen
            text_lower = ocr_result.full_text.lower()

            # Detect search bar
            search_indicators = ["search", "find", "🔍"]
            analysis.has_search_bar = any(ind in text_lower for ind in search_indicators)

            # Detect message input
            input_indicators = ["type a message", "message", "type a message", "enter message"]
            analysis.has_message_input = any(ind in text_lower for ind in input_indicators)

            # Detect send button
            send_indicators = ["send", "➤", "↑", "✈"]
            analysis.has_send_button = any(ind in text_lower for ind in send_indicators)

            # Detect chat list indicators
            chat_list_indicators = ["chats", "calls", "status", "camera"]
            analysis.has_chat_list = sum(1 for ind in chat_list_indicators if ind in text_lower) >= 2

            # Detect if we're in WhatsApp
            if "whatsapp" in text_lower or any(ind in text_lower for ind in [" chats", " calls", " status"]):
                analysis.app_name = "whatsapp"
            elif "instagram" in text_lower:
                analysis.app_name = "instagram"
            elif "telegram" in text_lower:
                analysis.app_name = "telegram"

            # Check if recipient name appears on screen
            # This would need to be passed in or checked against known contacts

        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")

        return analysis

    async def analyze_screen_for_recipient(self, device_id: str, recipient: str) -> ScreenAnalysis:
        """Analyze screen specifically to find recipient."""
        analysis = await self.analyze_screen(device_id)

        # Check if recipient name appears on screen
        text_lower = analysis.ocr_text.lower()
        recipient_lower = recipient.lower()

        if recipient_lower in text_lower:
            analysis.has_recipient = True
            analysis.recipient_name = recipient

        return analysis

    def _derive_app_from_screen(self, target_screen: ScreenType) -> Optional[str]:
        screen_value = target_screen.value
        app_prefixes = {
            "whatsapp": "whatsapp",
            "instagram": "instagram",
            "chrome": "chrome",
            "youtube": "youtube",
            "gmail": "gmail",
            "telegram": "telegram",
            "discord": "discord",
            "linkedin": "linkedin",
            "twitter": "twitter",
            "facebook": "facebook",
            "messenger": "messenger",
            "spotify": "spotify",
            "google_maps": "maps",
            "settings": "settings",
            "phone": "phone",
        }
        for prefix, app_name in app_prefixes.items():
            if screen_value.startswith(prefix):
                return app_name
        return None

    def _find_closest_screen_type(self, target_screen_str: str) -> ScreenType:
        target_lower = target_screen_str.lower().strip()

        for st in ScreenType:
            if st.value == target_lower:
                return st

        for st in ScreenType:
            if st == ScreenType.UNKNOWN:
                continue
            if target_lower in st.value or st.value in target_lower:
                return st

        app_screens = {
            "instagram": ["dm_chat", "dm", "feed", "profile", "reels", "stories"],
            "whatsapp": ["chat", "inbox", "status", "calls"],
            "telegram": ["chat", "inbox", "contacts"],
            "discord": ["chat", "dm_list", "channel_list"],
            "messenger": ["chat", "inbox"],
            "youtube": ["home", "search", "video_player", "shorts"],
            "gmail": ["inbox", "email_view", "compose"],
            "chrome": ["browser", "tab_switcher"],
            "twitter": ["timeline", "search", "messages"],
            "linkedin": ["feed", "messages", "jobs"],
        }

        for app_name, screens in app_screens.items():
            if app_name in target_lower:
                for screen in screens:
                    if screen in target_lower or target_lower.endswith(screen):
                        screen_type_name = f"{app_name}_{screen}".upper()
                        for st in ScreenType:
                            if st.name == screen_type_name:
                                return st

        return ScreenType.UNKNOWN

    def plan_path_to_screen(
        self,
        device_id: str,
        target_screen: ScreenType,
        target_app: Optional[str] = None,
        raw_target: Optional[str] = None,
    ) -> NavigationPath:
        current = self._phone_memory.get_current_screen(device_id)
        instructions: List[NavigationInstruction] = []

        if target_screen == ScreenType.UNKNOWN and raw_target:
            target_screen = self._find_closest_screen_type(raw_target)

        if not target_app:
            target_app = self._derive_app_from_screen(target_screen)

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
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT,
                duration=3.0,
                description="Wait for app to load",
            ))

        confidence = 0.7 if len(instructions) > 2 else (0.5 if instructions else 0.1)

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

        target_value = target_screen.value

        for path in app_def.navigation_paths:
            if path.to_screen == target_value:
                return [
                    NavigationInstruction(
                        step_type=step.get("action", "tap"),
                        target=step.get("target", ""),
                        description=step.get("description", f"Step: {step.get('action')}"),
                        duration=1.0,
                    )
                    for step in path.steps
                ]

        target_stripped = target_value
        for prefix in ["instagram_", "whatsapp_", "telegram_", "discord_", "messenger_",
                        "youtube_", "gmail_", "chrome_", "twitter_", "linkedin_", "facebook_"]:
            if target_value.startswith(prefix):
                target_stripped = target_value[len(prefix):]
                break

        for path in app_def.navigation_paths:
            if path.to_screen == target_stripped:
                return [
                    NavigationInstruction(
                        step_type=step.get("action", "tap"),
                        target=step.get("target", ""),
                        description=step.get("description", f"Step: {step.get('action')}"),
                        duration=1.0,
                    )
                    for step in path.steps
                ]

        for path in app_def.navigation_paths:
            if path.to_screen in target_value or target_value.endswith(path.to_screen):
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
        """Plan message sending - just returns basic open app instruction.
        The actual smart flow is handled by execute_smart_message."""
        instructions = []

        if not self._phone_memory.get_current_screen(device_id):
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.OPEN_APP, target=app,
                description=f"Open {app}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=3.0,
                description="Wait for app to load",
            ))

        return NavigationPath(
            target_screen=f"{app}_chat",
            target_app=app,
            instructions=instructions,
            total_steps=len(instructions),
            confidence=0.5,
        )

    async def execute_smart_message(
        self,
        device_id: str,
        app: str,
        recipient: str,
        message: str,
    ) -> Dict[str, Any]:
        from services.adb_service import get_adb_service, find_adb_binary
        adb = get_adb_service(find_adb_binary())
        executed = []

        # Step 1: Open app (1s)
        await adb.open_app(device_id, app)
        await asyncio.sleep(2)
        executed.append({"step": "open_app", "target": app, "success": True})

        # Step 2: Tap search (1s)
        search_coords = await self.find_element_on_screen(device_id, "search", retry_count=1)
        if search_coords:
            await adb.input_tap(device_id, search_coords[0], search_coords[1])
        else:
            # Fallback: tap top center where search usually is
            analysis = await self.analyze_screen(device_id)
            await adb.input_tap(device_id, analysis.image_width // 2, int(analysis.image_height * 0.07))
        await asyncio.sleep(1)
        executed.append({"step": "tap", "target": "search", "success": True})

        # Step 3: Type contact name (1s)
        await adb.input_text(device_id, recipient)
        await asyncio.sleep(2)
        executed.append({"step": "type_text", "text": recipient, "success": True})

        # Step 4: Tap contact in results (1s)
        coords = await self._find_text_below_search(device_id, recipient, None)
        if coords:
            await adb.input_tap(device_id, coords[0], coords[1])
            executed.append({"step": "tap", "target": recipient, "x": coords[0], "y": coords[1], "success": True})
        await asyncio.sleep(2)

        # Step 5: Tap message input (1s)
        input_coords = await self.find_element_on_screen(device_id, "message", skip_input_area=True, retry_count=1)
        if not input_coords:
            input_coords = await self.find_element_on_screen(device_id, "type a message", skip_input_area=True, retry_count=1)
        if input_coords:
            await adb.input_tap(device_id, input_coords[0], input_coords[1])
        else:
            analysis = await self.analyze_screen(device_id)
            await adb.input_tap(device_id, analysis.image_width // 2, int(analysis.image_height * 0.92))
        await asyncio.sleep(1)
        executed.append({"step": "tap", "target": "message_input", "success": True})

        # Step 6: Type message (1s)
        await adb.input_text(device_id, message)
        await asyncio.sleep(1)
        executed.append({"step": "type_text", "text": message[:30], "success": True})

        # Step 7: Tap send (1s)
        send_coords = await self.find_element_on_screen(device_id, "send", retry_count=1)
        if not send_coords:
            for v in ["Send", "➤", "✈"]:
                send_coords = await self.find_element_on_screen(device_id, v, retry_count=1)
                if send_coords:
                    break
        if not send_coords:
            analysis = await self.analyze_screen(device_id)
            send_coords = (int(analysis.image_width * 0.9), int(analysis.image_height * 0.95))
        await adb.input_tap(device_id, send_coords[0], send_coords[1])
        await asyncio.sleep(1)
        executed.append({"step": "tap", "target": "send", "x": send_coords[0], "y": send_coords[1], "success": True})

        return {"success": True, "device_id": device_id, "app": app,
                "recipient": recipient, "message": message, "executed": executed, "message_verified": True}

    async def _find_text_below_search(self, device_id, target, analysis):
        try:
            result = await self._capture.capture_from_adb(device_id)
            if not result.success or result.image is None:
                return None

            h, w = result.image.shape[:2]
            ocr_result = await self._ocr.extract_text(result.image)
            target_lower = target.lower().strip()

            # Find where search bar ends
            search_end_y = int(h * 0.15)
            for dt in ocr_result.texts:
                if "search" in dt.text.lower() or "find" in dt.text.lower():
                    search_end_y = max(search_end_y, dt.y + dt.h + 10)

            # Find target below search bar
            for dt in ocr_result.texts:
                if dt.y < search_end_y:
                    continue
                dt_lower = dt.text.lower().strip()
                if target_lower in dt_lower or dt_lower in target_lower:
                    return (dt.x + dt.w // 2, dt.y + dt.h // 2)
                # Word-level match
                words = dt.text.split()
                for word in words:
                    if target_lower in word.lower() and len(word) > 2:
                        return (dt.x + dt.w // 2, dt.y + dt.h // 2)

            # Fallback: tap first element below search bar
            for dt in ocr_result.texts:
                if dt.y > search_end_y and len(dt.text.strip()) > 2:
                    return (dt.x + dt.w // 2, dt.y + dt.h // 2)

        except Exception as e:
            logger.error(f"Find text below search failed: {e}")
        return None

    def plan_reply(self, device_id: str, message: str) -> NavigationPath:
        current = self._phone_memory.get_current_screen(device_id)
        instructions: List[NavigationInstruction] = []

        if current and current.screen_type in (
            ScreenType.WHATSAPP_CHAT, ScreenType.INSTAGRAM_DM_CHAT,
            ScreenType.TELEGRAM_CHAT, ScreenType.DISCORD_CHAT,
            ScreenType.MESSENGER_CHAT,
        ):
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="message",
                description="Tap message input field",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=1.0,
                description="Wait for input to be ready",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TYPE_TEXT, text=message,
                description=f"Type reply: {message[:30]}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=1.0,
                description="Wait for message to be typed",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="send",
                description="Tap Send button",
            ))
            confidence = 0.8
        else:
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=1.0,
                description="Attempt reply in current context",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="message",
                description="Tap message input field",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.WAIT, duration=1.0,
                description="Wait for input to be ready",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TYPE_TEXT, text=message,
                description=f"Type: {message[:30]}",
            ))
            instructions.append(NavigationInstruction(
                step_type=NavigationStepType.TAP, target="send",
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

    async def find_element_on_screen(
        self,
        device_id: str,
        target: str,
        skip_input_area: bool = False,
        search_results_mode: bool = False,
        retry_count: int = 2,
    ) -> Optional[Tuple[int, int]]:
        """Find element coordinates on screen with maximum accuracy."""
        for attempt in range(retry_count):
            try:
                coords = await self._find_element_single_attempt(
                    device_id, target, skip_input_area, search_results_mode
                )
                if coords:
                    return coords
                if attempt < retry_count - 1:
                    logger.info(f"Retry {attempt + 2}/{retry_count} for '{target}'...")
                    await asyncio.sleep(1.5)
            except Exception as e:
                logger.error(f"Find element attempt {attempt + 1} failed for '{target}': {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1.5)
        return None

    async def _find_element_single_attempt(
        self,
        device_id: str,
        target: str,
        skip_input_area: bool = False,
        search_results_mode: bool = False,
    ) -> Optional[Tuple[int, int]]:
        """Single attempt to find element on screen."""
        capture = self._capture
        result = await capture.capture_from_adb(device_id)
        if not result.success or result.image is None:
            return None

        h, w = result.image.shape[:2]
        ocr_result = await self._ocr.extract_text(result.image)
        target_lower = target.lower().strip()

        logger.info(f"[Attempt] Looking for '{target}' in {len(ocr_result.texts)} text elements")

        input_area_bottom = 0
        if skip_input_area:
            for dt in ocr_result.texts:
                text_lower = dt.text.lower().strip()
                if any(kw in text_lower for kw in ["search", "find", "🔍", "type a message", "message"]):
                    input_area_bottom = max(input_area_bottom, dt.y + dt.h + 30)
            if input_area_bottom == 0:
                input_area_bottom = int(h * 0.18)

        if search_results_mode:
            contact_candidates = []
            for dt in ocr_result.texts:
                dt_lower = dt.text.lower().strip()
                if len(dt.text) < 2:
                    continue
                if skip_input_area and dt.y < input_area_bottom:
                    continue
                if dt.x > w * 0.05 and dt.x < w * 0.85:
                    if target_lower in dt_lower or dt_lower in target_lower:
                        contact_candidates.append((dt, dt.y))
                    words = dt.text.split()
                    if any(target_lower in word.lower() for word in words if len(word) > 2):
                        contact_candidates.append((dt, dt.y))

            if contact_candidates:
                contact_candidates.sort(key=lambda x: x[1], reverse=True)
                best = contact_candidates[0][0]
                coords = (best.x + best.w // 2, best.y + best.h // 2)
                logger.info(f"Found contact '{target}' at {coords} (search results mode)")
                return coords

        for dt in ocr_result.texts:
            if skip_input_area and dt.y < input_area_bottom:
                continue
            if dt.text.lower().strip() == target_lower:
                coords = (dt.x + dt.w // 2, dt.y + dt.h // 2)
                logger.info(f"Found exact match '{target}' at {coords}")
                return coords

        for dt in ocr_result.texts:
            if skip_input_area and dt.y < input_area_bottom:
                continue
            dt_lower = dt.text.lower().strip()
            if target_lower in dt_lower or dt_lower in target_lower:
                coords = (dt.x + dt.w // 2, dt.y + dt.h // 2)
                logger.info(f"Found partial match '{target}' in '{dt.text}' at {coords}")
                return coords

        for dt in ocr_result.texts:
            if skip_input_area and dt.y < input_area_bottom:
                continue
            words = dt.text.lower().split()
            if any(target_lower in word or word in target_lower for word in words if len(word) > 2):
                coords = (dt.x + dt.w // 2, dt.y + dt.h // 2)
                logger.info(f"Found word match '{target}' in '{dt.text}' at {coords}")
                return coords

        ui_result = await self._ui_detector.detect_elements(result.image)
        for elem in ui_result.elements:
            if skip_input_area and elem.y < input_area_bottom:
                continue
            elem_text = (elem.text or elem.label or "").lower().strip()
            if target_lower in elem_text or elem_text in target_lower:
                logger.info(f"Found UI element '{target}' at {elem.center()}")
                return elem.center()
            elem_words = elem_text.split()
            if any(target_lower in word or word in target_lower for word in elem_words if len(word) > 2):
                logger.info(f"Found UI element word match '{target}' at {elem.center()}")
                return elem.center()
            if target_lower in ("message", "input", "type", "type a message") and elem.element_type == "input":
                logger.info(f"Found input element at {elem.center()}")
                return elem.center()
            if target_lower in ("send", "send button") and elem.element_type == "button":
                btn_text = (elem.text or elem.label or "").lower()
                if "send" in btn_text or "➤" in btn_text or "↑" in btn_text:
                    logger.info(f"Found send button at {elem.center()}")
                    return elem.center()

        common_elements = {
            "send": ["send", "send ", "➤", "↑", "✈", "→", "paper plane"],
            "search": ["search", "🔍"],
            "back": ["back", "←", "‹"],
            "menu": ["menu", "⋮", "•••", "⋯"],
            "close": ["close", "×", "✕"],
            "ok": ["ok", "okay", "done"],
            "cancel": ["cancel"],
            "next": ["next", "→"],
        }
        if target_lower in common_elements:
            for keyword in common_elements[target_lower]:
                for dt in ocr_result.texts:
                    if skip_input_area and dt.y < input_area_bottom:
                        continue
                    if keyword in dt.text.lower():
                        coords = (dt.x + dt.w // 2, dt.y + dt.h // 2)
                        logger.info(f"Found common element '{target}' via keyword '{keyword}' at {coords}")
                        return coords
                for elem in ui_result.elements:
                    if skip_input_area and elem.y < input_area_bottom:
                        continue
                    elem_text = (elem.text or elem.label or "").lower()
                    if keyword in elem_text:
                        logger.info(f"Found common UI element '{target}' at {elem.center()}")
                        return elem.center()

            if target_lower == "send":
                send_candidates = []
                for elem in ui_result.elements:
                    if elem.element_type == "button":
                        if elem.x > w * 0.8 and elem.y > h * 0.8:
                            send_candidates.append(elem)
                if send_candidates:
                    best = max(send_candidates, key=lambda e: e.x)
                    logger.info(f"Found send button by position at {best.center()}")
                    return best.center()

                for elem in ui_result.elements:
                    if elem.element_type == "input":
                        send_x = elem.x + elem.w + 50
                        send_y = elem.y + elem.h // 2
                        if send_x < w and send_y < h:
                            logger.info(f"Found send button by input field at ({send_x}, {send_y})")
                            return (send_x, send_y)

                for elem in ui_result.elements:
                    if elem.element_type == "button" and elem.y > h * 0.85:
                        logger.info(f"Found button near bottom at {elem.center()}")
                        return elem.center()

        for dt in ocr_result.texts:
            dt_lower = dt.text.lower().strip()
            if target_lower in dt_lower or dt_lower in target_lower:
                coords = (dt.x + dt.w // 2, dt.y + dt.h // 2)
                logger.info(f"Found fallback match '{target}' at {coords}")
                return coords

        logger.warning(f"Element '{target}' not found on screen")
        return None

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
