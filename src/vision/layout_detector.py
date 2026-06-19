import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

import cv2
import numpy as np

from vision.ui_detector import DetectedUIElement

logger = logging.getLogger(__name__)


class SectionType(str, Enum):
    TOP_BAR = "top_bar"
    BOTTOM_BAR = "bottom_bar"
    CONTENT_AREA = "content_area"
    SIDE_MENU = "side_menu"
    LIST = "list"
    GRID = "grid"
    MODAL = "modal"
    DIALOG = "dialog"
    POPUP = "popup"
    TAB_BAR = "tab_bar"
    CARD = "card"
    HEADER = "header"
    FOOTER = "footer"
    UNKNOWN = "unknown"


@dataclass
class LayoutSection:
    section_type: SectionType
    x: int
    y: int
    w: int
    h: int
    confidence: float
    elements: List[DetectedUIElement] = field(default_factory=list)
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.section_type.value,
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "confidence": self.confidence,
            "label": self.label,
            "elements": [e.to_dict() for e in self.elements],
        }


@dataclass
class LayoutResult:
    sections: List[LayoutSection] = field(default_factory=list)
    layout_type: str = "unknown"
    image_width: int = 0
    image_height: int = 0
    detected_at: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    error: str = ""

    def has_section(self, section_type: SectionType) -> bool:
        return any(s.section_type == section_type for s in self.sections)

    def get_section(self, section_type: SectionType) -> Optional[LayoutSection]:
        for s in self.sections:
            if s.section_type == section_type:
                return s
        return None


class LayoutDetector:
    TOP_BAR_HEIGHT_RATIO = 0.08
    BOTTOM_BAR_HEIGHT_RATIO = 0.08
    MIN_MODAL_AREA_RATIO = 0.3
    MAX_MODAL_AREA_RATIO = 0.85

    def __init__(self):
        pass

    async def detect_layout(self, image: np.ndarray,
                            elements: Optional[List[DetectedUIElement]] = None) -> LayoutResult:
        if image is None or image.size == 0:
            return LayoutResult(success=False, error="Empty image")
        h, w = image.shape[:2]

        sections = []

        top_bar = self._detect_top_bar(image, w, h)
        if top_bar:
            sections.append(top_bar)

        bottom_bar = self._detect_bottom_bar(image, w, h, elements or [])
        if bottom_bar:
            sections.append(bottom_bar)

        modal = self._detect_modal(image, w, h)
        if modal:
            sections.append(modal)

        if not modal:
            content = self._detect_content_area(image, w, h, top_bar, bottom_bar)
            if content:
                sections.append(content)

                list_sections = self._detect_list_items(image, content, w, h)
                sections.extend(list_sections)

                grid = self._detect_grid(image, content, w, h)
                if grid:
                    sections.extend(grid)

        tab_bar = self._detect_tab_bar(elements or [], h)
        if tab_bar:
            sections.append(tab_bar)

        dialogs = self._detect_dialogs(image, elements or [], w, h)
        sections.extend(dialogs)

        layout_type = self._classify_layout_type(sections, w, h)

        return LayoutResult(
            sections=sections,
            layout_type=layout_type,
            image_width=w, image_height=h,
            success=True,
        )

    def _detect_top_bar(self, image: np.ndarray, img_w: int, img_h: int) -> Optional[LayoutSection]:
        bar_height = int(img_h * self.TOP_BAR_HEIGHT_RATIO)
        roi = image[0:bar_height, :]
        if roi.size == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        if mean_brightness < 30:
            return None

        std_val = np.std(gray)
        if std_val < 10:
            return None

        return LayoutSection(
            section_type=SectionType.TOP_BAR,
            x=0, y=0, w=img_w, h=bar_height,
            confidence=0.7,
        )

    def _detect_bottom_bar(self, image: np.ndarray, img_w: int, img_h: int,
                           elements: List[DetectedUIElement]) -> Optional[LayoutSection]:
        bar_height = int(img_h * self.BOTTOM_BAR_HEIGHT_RATIO)
        y_start = img_h - bar_height
        roi = image[y_start:img_h, :]
        if roi.size == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        if mean_brightness < 30:
            return None

        bottom_elements = [e for e in elements if e.y > y_start and e.y + e.h <= img_h]
        if not bottom_elements and np.std(gray) < 10:
            return None

        return LayoutSection(
            section_type=SectionType.BOTTOM_BAR,
            x=0, y=y_start, w=img_w, h=bar_height,
            confidence=0.7,
            elements=bottom_elements,
        )

    def _detect_content_area(self, image: np.ndarray, img_w: int, img_h: int,
                             top_bar: Optional[LayoutSection],
                             bottom_bar: Optional[LayoutSection]) -> Optional[LayoutSection]:
        y_start = top_bar.h if top_bar else 0
        y_end = (img_h - bottom_bar.h) if bottom_bar else img_h
        if y_end <= y_start:
            return None
        return LayoutSection(
            section_type=SectionType.CONTENT_AREA,
            x=0, y=y_start, w=img_w, h=y_end - y_start,
            confidence=0.9,
        )

    def _detect_list_items(self, image: np.ndarray, content_area: LayoutSection,
                           img_w: int, img_h: int) -> List[LayoutSection]:
        lists = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        has_separators = np.sum(horizontal_lines) / 255 > 5

        if has_separators:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

            contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            items = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if (y < content_area.y or y + h > content_area.y + content_area.h):
                    continue
                if w < img_w * 0.3 or h < 20 or h > img_h * 0.2:
                    continue
                items.append(LayoutSection(
                    section_type=SectionType.LIST,
                    x=x, y=y, w=w, h=h,
                    confidence=0.6,
                ))

            if len(items) >= 2:
                lists.extend(items)

        return lists

    def _detect_grid(self, image: np.ndarray, content_area: LayoutSection,
                     img_w: int, img_h: int) -> List[LayoutSection]:
        grids = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        v_count = np.sum(vertical_lines) / 255
        h_count = np.sum(horizontal_lines) / 255

        if v_count > h_count * 0.5 and h_count > 5:
            grids.append(LayoutSection(
                section_type=SectionType.GRID,
                x=content_area.x, y=content_area.y,
                w=content_area.w, h=content_area.h,
                confidence=0.5,
            ))

        return grids

    def _detect_modal(self, image: np.ndarray, img_w: int, img_h: int) -> Optional[LayoutSection]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        img_area = img_w * img_h
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < img_area * self.MIN_MODAL_AREA_RATIO:
                continue
            if area > img_area * self.MAX_MODAL_AREA_RATIO:
                continue
            aspect = w / h if h > 0 else 0
            if aspect < 0.5 or aspect > 2.0:
                continue

            if y > img_h * 0.1 and y + h < img_h * 0.9:
                return LayoutSection(
                    section_type=SectionType.MODAL,
                    x=x, y=y, w=w, h=h,
                    confidence=0.6,
                )

        return None

    def _detect_dialogs(self, image: np.ndarray, elements: List[DetectedUIElement],
                        img_w: int, img_h: int) -> List[LayoutSection]:
        dialogs = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img_area = img_w * img_h

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < img_area * 0.1 or area > img_area * 0.5:
                continue
            if y < img_h * 0.15 or y + h > img_h * 0.85:
                continue

            dialog_btns = [e for e in elements if e.x >= x and e.y >= y and e.x + e.w <= x + w and e.y + e.h <= y + h]
            has_buttons = len(dialog_btns) >= 1

            if has_buttons:
                dialogs.append(LayoutSection(
                    section_type=SectionType.DIALOG,
                    x=x, y=y, w=w, h=h,
                    confidence=0.7,
                    elements=dialog_btns,
                ))

        return dialogs

    def _detect_tab_bar(self, elements: List[DetectedUIElement],
                        img_h: int) -> Optional[LayoutSection]:
        tab_elements = [e for e in elements if e.element_type == "tab"]
        if not tab_elements:
            return None

        min_y = min(e.y for e in tab_elements)
        max_y = max(e.y + e.h for e in tab_elements)
        min_x = min(e.x for e in tab_elements)
        max_x = max(e.x + e.w for e in tab_elements)

        if tab_elements and min_y > img_h * 0.7:
            return LayoutSection(
                section_type=SectionType.TAB_BAR,
                x=min_x, y=min_y, w=max_x - min_x, h=max_y - min_y,
                confidence=0.8,
                elements=tab_elements,
            )

        return None

    def _classify_layout_type(self, sections: List[LayoutSection],
                              img_w: int, img_h: int) -> str:
        types = [s.section_type for s in sections]
        if SectionType.MODAL in types:
            return "modal"
        if SectionType.DIALOG in types:
            return "dialog"
        if SectionType.GRID in types:
            return "grid"
        if SectionType.LIST in types:
            return "list"
        if SectionType.TOP_BAR in types and SectionType.BOTTOM_BAR in types:
            return "standard_app"
        if SectionType.TOP_BAR in types:
            return "top_bar_only"
        return "unknown"


_layout_detector: Optional[LayoutDetector] = None


def get_layout_detector() -> LayoutDetector:
    global _layout_detector
    if _layout_detector is None:
        _layout_detector = LayoutDetector()
    return _layout_detector
