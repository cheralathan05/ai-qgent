"""Vision Agent - Central vision analysis combining YOLO, OCR, screen classification.

Captures screen, runs all detection pipelines, and produces a unified ScreenState
that other agents can reason about.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np

from vision.screen_capture import get_screen_capture_service, ScreenCaptureResult
from vision.paddle_ocr_service import get_paddle_ocr_service, PaddleOCRResult, PaddleDetectedText
from vision.yolo_detector import get_yolo_detector, YOLOResult, YOLODetection
from vision.ui_detector import get_ui_detector, UIDetectionResult
from vision.screen_classifier import get_screen_classifier, ScreenClassificationResult, ScreenType
from vision.layout_detector import get_layout_detector, LayoutResult

logger = logging.getLogger(__name__)


@dataclass
class DetectedElement:
    """Unified element detection from all vision pipelines."""
    element_type: str
    x: int
    y: int
    w: int
    h: int
    confidence: float
    text: str = ""
    label: str = ""
    source: str = ""  # "yolo", "ocr", "ui_detector", "combined"

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def to_dict(self) -> dict:
        return {
            "type": self.element_type,
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "confidence": self.confidence,
            "text": self.text,
            "label": self.label,
            "source": self.source,
        }


@dataclass
class ScreenState:
    """Complete analysis of current screen state."""
    device_id: str = ""
    app_name: str = ""
    screen_type: str = ""
    screen_name: str = ""
    classification_confidence: float = 0.0

    # Elements detected by different pipelines
    elements: List[DetectedElement] = field(default_factory=list)
    buttons: List[DetectedElement] = field(default_factory=list)
    inputs: List[DetectedElement] = field(default_factory=list)
    icons: List[DetectedElement] = field(default_factory=list)
    text_labels: List[DetectedElement] = field(default_factory=list)
    search_bars: List[DetectedElement] = field(default_factory=list)
    send_buttons: List[DetectedElement] = field(default_factory=list)
    back_buttons: List[DetectedElement] = field(default_factory=list)

    # OCR results
    ocr_texts: List[PaddleDetectedText] = field(default_factory=list)
    full_ocr_text: str = ""
    ocr_engine: str = ""

    # Screen info
    image_width: int = 0
    image_height: int = 0
    screenshot_path: str = ""

    # Timing
    captured_at: datetime = field(default_factory=datetime.utcnow)
    analysis_time_ms: float = 0.0
    success: bool = False
    error: str = ""

    def has_element_type(self, element_type: str) -> bool:
        return any(e.element_type == element_type for e in self.elements)

    def find_element_by_text(self, text: str, case_sensitive: bool = False) -> Optional[DetectedElement]:
        search = text if case_sensitive else text.lower()
        for e in self.elements:
            e_text = e.text if case_sensitive else e.text.lower()
            if e_text and (search in e_text or e_text in search):
                return e
        return None

    def find_button_by_text(self, text: str) -> Optional[DetectedElement]:
        search = text.lower()
        for b in self.buttons:
            if b.text and search in b.text.lower():
                return b
        return None

    def find_input_field(self) -> Optional[DetectedElement]:
        if self.inputs:
            return self.inputs[0]
        for e in self.elements:
            if e.element_type == "input_field":
                return e
        return None

    def find_send_button(self) -> Optional[DetectedElement]:
        if self.send_buttons:
            return self.send_buttons[0]
        send_keywords = ["send", "➤", "↑", "✈", "→"]
        for b in self.buttons:
            if b.text and any(kw in b.text.lower() for kw in send_keywords):
                return b
        for e in self.elements:
            if e.element_type == "button" and e.y > self.image_height * 0.85:
                if e.x > self.image_width * 0.7:
                    return e
        return None

    def find_search_bar(self) -> Optional[DetectedElement]:
        if self.search_bars:
            return self.search_bars[0]
        search_keywords = ["search", "find", "🔍"]
        for e in self.elements:
            if e.text and any(kw in e.text.lower() for kw in search_keywords):
                return e
        for e in self.elements:
            if e.element_type == "input_field" and e.y < self.image_height * 0.15:
                return e
        return None

    def find_back_button(self) -> Optional[DetectedElement]:
        if self.back_buttons:
            return self.back_buttons[0]
        back_keywords = ["back", "←", "‹"]
        for b in self.buttons:
            if b.text and any(kw in b.text.lower() for kw in back_keywords):
                return b
        for e in self.elements:
            if e.element_type == "icon" and e.x < self.image_width * 0.1 and e.y < self.image_height * 0.1:
                return e
        return None

    def find_element_in_region(
        self, x1: int, y1: int, x2: int, y2: int, element_type: Optional[str] = None
    ) -> List[DetectedElement]:
        results = []
        for e in self.elements:
            cx, cy = e.center()
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                if element_type is None or e.element_type == element_type:
                    results.append(e)
        return results

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "app_name": self.app_name,
            "screen_type": self.screen_type,
            "screen_name": self.screen_name,
            "classification_confidence": self.classification_confidence,
            "elements_count": len(self.elements),
            "buttons_count": len(self.buttons),
            "inputs_count": len(self.inputs),
            "icons_count": len(self.icons),
            "full_ocr_text": self.full_ocr_text[:500],
            "ocr_engine": self.ocr_engine,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "analysis_time_ms": self.analysis_time_ms,
            "success": self.success,
            "error": self.error,
        }


class VisionAgent:
    """Central vision analysis agent.

    Captures screen and runs all detection pipelines to produce
    a unified ScreenState object.
    """

    def __init__(self):
        self._capture = get_screen_capture_service()
        self._ocr = get_paddle_ocr_service()
        self._yolo = get_yolo_detector()
        self._ui_detector = get_ui_detector()
        self._classifier = get_screen_classifier()
        self._layout = get_layout_detector()

    async def analyze_screen(
        self, device_id: str, foreground_app: Optional[str] = None
    ) -> ScreenState:
        """Full screen analysis: capture + OCR + YOLO + classification."""
        start = datetime.utcnow()
        state = ScreenState(device_id=device_id)

        # Step 1: Capture screenshot
        capture = await self._capture.capture_from_adb(device_id)
        if not capture.success or capture.image is None:
            state.error = f"Screen capture failed: {capture.error}"
            state.analysis_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
            return state

        state.image_width = capture.width
        state.image_height = capture.height
        state.screenshot_path = capture.filepath or ""

        # Step 2: Run OCR
        ocr_result = await self._ocr.extract_text(capture.image)
        state.ocr_texts = ocr_result.texts
        state.full_ocr_text = ocr_result.full_text
        state.ocr_engine = ocr_result.engine_used

        # Step 3: Run YOLO detection
        yolo_result = await self._yolo.detect_elements(capture.image)

        # Step 4: Run contour-based UI detection (complementary)
        ui_result = await self._ui_detector.detect_elements(capture.image)

        # Step 5: Merge detections from all sources
        state.elements = self._merge_detections(yolo_result, ui_result, ocr_result, state.image_height)

        # Categorize elements
        for e in state.elements:
            if e.element_type == "button":
                state.buttons.append(e)
            elif e.element_type == "input_field":
                state.inputs.append(e)
            elif e.element_type in ("icon", "back_button", "menu_button", "send_button"):
                state.icons.append(e)
            elif e.element_type == "search_bar":
                state.search_bars.append(e)
            elif e.element_type == "send_button":
                state.send_buttons.append(e)
            elif e.element_type == "back_button":
                state.back_buttons.append(e)
            elif e.element_type == "text_label":
                state.text_labels.append(e)

        # Step 6: Classify screen
        classification = await self._classifier.classify(
            image=capture.image,
            foreground_app=foreground_app,
            text_content=ocr_result.full_text,
            ui_result=ui_result,
        )
        state.app_name = classification.app_name or foreground_app or ""
        state.screen_type = classification.screen_type.value
        state.screen_name = classification.screen_name or classification.screen_type.value
        state.classification_confidence = classification.confidence

        state.success = True
        state.analysis_time_ms = (datetime.utcnow() - start).total_seconds() * 1000

        logger.info(
            f"VisionAgent: analyzed {state.image_width}x{state.image_height} screen "
            f"in {state.analysis_time_ms:.0f}ms - app={state.app_name}, "
            f"screen={state.screen_type}, elements={len(state.elements)}, "
            f"ocr_texts={len(state.ocr_texts)}"
        )

        return state

    async def quick_analyze(self, device_id: str) -> ScreenState:
        """Quick analysis: capture + OCR only (no YOLO, faster)."""
        start = datetime.utcnow()
        state = ScreenState(device_id=device_id)

        capture = await self._capture.capture_from_adb(device_id)
        if not capture.success or capture.image is None:
            state.error = capture.error
            return state

        state.image_width = capture.width
        state.image_height = capture.height
        state.screenshot_path = capture.filepath or ""

        ocr_result = await self._ocr.extract_text(capture.image)
        state.ocr_texts = ocr_result.texts
        state.full_ocr_text = ocr_result.full_text
        state.ocr_engine = ocr_result.engine_used

        classification = await self._classifier.classify(
            image=capture.image,
            text_content=ocr_result.full_text,
        )
        state.app_name = classification.app_name or ""
        state.screen_type = classification.screen_type.value
        state.screen_name = classification.screen_name or classification.screen_type.value
        state.classification_confidence = classification.confidence

        state.success = True
        state.analysis_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return state

    async def find_element(
        self,
        device_id: str,
        target: str,
        element_type: Optional[str] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[DetectedElement]:
        """Find a specific element on screen by text or type."""
        state = await self.analyze_screen(device_id)
        if not state.success:
            return None

        # Try exact text match first
        element = state.find_element_by_text(target)
        if element:
            return element

        # Try partial text match
        target_lower = target.lower()
        for e in state.elements:
            if e.text and target_lower in e.text.lower():
                if element_type is None or e.element_type == element_type:
                    return e

        # Try by element type
        if element_type:
            if element_type == "button" and state.buttons:
                return state.buttons[0]
            elif element_type == "input_field" and state.inputs:
                return state.inputs[0]
            elif element_type == "send_button":
                return state.find_send_button()
            elif element_type == "search_bar":
                return state.find_search_bar()

        # Try region filter
        if region:
            candidates = state.find_element_in_region(*region, element_type)
            if candidates:
                return candidates[0]

        return None

    def _merge_detections(
        self,
        yolo_result: YOLOResult,
        ui_result: UIDetectionResult,
        ocr_result: PaddleOCRResult,
        img_h: int,
    ) -> List[DetectedElement]:
        """Merge detections from YOLO, UI detector, and OCR into unified elements."""
        elements: List[DetectedElement] = []
        seen_positions: set = set()

        def pos_key(x, y, w, h):
            return (x // 20, y // 20, w // 20, h // 20)

        # Add YOLO detections (highest priority)
        for det in yolo_result.detections:
            key = pos_key(det.x, det.y, det.w, det.h)
            if key not in seen_positions:
                seen_positions.add(key)
                elements.append(DetectedElement(
                    element_type=det.class_name,
                    x=det.x, y=det.y, w=det.w, h=det.h,
                    confidence=det.confidence,
                    source="yolo",
                ))

        # Add UI detector elements (fill gaps)
        for elem in ui_result.elements:
            key = pos_key(elem.x, elem.y, elem.w, elem.h)
            if key not in seen_positions:
                seen_positions.add(key)
                elements.append(DetectedElement(
                    element_type=elem.element_type,
                    x=elem.x, y=elem.y, w=elem.w, h=elem.h,
                    confidence=elem.confidence,
                    text=elem.text or elem.label,
                    label=elem.label,
                    source="ui_detector",
                ))

        # Add OCR-based elements (text regions that look like UI elements)
        for dt in ocr_result.texts:
            key = pos_key(dt.x, dt.y, dt.w, dt.h)
            if key not in seen_positions:
                # Classify text region as potential UI element
                element_type = self._classify_text_as_element(dt.text, dt.x, dt.y, dt.w, dt.h, img_h)
                if element_type != "text_label":
                    seen_positions.add(key)
                    elements.append(DetectedElement(
                        element_type=element_type,
                        x=dt.x, y=dt.y, w=dt.w, h=dt.h,
                        confidence=dt.confidence * 0.8,
                        text=dt.text,
                        source="ocr",
                    ))

        # Sort by confidence
        elements.sort(key=lambda e: e.confidence, reverse=True)

        return elements

    def _classify_text_as_element(
        self, text: str, x: int, y: int, w: int, h: int, img_h: int
    ) -> str:
        text_lower = text.lower().strip()

        button_keywords = [
            "send", "submit", "ok", "done", "next", "back", "cancel", "save",
            "share", "post", "comment", "like", "follow", "message", "call",
            "search", "open", "start", "stop", "delete", "edit", "create",
            "add", "remove", "update", "view", "close", "reply", "forward",
            "yes", "no", "confirm", "accept", "decline",
        ]
        input_keywords = [
            "search", "type", "message", "enter", "input", "find",
            "email", "password", "phone",
        ]

        if any(kw in text_lower for kw in button_keywords):
            return "button"
        if any(kw in text_lower for kw in input_keywords) and w > 100:
            return "input_field"
        if y > img_h * 0.9:
            return "nav_bar"
        return "text_label"


_vision_agent: Optional[VisionAgent] = None


def get_vision_agent() -> VisionAgent:
    global _vision_agent
    if _vision_agent is None:
        _vision_agent = VisionAgent()
    return _vision_agent
