"""
Perception Engine - Unified screen understanding from multiple sources.

Combines:
- Android Accessibility Tree (via companion app WebSocket)
- UI Automator XML dump (via ADB)
- Screenshot + Computer Vision
- OCR text extraction
- Foreground app/activity detection
- Notification state

Output: ScreenPerception with complete UI understanding.
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    TEXT = "text"
    ICON = "icon"
    IMAGE = "image"
    LIST = "list"
    TAB = "tab"
    MENU = "menu"
    DIALOG = "dialog"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    SPINNER = "spinner"
    SCROLL_VIEW = "scroll_view"
    WEB_VIEW = "web_view"
    UNKNOWN = "unknown"


@dataclass
class UIElement:
    """A single UI element from any source."""
    element_id: str = ""
    element_type: ElementType = ElementType.UNKNOWN
    text: str = ""
    content_description: str = ""
    class_name: str = ""
    package: str = ""
    resource_id: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    clickable: bool = False
    scrollable: bool = False
    editable: bool = False
    focused: bool = False
    enabled: bool = True
    visible: bool = True
    selected: bool = False
    checked: bool = False
    source: str = ""  # "accessibility", "ui_automator", "vision", "ocr"
    confidence: float = 1.0
    children: List["UIElement"] = field(default_factory=list)
    bounds: str = ""

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def area(self) -> int:
        return self.w * self.h

    def contains_point(self, px: int, py: int) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def overlaps(self, other: "UIElement") -> bool:
        return (self.x < other.x + other.w and self.x + self.w > other.x and
                self.y < other.y + other.h and self.y + self.h > other.y)

    def to_dict(self) -> dict:
        return {
            "id": self.element_id,
            "type": self.element_type.value,
            "text": self.text,
            "content_description": self.content_description,
            "class_name": self.class_name,
            "package": self.package,
            "resource_id": self.resource_id,
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "clickable": self.clickable,
            "scrollable": self.scrollable,
            "editable": self.editable,
            "focused": self.focused,
            "enabled": self.enabled,
            "visible": self.visible,
            "selected": self.selected,
            "checked": self.checked,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class ActivityInfo:
    """Current activity/window information."""
    package: str = ""
    activity: str = ""
    window_title: str = ""
    is_running: bool = False


@dataclass
class NotificationInfo:
    """Active notification information."""
    package: str = ""
    title: str = ""
    text: str = ""
    timestamp: str = ""


@dataclass
class DeviceState:
    """Current device state."""
    screen_on: bool = True
    locked: bool = False
    battery_level: int = 0
    connected: bool = True


@dataclass
class ScreenPerception:
    """Complete perception of the current screen state."""
    device_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # App/Activity context
    activity: ActivityInfo = field(default_factory=ActivityInfo)
    device_state: DeviceState = field(default_factory=DeviceState)

    # UI elements from all sources
    elements: List[UIElement] = field(default_factory=list)
    accessibility_elements: List[UIElement] = field(default_factory=list)
    ui_automator_elements: List[UIElement] = field(default_factory=list)
    vision_elements: List[UIElement] = field(default_factory=list)
    ocr_elements: List[UIElement] = field(default_factory=list)

    # Quick-access element groups
    buttons: List[UIElement] = field(default_factory=list)
    inputs: List[UIElement] = field(default_factory=list)
    texts: List[UIElement] = field(default_factory=list)
    clickable_elements: List[UIElement] = field(default_factory=list)
    scrollable_elements: List[UIElement] = field(default_factory=list)
    editable_elements: List[UIElement] = field(default_factory=list)

    # OCR text
    full_text: str = ""
    ocr_texts: List[str] = field(default_factory=list)

    # Screen info
    image_width: int = 0
    image_height: int = 0
    screenshot_path: str = ""

    # Notifications
    notifications: List[NotificationInfo] = field(default_factory=list)

    # Confidence
    perception_confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)

    # Timing
    perception_time_ms: float = 0.0
    success: bool = False
    error: str = ""

    def find_element(
        self,
        text: str = "",
        element_type: Optional[ElementType] = None,
        content_description: str = "",
        resource_id: str = "",
        clickable_only: bool = False,
    ) -> Optional[UIElement]:
        """Find a single element matching criteria."""
        for e in self.elements:
            if clickable_only and not e.clickable:
                continue
            if element_type and e.element_type != element_type:
                continue
            if text and text.lower() not in e.text.lower() and text.lower() not in e.content_description.lower():
                continue
            if content_description and content_description.lower() not in e.content_description.lower():
                continue
            if resource_id and resource_id != e.resource_id:
                continue
            return e
        return None

    def find_elements(
        self,
        text: str = "",
        element_type: Optional[ElementType] = None,
        clickable_only: bool = False,
        editable_only: bool = False,
    ) -> List[UIElement]:
        """Find all elements matching criteria."""
        results = []
        for e in self.elements:
            if clickable_only and not e.clickable:
                continue
            if editable_only and not e.editable:
                continue
            if element_type and e.element_type != element_type:
                continue
            if text and text.lower() not in e.text.lower() and text.lower() not in e.content_description.lower():
                continue
            results.append(e)
        return results

    def find_button(self, text: str) -> Optional[UIElement]:
        """Find a button by text or content description."""
        text_lower = text.lower()
        for e in self.buttons:
            if text_lower in e.text.lower() or text_lower in e.content_description.lower():
                return e
        return self.find_element(text=text, element_type=ElementType.BUTTON, clickable_only=True)

    def find_input(self, hint: str = "") -> Optional[UIElement]:
        """Find an input field, optionally by hint text."""
        if hint:
            e = self.find_element(text=hint, element_type=ElementType.INPUT)
            if e:
                return e
        if self.editable_elements:
            return self.editable_elements[0]
        return self.find_element(element_type=ElementType.INPUT, editable_only=True)

    def find_send_button(self) -> Optional[UIElement]:
        """Find send button using common patterns."""
        send_keywords = ["send", "submit", "➤", "↑", "✈", "→"]
        for e in self.buttons:
            combined = (e.text + " " + e.content_description).lower()
            if any(kw in combined for kw in send_keywords):
                return e
        return None

    def find_search_bar(self) -> Optional[UIElement]:
        """Find search bar using common patterns."""
        search_keywords = ["search", "find", "🔍"]
        for e in self.elements:
            combined = (e.text + " " + e.content_description).lower()
            if any(kw in combined for kw in search_keywords):
                if e.element_type in (ElementType.INPUT, ElementType.BUTTON, ElementType.TEXT):
                    return e
        return None

    def has_text(self, text: str, case_sensitive: bool = False) -> bool:
        """Check if text exists on screen."""
        search = text if case_sensitive else text.lower()
        full = self.full_text if case_sensitive else self.full_text.lower()
        return search in full

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat(),
            "activity": {
                "package": self.activity.package,
                "activity": self.activity.activity,
            },
            "device_state": {
                "screen_on": self.device_state.screen_on,
                "locked": self.device_state.locked,
                "battery_level": self.device_state.battery_level,
            },
            "elements_count": len(self.elements),
            "buttons_count": len(self.buttons),
            "inputs_count": len(self.inputs),
            "clickable_count": len(self.clickable_elements),
            "editable_count": len(self.editable_elements),
            "full_text_preview": self.full_text[:500],
            "sources_used": self.sources_used,
            "perception_confidence": self.perception_confidence,
            "perception_time_ms": self.perception_time_ms,
            "success": self.success,
        }


class PerceptionEngine:
    """Unified perception engine combining all screen understanding sources."""

    def __init__(self):
        self._screen_capture = None
        self._ocr_service = None
        self._ui_detector = None
        self._accessibility_bridge = None
        self._adb = None

    def _get_screen_capture(self):
        if self._screen_capture is None:
            from vision.screen_capture import get_screen_capture_service
            self._screen_capture = get_screen_capture_service()
        return self._screen_capture

    def _get_ocr(self):
        if self._ocr_service is None:
            from vision.ocr_service import get_ocr_service
            self._ocr_service = get_ocr_service()
        return self._ocr_service

    def _get_ui_detector(self):
        if self._ui_detector is None:
            from vision.ui_detector import get_ui_detector
            self._ui_detector = get_ui_detector()
        return self._ui_detector

    def _get_accessibility_bridge(self):
        if self._accessibility_bridge is None:
            from services.accessibility_bridge import get_accessibility_bridge
            self._accessibility_bridge = get_accessibility_bridge()
        return self._accessibility_bridge

    def _get_adb(self):
        if self._adb is None:
            from services.adb_service import get_adb_service, find_adb_binary
            self._adb = get_adb_service(find_adb_binary())
        return self._adb

    async def perceive(self, device_id: str) -> ScreenPerception:
        """Full perception of current screen state from all sources."""
        start = datetime.utcnow()
        perception = ScreenPerception(device_id=device_id)

        try:
            # Run all perception sources concurrently
            tasks = [
                self._perceive_accessibility(device_id, perception),
                self._perceive_ui_automator(device_id, perception),
                self._perceive_screenshot(device_id, perception),
                self._perceive_device_state(device_id, perception),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Merge all detected elements into unified list
            self._merge_elements(perception)

            # Calculate confidence based on sources
            source_count = len(perception.sources_used)
            perception.perception_confidence = min(1.0, 0.3 + (source_count * 0.2))

            perception.perception_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
            perception.success = len(perception.elements) > 0 or perception.full_text != ""

            logger.info(
                f"Perception complete for {device_id}: "
                f"{len(perception.elements)} elements, "
                f"{len(perception.buttons)} buttons, "
                f"{len(perception.inputs)} inputs, "
                f"confidence={perception.perception_confidence:.2f}, "
                f"time={perception.perception_time_ms:.0f}ms, "
                f"sources={perception.sources_used}"
            )

        except Exception as e:
            perception.error = str(e)
            perception.perception_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
            logger.error(f"Perception failed for {device_id}: {e}")

        return perception

    async def quick_perceive(self, device_id: str) -> ScreenPerception:
        """Quick perception using only Accessibility and foreground app detection."""
        start = datetime.utcnow()
        perception = ScreenPerception(device_id=device_id)

        try:
            tasks = [
                self._perceive_accessibility(device_id, perception),
                self._perceive_device_state(device_id, perception),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

            self._merge_elements(perception)
            perception.perception_confidence = 0.5 if perception.accessibility_elements else 0.2
            perception.perception_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
            perception.success = len(perception.elements) > 0

        except Exception as e:
            perception.error = str(e)
            perception.perception_time_ms = (datetime.utcnow() - start).total_seconds() * 1000

        return perception

    async def _perceive_accessibility(self, device_id: str, perception: ScreenPerception):
        """Get UI elements from Android Accessibility Service via bridge."""
        try:
            bridge = self._get_accessibility_bridge()
            tree = await bridge.get_accessibility_tree(device_id)
            if tree:
                perception.accessibility_elements = self._parse_accessibility_tree(tree)
                perception.sources_used.append("accessibility")
        except Exception as e:
            logger.debug(f"Accessibility perception unavailable: {e}")

    async def _perceive_ui_automator(self, device_id: str, perception: ScreenPerception):
        """Get UI hierarchy from UIAutomator dump via ADB."""
        try:
            adb = self._get_adb()
            xml_output = await adb.shell(device_id, "uiautomator dump /dev/tty", timeout=10)
            if xml_output and "<hierarchy" in xml_output:
                perception.ui_automator_elements = self._parse_ui_automator_xml(xml_output)
                perception.sources_used.append("ui_automator")
        except Exception as e:
            logger.debug(f"UIAutomator perception unavailable: {e}")

    async def _perceive_screenshot(self, device_id: str, perception: ScreenPerception):
        """Get elements from screenshot + OCR + vision."""
        try:
            capture = self._get_screen_capture()
            result = await capture.capture_from_adb(device_id)
            if result.success and result.image is not None:
                perception.image_width = result.width
                perception.image_height = result.height
                perception.screenshot_path = result.filepath or ""

                # OCR
                ocr = self._get_ocr()
                ocr_result = await ocr.extract_text(result.image)
                perception.full_text = ocr_result.full_text
                perception.ocr_texts = [t.text for t in ocr_result.texts]

                for dt in ocr_result.texts:
                    perception.ocr_elements.append(UIElement(
                        text=dt.text,
                        x=dt.x, y=dt.y, w=dt.w, h=dt.h,
                        element_type=ElementType.TEXT,
                        source="ocr",
                        confidence=dt.confidence,
                    ))

                # Vision-based UI detection
                ui_detector = self._get_ui_detector()
                ui_result = await ui_detector.detect_elements(result.image)
                for elem in ui_result.elements:
                    element_type = ElementType.UNKNOWN
                    if elem.element_type == "button":
                        element_type = ElementType.BUTTON
                    elif elem.element_type == "input":
                        element_type = ElementType.INPUT
                    elif elem.element_type == "icon":
                        element_type = ElementType.ICON
                    elif elem.element_type == "text":
                        element_type = ElementType.TEXT
                    elif elem.element_type == "image":
                        element_type = ElementType.IMAGE

                    perception.vision_elements.append(UIElement(
                        text=elem.text or elem.label,
                        content_description=elem.content_description,
                        x=elem.x, y=elem.y, w=elem.w, h=elem.h,
                        element_type=element_type,
                        clickable=element_type in (ElementType.BUTTON, ElementType.ICON),
                        source="vision",
                        confidence=elem.confidence,
                    ))

                perception.sources_used.append("screenshot")
                perception.sources_used.append("ocr")

        except Exception as e:
            logger.debug(f"Screenshot perception unavailable: {e}")

    async def _perceive_device_state(self, device_id: str, perception: ScreenPerception):
        """Get device state (foreground app, battery, lock state)."""
        try:
            adb = self._get_adb()

            # Foreground app
            foreground = await adb.get_foreground_app(device_id)
            if foreground:
                perception.activity.package = foreground

            # Screen state
            screen_state = await adb.get_screen_state(device_id)
            perception.device_state.screen_on = screen_state == "on"

            # Lock state
            lock_state = await adb.get_lock_state(device_id)
            perception.device_state.locked = lock_state or False

            # Battery
            battery = await adb.get_battery_level(device_id)
            perception.device_state.battery_level = battery or 0

            perception.sources_used.append("device_state")

        except Exception as e:
            logger.debug(f"Device state perception unavailable: {e}")

    def _parse_accessibility_tree(self, tree_data: Dict[str, Any]) -> List[UIElement]:
        """Parse accessibility tree from the companion app."""
        elements = []
        nodes = tree_data.get("nodes", [])
        for node in nodes:
            element = self._accessibility_node_to_element(node)
            if element:
                elements.append(element)
        return elements

    def _accessibility_node_to_element(self, node: Dict[str, Any]) -> Optional[UIElement]:
        """Convert an accessibility node to a UIElement."""
        try:
            bounds_str = node.get("bounds", "")
            x, y, w, h = self._parse_bounds(bounds_str)

            class_name = node.get("className", "")
            element_type = self._class_name_to_element_type(class_name)

            return UIElement(
                element_id=str(node.get("nodeId", "")),
                element_type=element_type,
                text=node.get("text", ""),
                content_description=node.get("contentDescription", ""),
                class_name=class_name,
                package=node.get("packageName", ""),
                resource_id=node.get("viewIdResourceName", ""),
                x=x, y=y, w=w, h=h,
                clickable=node.get("clickable", False),
                scrollable=node.get("scrollable", False),
                editable=node.get("editable", False),
                focused=node.get("focused", False),
                enabled=node.get("enabled", True),
                visible=node.get("visibleToUser", True),
                selected=node.get("selected", False),
                checked=node.get("checked", False),
                source="accessibility",
                confidence=1.0,
                bounds=bounds_str,
            )
        except Exception:
            return None

    def _parse_ui_automator_xml(self, xml_output: str) -> List[UIElement]:
        """Parse UIAutomator XML dump into UIElements."""
        elements = []
        try:
            # Clean XML output (remove trailing messages)
            xml_start = xml_output.find("<?xml")
            if xml_start < 0:
                xml_start = xml_output.find("<hierarchy")
            if xml_start < 0:
                return elements

            xml_end = xml_output.rfind("</hierarchy>")
            if xml_end < 0:
                xml_end = len(xml_output)
            else:
                xml_end += len("</hierarchy>")

            xml_str = xml_output[xml_start:xml_end]
            root = ET.fromstring(xml_str)

            for node in root.iter("node"):
                element = self._ui_automator_node_to_element(node)
                if element:
                    elements.append(element)

        except ET.ParseError as e:
            logger.debug(f"UIAutomator XML parse error: {e}")
        except Exception as e:
            logger.debug(f"UIAutomator parse error: {e}")

        return elements

    def _ui_automator_node_to_element(self, node: ET.Element) -> Optional[UIElement]:
        """Convert a UIAutomator XML node to UIElement."""
        try:
            bounds = node.get("bounds", "")
            x, y, w, h = self._parse_bounds(bounds)

            class_name = node.get("class", "")
            element_type = self._class_name_to_element_type(class_name)

            clickable = node.get("clickable", "false") == "true"
            scrollable = node.get("scrollable", "false") == "true"
            enabled = node.get("enabled", "true") == "true"
            focused = node.get("focused", "false") == "true"
            selected = node.get("selected", "false") == "true"
            checked = node.get("checked", "false") == "true"
            editable = node.get("editable", "false") == "true"

            # Infer editability from class name
            if not editable and "EditText" in class_name:
                editable = True

            return UIElement(
                element_type=element_type,
                text=node.get("text", ""),
                content_description=node.get("content-desc", ""),
                class_name=class_name,
                package=node.get("package", ""),
                resource_id=node.get("resource-id", ""),
                x=x, y=y, w=w, h=h,
                clickable=clickable,
                scrollable=scrollable,
                editable=editable,
                focused=focused,
                enabled=enabled,
                selected=selected,
                checked=checked,
                source="ui_automator",
                confidence=0.9,
                bounds=bounds,
            )
        except Exception:
            return None

    def _class_name_to_element_type(self, class_name: str) -> ElementType:
        """Map Android widget class name to ElementType."""
        if not class_name:
            return ElementType.UNKNOWN
        cn = class_name.lower()
        if "button" in cn or "imagebutton" in cn:
            return ElementType.BUTTON
        if "edittext" in cn or "textview" in cn and "edit" in cn:
            return ElementType.INPUT
        if "textview" in cn or "text" in cn:
            return ElementType.TEXT
        if "imageview" in cn or "image" in cn:
            return ElementType.IMAGE
        if "listview" in cn or "recyclerview" in cn or "list" in cn:
            return ElementType.LIST
        if "tab" in cn:
            return ElementType.TAB
        if "menu" in cn:
            return ElementType.MENU
        if "dialog" in cn:
            return ElementType.DIALOG
        if "checkbox" in cn:
            return ElementType.CHECKBOX
        if "switch" in cn or "toggle" in cn:
            return ElementType.SWITCH
        if "spinner" in cn:
            return ElementType.SPINNER
        if "scrollview" in cn or "nestedscroll" in cn:
            return ElementType.SCROLL_VIEW
        if "webview" in cn:
            return ElementType.WEB_VIEW
        return ElementType.UNKNOWN

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        """Parse bounds string like '[0,0][1080,1920]' into (x, y, w, h)."""
        try:
            if not bounds_str:
                return (0, 0, 0, 0)
            bounds_str = bounds_str.replace("][", ",").replace("[", "").replace("]", "")
            parts = [int(p) for p in bounds_str.split(",")]
            if len(parts) == 4:
                x1, y1, x2, y2 = parts
                return (x1, y1, x2 - x1, y2 - y1)
        except (ValueError, IndexError):
            pass
        return (0, 0, 0, 0)

    def _merge_elements(self, perception: ScreenPerception):
        """Merge elements from all sources into unified list, deduplicating."""
        all_elements: List[UIElement] = []
        seen_positions: set = set()

        def pos_key(x, y, w, h):
            return (x // 30, y // 30, w // 30, h // 30)

        # Priority: Accessibility > UIAutomator > Vision > OCR
        source_priority = [
            ("accessibility", perception.accessibility_elements),
            ("ui_automator", perception.ui_automator_elements),
            ("vision", perception.vision_elements),
            ("ocr", perception.ocr_elements),
        ]

        for source_name, elements in source_priority:
            for e in elements:
                key = pos_key(e.x, e.y, e.w, e.h)
                if key not in seen_positions:
                    seen_positions.add(key)
                    all_elements.append(e)

        # Categorize
        for e in all_elements:
            if e.element_type == ElementType.BUTTON:
                perception.buttons.append(e)
            elif e.element_type == ElementType.INPUT:
                perception.inputs.append(e)
            elif e.element_type == ElementType.TEXT:
                perception.texts.append(e)
            if e.clickable:
                perception.clickable_elements.append(e)
            if e.scrollable:
                perception.scrollable_elements.append(e)
            if e.editable:
                perception.editable_elements.append(e)

        perception.elements = all_elements


_perception_engine: Optional[PerceptionEngine] = None


def get_perception_engine() -> PerceptionEngine:
    global _perception_engine
    if _perception_engine is None:
        _perception_engine = PerceptionEngine()
    return _perception_engine
