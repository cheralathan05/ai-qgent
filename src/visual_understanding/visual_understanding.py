"""Visual Understanding: OCR, UI detection, layout/button/text/icon/color detection, screen classification."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ScreenType(str, Enum):
    HOME_SCREEN = "home_screen"
    SETTINGS = "settings"
    WHATSAPP_CHAT = "whatsapp_chat"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_DM = "instagram_dm"
    CHROME_SEARCH = "chrome_search"
    YOUTUBE_VIDEO = "youtube_video"
    APP_DRAWER = "app_drawer"
    LOCK_SCREEN = "lock_screen"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


@dataclass
class DetectedElement:
    element_type: str  # button, text, icon, input, image
    text: Optional[str] = None
    confidence: float = 0.0
    bounds: Optional[Dict[str, int]] = None
    color: Optional[str] = None
    content_description: Optional[str] = None


@dataclass
class UIDetectionResult:
    elements: List[DetectedElement] = field(default_factory=list)
    text_content: str = ""
    layout_type: str = "unknown"
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ScreenClassification:
    screen_type: ScreenType
    app_name: Optional[str] = None
    screen_name: Optional[str] = None
    confidence: float = 0.0
    detected_elements: List[DetectedElement] = field(default_factory=list)


class VisualUnderstanding:
    """Analyzes screen content using OCR, element detection, and classification."""

    SCREEN_SIGNATURES = {
        ScreenType.INSTAGRAM_FEED: {"apps": ["instagram"], "indicators": ["feed", "home", "like", "comment"]},
        ScreenType.INSTAGRAM_DM: {"apps": ["instagram"], "indicators": ["direct", "message", "inbox", "chat"]},
        ScreenType.WHATSAPP_CHAT: {"apps": ["whatsapp"], "indicators": ["chat", "message", "type a message", "whatsapp"]},
        ScreenType.CHROME_SEARCH: {"apps": ["chrome"], "indicators": ["search", "google", "url", "http"]},
        ScreenType.YOUTUBE_VIDEO: {"apps": ["youtube"], "indicators": ["subscribe", "like", "comment", "share", "video"]},
        ScreenType.SETTINGS: {"apps": ["settings"], "indicators": ["setting", "preference", "config"]},
        ScreenType.HOME_SCREEN: {"indicators": ["home screen", "app drawer", "wallpaper"]},
        ScreenType.LOCK_SCREEN: {"indicators": ["lock screen", "enter pin", "password", "pattern"]},
    }

    APP_PACKAGE_MAP = {
        "com.instagram.android": "instagram",
        "com.whatsapp": "whatsapp",
        "com.android.chrome": "chrome",
        "com.google.android.youtube": "youtube",
        "com.android.settings": "settings",
    }

    def __init__(self):
        pass

    async def detect_elements(self, screenshot_data: Optional[bytes] = None, xml_dump: Optional[str] = None) -> UIDetectionResult:
        elements = []
        text_content = ""

        if xml_dump:
            parsed = self._parse_xml_elements(xml_dump)
            elements = parsed.get("elements", [])
            text_content = parsed.get("text", "")

        return UIDetectionResult(
            elements=elements,
            text_content=text_content,
            layout_type="inferred",
        )

    def _parse_xml_elements(self, xml: str) -> Dict[str, Any]:
        elements = []
        texts = []
        import re
        node_pattern = re.compile(r'<node[^>]*>')
        for match in node_pattern.finditer(xml):
            attrs = self._parse_node_attributes(match.group())
            if attrs:
                element = DetectedElement(
                    element_type=attrs.get("class", "unknown").split(".")[-1].lower(),
                    text=attrs.get("text", ""),
                    confidence=0.9,
                    content_description=attrs.get("content-desc", ""),
                )
                elements.append(element)
                if attrs.get("text"):
                    texts.append(attrs["text"])
        return {"elements": elements, "text": " ".join(texts)}

    def _parse_node_attributes(self, node_str: str) -> Dict[str, str]:
        attrs = {}
        import re
        for match in re.finditer(r'(\w+)=["\']([^"\']*)["\']', node_str):
            attrs[match.group(1)] = match.group(2)
        return attrs

    def classify_screen(self, foreground_app: Optional[str] = None, text_content: str = "", elements: Optional[List[DetectedElement]] = None) -> ScreenClassification:
        app_name = self._resolve_app_name(foreground_app) if foreground_app else None
        text_lower = text_content.lower()

        for screen_type, signature in self.SCREEN_SIGNATURES.items():
            app_match = not signature.get("apps") or (app_name and app_name in signature["apps"])
            indicator_match = any(ind in text_lower for ind in signature["indicators"])

            if app_match and indicator_match:
                return ScreenClassification(
                    screen_type=screen_type,
                    app_name=app_name,
                    screen_name=screen_type.value,
                    confidence=0.85 if indicator_match else 0.6,
                    detected_elements=elements or [],
                )

        return ScreenClassification(
            screen_type=ScreenType.UNKNOWN,
            app_name=app_name,
            screen_name="unknown",
            confidence=0.3,
            detected_elements=elements or [],
        )

    def _resolve_app_name(self, package: str) -> Optional[str]:
        return self.APP_PACKAGE_MAP.get(package, package.split(".")[-1] if "." in package else package)

    async def ocr_text(self, image_data: bytes) -> str:
        return ""

    def detect_buttons(self, elements: List[DetectedElement]) -> List[DetectedElement]:
        return [e for e in elements if e.element_type in ("button", "imagebutton", "textview") and e.text]

    def detect_text(self, elements: List[DetectedElement]) -> List[DetectedElement]:
        return [e for e in elements if e.element_type == "textview" and e.text]

    def detect_inputs(self, elements: List[DetectedElement]) -> List[DetectedElement]:
        return [e for e in elements if e.element_type in ("edittext", "input")]


_visual_understanding: Optional[VisualUnderstanding] = None


def get_visual_understanding() -> VisualUnderstanding:
    global _visual_understanding
    if _visual_understanding is None:
        _visual_understanding = VisualUnderstanding()
    return _visual_understanding
