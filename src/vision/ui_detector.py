import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import cv2
import numpy as np

from vision.ocr_service import get_ocr_service, DetectedText

logger = logging.getLogger(__name__)


@dataclass
class DetectedUIElement:
    element_type: str
    x: int
    y: int
    w: int
    h: int
    confidence: float
    label: str = ""
    text: str = ""
    content_description: str = ""

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def area(self) -> int:
        return self.w * self.h

    def to_dict(self) -> dict:
        return {
            "type": self.element_type,
            "label": self.label,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "confidence": self.confidence,
        }


@dataclass
class UIDetectionResult:
    elements: List[DetectedUIElement] = field(default_factory=list)
    buttons: List[DetectedUIElement] = field(default_factory=list)
    inputs: List[DetectedUIElement] = field(default_factory=list)
    icons: List[DetectedUIElement] = field(default_factory=list)
    tabs: List[DetectedUIElement] = field(default_factory=list)
    menus: List[DetectedUIElement] = field(default_factory=list)
    images: List[DetectedUIElement] = field(default_factory=list)
    text_regions: List[DetectedUIElement] = field(default_factory=list)
    text_content: str = ""
    detected_at: datetime = field(default_factory=datetime.utcnow)
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    error: str = ""


class UIDetector:
    MIN_BUTTON_AREA = 200
    MAX_BUTTON_AREA_RATIO = 0.3
    MIN_INPUT_HEIGHT = 10
    TAB_HEIGHT_RATIO = 0.06
    BOTTOM_BAR_RATIO = 0.1

    def __init__(self):
        self._ocr = get_ocr_service()

    async def detect_elements(self, image: np.ndarray) -> UIDetectionResult:
        if image is None or image.size == 0:
            return UIDetectionResult(success=False, error="Empty image")
        h, w = image.shape[:2]

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        ocr_result = await self._ocr.extract_text(image)

        text_regions = self._detect_text_regions_from_ocr(ocr_result)
        buttons = self._detect_buttons(gray, binary, image, ocr_result, w, h)
        inputs = self._detect_inputs(gray, binary, ocr_result, w, h)
        icons = self._detect_icons(binary, w, h)
        tabs = self._detect_tabs(buttons, ocr_result, h)
        menus = self._detect_menus(buttons, h)
        images = self._detect_images(gray, w, h)

        # Enhanced button detection from OCR text
        for dt in ocr_result.texts:
            txt_lower = dt.text.lower().strip()
            # Detect buttons from text that looks like buttons
            if dt.h < h * 0.08 and dt.w > 20 and dt.h > 10:
                button_keywords = [
                    "send", "submit", "ok", "done", "next", "back", "cancel", "save",
                    "share", "post", "comment", "like", "follow", "message", "call",
                    "search", "open", "start", "stop", "delete", "edit", "create",
                    "add", "remove", "update", "view", "close", "reply", "forward",
                    "yes", "no", "confirm", "accept", "decline", "retry", "continue",
                    "sign in", "log in", "login", "sign up", "register",
                ]
                is_button_text = any(kw in txt_lower for kw in button_keywords)
                if is_button_text:
                    # Check if a button already exists near this text
                    nearby = [b for b in buttons if abs(b.x - dt.x) < 50 and abs(b.y - dt.y) < 30]
                    if not nearby:
                        buttons.append(DetectedUIElement(
                            element_type="button",
                            x=max(0, dt.x - 10), y=max(0, dt.y - 5),
                            w=dt.w + 20, h=dt.h + 10,
                            confidence=dt.confidence * 0.9,
                            label=dt.text, text=dt.text,
                        ))

        # Detect input fields from OCR hints
        input_keywords = ["search", "type", "message", "enter", "input", "find", "email", "password"]
        for dt in ocr_result.texts:
            txt_lower = dt.text.lower().strip()
            if any(kw in txt_lower for kw in input_keywords):
                # Check if this looks like a placeholder text (usually lighter color, smaller)
                nearby_inputs = [i for i in inputs if abs(i.x - dt.x) < 50 and abs(i.y - dt.y) < 30]
                if not nearby_inputs and dt.w > 100:
                    inputs.append(DetectedUIElement(
                        element_type="input",
                        x=max(0, dt.x - 10), y=max(0, dt.y - 5),
                        w=dt.w + 20, h=dt.h + 10,
                        confidence=dt.confidence * 0.7,
                        label=dt.text, text=dt.text,
                    ))

        all_elements = buttons + inputs + icons + tabs + menus + images + text_regions

        return UIDetectionResult(
            elements=all_elements,
            buttons=buttons,
            inputs=inputs,
            icons=icons,
            tabs=tabs,
            menus=menus,
            images=images,
            text_regions=text_regions,
            text_content=ocr_result.full_text,
            image_width=w,
            image_height=h,
            success=True,
        )

    def _overlaps(self, a, b) -> bool:
        if not hasattr(a, 'x') or not hasattr(b, 'x'):
            return False
        return (a.x < b.x + b.w and a.x + a.w > b.x and
                a.y < b.y + b.h and a.y + a.h > b.y)

    def _detect_text_regions_from_ocr(self, ocr_result) -> List[DetectedUIElement]:
        regions = []
        for dt in ocr_result.texts:
            regions.append(DetectedUIElement(
                element_type="text",
                x=dt.x, y=dt.y, w=dt.w, h=dt.h,
                confidence=dt.confidence,
                label=dt.text,
                text=dt.text,
            ))
        return regions

    def _detect_buttons(self, gray: np.ndarray, binary: np.ndarray, image: np.ndarray,
                        ocr_result, img_w: int, img_h: int) -> List[DetectedUIElement]:
        buttons = []

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img_area = img_w * img_h

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < self.MIN_BUTTON_AREA or area > img_area * self.MAX_BUTTON_AREA_RATIO:
                continue
            aspect = w / h if h > 0 else 0
            if aspect < 0.5 or aspect > 8:
                continue

            label = ""
            for dt in ocr_result.texts:
                if (dt.x >= x - 5 and dt.y >= y - 5 and
                    dt.x + dt.w <= x + w + 5 and dt.y + dt.h <= y + h + 5):
                    label = dt.text
                    break

            is_clickable = aspect > 1.5 and w < img_w * 0.8

            button_types = [".btn", "button", "android.widget.button"]

            element_type = "button" if (is_clickable or label) else "unknown"

            if element_type == "button":
                buttons.append(DetectedUIElement(
                    element_type="button",
                    x=x, y=y, w=w, h=h,
                    confidence=0.6,
                    label=label,
                    text=label,
                ))

        bottom_y = img_h * (1 - self.BOTTOM_BAR_RATIO)
        nav_buttons = [b for b in buttons if b.y > bottom_y]
        for nb in nav_buttons:
            nb.element_type = "nav_button"

        return buttons

    def _detect_inputs(self, gray: np.ndarray, binary: np.ndarray,
                       ocr_result, img_w: int, img_h: int) -> List[DetectedUIElement]:
        inputs = []

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(binary, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h < self.MIN_INPUT_HEIGHT or w < 50:
                continue
            aspect = w / h if h > 0 else 0
            if aspect < 2 or aspect > 20:
                continue
            if y < img_h * 0.05 or y > img_h * 0.95:
                continue

            label = ""
            for dt in ocr_result.texts:
                dt_bottom = dt.y + dt.h
                if abs(dt_bottom - y) < 10 and dt.x < x + w and dt.x + dt.w > x:
                    label = dt.text
                    break

            roi = gray[y:y + min(h, 50), x:x + w]
            if roi.size == 0:
                continue
            bottom_edge = np.mean(roi[-3:, :]) if roi.shape[0] >= 3 else 0
            has_bottom_line = bottom_edge < 80

            if has_bottom_line or h < 60:
                inputs.append(DetectedUIElement(
                    element_type="input",
                    x=x, y=y, w=w, h=h,
                    confidence=0.5,
                    label=label,
                    text=label,
                ))

        return inputs

    def _detect_icons(self, binary: np.ndarray, img_w: int, img_h: int) -> List[DetectedUIElement]:
        icons = []
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        eroded = cv2.erode(binary, kernel, iterations=1)

        contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < 200 or area > 10000:
                continue
            aspect = w / h if h > 0 else 0
            if aspect < 0.5 or aspect > 2.0:
                continue

            icons.append(DetectedUIElement(
                element_type="icon",
                x=x, y=y, w=w, h=h,
                confidence=0.4,
            ))

        return icons

    def _detect_tabs(self, buttons: List[DetectedUIElement], ocr_result,
                     img_h: int) -> List[DetectedUIElement]:
        tabs = []
        max_tab_height = img_h * self.TAB_HEIGHT_RATIO

        top_buttons = [b for b in buttons if b.y < img_h * 0.15]
        if len(top_buttons) >= 2:
            sorted_btns = sorted(top_buttons, key=lambda b: b.x)
            gaps = [sorted_btns[i + 1].x - (sorted_btns[i].x + sorted_btns[i].w)
                    for i in range(len(sorted_btns) - 1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            if avg_gap < 20:
                for tb in top_buttons:
                    tabs.append(DetectedUIElement(
                        element_type="tab",
                        x=tb.x, y=tb.y, w=tb.w, h=tb.h,
                        confidence=0.7,
                        label=tb.label,
                        text=tb.text,
                    ))

        return tabs

    def _detect_menus(self, buttons: List[DetectedUIElement], img_h: int) -> List[DetectedUIElement]:
        menus = []
        top_buttons = sorted([b for b in buttons if b.y < img_h * 0.12], key=lambda b: b.x)

        rightmost = None
        for tb in top_buttons:
            if tb.label.lower() in ("menu", "more", "options", "⋮", "•••") or tb.x > 800:
                rightmost = tb

        if rightmost:
            menus.append(DetectedUIElement(
                element_type="menu",
                x=rightmost.x, y=rightmost.y,
                w=rightmost.w, h=rightmost.h,
                confidence=0.8,
                label="menu",
                text=rightmost.label,
            ))

        return menus

    def _detect_images(self, gray: np.ndarray, img_w: int, img_h: int) -> List[DetectedUIElement]:
        images = []
        edges = cv2.Canny(gray, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            img_area = img_w * img_h
            if area < img_area * 0.01 or area > img_area * 0.6:
                continue
            aspect = w / h if h > 0 else 0
            if aspect < 0.3 or aspect > 3.0:
                continue

            images.append(DetectedUIElement(
                element_type="image",
                x=x, y=y, w=w, h=h,
                confidence=0.5,
            ))

        return images

    def classify_element_type(self, element: DetectedUIElement, ocr_result) -> str:
        text_lower = element.text.lower()
        if any(word in text_lower for word in ("send", "submit", "ok", "done", "next", "go", "post", "share")):
            return "action_button"
        if any(word in text_lower for word in ("cancel", "back", "close", "dismiss")):
            return "dismiss_button"
        if any(word in text_lower for word in ("search", "find", "look up")):
            return "search_button"
        return element.element_type


_ui_detector: Optional[UIDetector] = None


def get_ui_detector() -> UIDetector:
    global _ui_detector
    if _ui_detector is None:
        _ui_detector = UIDetector()
    return _ui_detector
