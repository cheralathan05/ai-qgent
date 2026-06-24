"""YOLO-based UI element detector for mobile screens.

Uses YOLOv8 for general object detection combined with OCR-based
UI element classification. Falls back to OpenCV contour detection
when YOLO is not available.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# UI element class names for mobile screens
UI_CLASSES = {
    0: "button",
    1: "input_field",
    2: "icon",
    3: "text_label",
    4: "checkbox",
    5: "toggle",
    6: "slider",
    7: "dropdown",
    8: "tab",
    9: "image",
    10: "nav_bar",
    11: "status_bar",
    12: "search_bar",
    13: "send_button",
    14: "back_button",
    15: "menu_button",
}


@dataclass
class YOLODetection:
    class_id: int
    class_name: str
    confidence: float
    x: int
    y: int
    w: int
    h: int

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def area(self) -> int:
        return self.w * self.h

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
        }


@dataclass
class YOLOResult:
    detections: List[YOLODetection] = field(default_factory=list)
    buttons: List[YOLODetection] = field(default_factory=list)
    inputs: List[YOLODetection] = field(default_factory=list)
    icons: List[YOLODetection] = field(default_factory=list)
    search_bars: List[YOLODetection] = field(default_factory=list)
    send_buttons: List[YOLODetection] = field(default_factory=list)
    back_buttons: List[YOLODetection] = field(default_factory=list)
    menu_buttons: List[YOLODetection] = field(default_factory=list)
    text_labels: List[YOLODetection] = field(default_factory=list)
    images: List[YOLODetection] = field(default_factory=list)
    all_elements: List[YOLODetection] = field(default_factory=list)
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    engine_used: str = ""
    processing_time_ms: float = 0.0
    detected_at: datetime = field(default_factory=datetime.utcnow)

    def find_by_class(self, class_name: str) -> List[YOLODetection]:
        return [d for d in self.detections if d.class_name == class_name]

    def find_nearest(self, x: int, y: int, class_name: Optional[str] = None) -> Optional[YOLODetection]:
        candidates = self.detections
        if class_name:
            candidates = [d for d in candidates if d.class_name == class_name]
        if not candidates:
            return None
        best = None
        best_dist = float("inf")
        for d in candidates:
            cx, cy = d.center()
            dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = d
        return best

    def find_in_region(self, x1: int, y1: int, x2: int, y2: int) -> List[YOLODetection]:
        results = []
        for d in self.detections:
            cx, cy = d.center()
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                results.append(d)
        return results


class YOLODetector:
    """YOLO-based UI element detector with contour-based fallback."""

    MIN_BUTTON_AREA = 200
    MAX_BUTTON_AREA_RATIO = 0.3
    MIN_INPUT_HEIGHT = 10

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path or os.environ.get(
            "YOLO_UI_MODEL", ""
        )
        self._yolo_available = None

    def _check_yolo(self) -> bool:
        if self._yolo_available is not None:
            return self._yolo_available
        try:
            from ultralytics import YOLO
            self._yolo_available = True
            logger.info("YOLO detector available (ultralytics)")
        except ImportError:
            self._yolo_available = False
            logger.warning("YOLO not available (ultralytics not installed)")
        return self._yolo_available

    def _get_model(self):
        if self._model is not None:
            return self._model if self._model is not False else None

        if not self._check_yolo():
            self._model = False
            return None

        try:
            from ultralytics import YOLO

            if self._model_path and os.path.isfile(self._model_path):
                self._model = YOLO(self._model_path)
                logger.info(f"Loaded custom YOLO model from {self._model_path}")
            else:
                self._model = YOLO("yolov8n.pt")
                logger.info("Loaded YOLOv8n (nano) model")

            return self._model
        except Exception as e:
            logger.warning(f"Failed to load YOLO model: {e}")
            self._model = False
            return None

    async def detect_elements(self, image: np.ndarray) -> YOLOResult:
        if image is None or image.size == 0:
            return YOLOResult(success=False)

        h, w = image.shape[:2]
        start = datetime.utcnow()

        model = self._get_model()
        if model is not None:
            result = await self._yolo_detect(model, image, w, h)
            result.processing_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
            return result

        result = await self._contour_detect(image, w, h)
        result.processing_time_ms = (datetime.utcnow() - start).total_seconds() * 1000
        return result

    async def _yolo_detect(
        self, model, image: np.ndarray, w: int, h: int
    ) -> YOLOResult:
        try:
            results = model(image, verbose=False, conf=0.3)
        except Exception as e:
            logger.warning(f"YOLO detection failed: {e}")
            return await self._contour_detect(image, w, h)

        detections = []
        buttons = []
        inputs = []
        icons = []
        search_bars = []
        send_buttons = []
        back_buttons = []
        menu_buttons = []
        text_labels = []
        images = []

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                class_name = UI_CLASSES.get(cls_id, f"class_{cls_id}")

                det = YOLODetection(
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=conf,
                    x=x1, y=y1, w=x2 - x1, h=y2 - y1,
                )
                detections.append(det)

                if class_name == "button":
                    buttons.append(det)
                elif class_name == "input_field":
                    inputs.append(det)
                elif class_name in ("icon", "back_button", "menu_button", "send_button"):
                    icons.append(det)
                    if class_name == "send_button":
                        send_buttons.append(det)
                    elif class_name == "back_button":
                        back_buttons.append(det)
                    elif class_name == "menu_button":
                        menu_buttons.append(det)
                elif class_name == "search_bar":
                    search_bars.append(det)
                elif class_name == "text_label":
                    text_labels.append(det)
                elif class_name == "image":
                    images.append(det)

        logger.info(f"YOLO detected {len(detections)} elements")

        return YOLOResult(
            detections=detections,
            buttons=buttons,
            inputs=inputs,
            icons=icons,
            search_bars=search_bars,
            send_buttons=send_buttons,
            back_buttons=back_buttons,
            menu_buttons=menu_buttons,
            text_labels=text_labels,
            images=images,
            all_elements=detections,
            image_width=w,
            image_height=h,
            success=True,
            engine_used="yolo",
        )

    async def _contour_detect(
        self, image: np.ndarray, w: int, h: int
    ) -> YOLOResult:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img_area = w * h

        detections = []
        buttons = []
        icons = []
        inputs = []

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch
            if area < self.MIN_BUTTON_AREA or area > img_area * self.MAX_BUTTON_AREA_RATIO:
                continue
            aspect = cw / ch if ch > 0 else 0
            if aspect < 0.3 or aspect > 10:
                continue

            is_clickable = aspect > 1.5 and cw < w * 0.8
            is_icon = 0.5 <= aspect <= 2.0 and area < 10000
            is_input = aspect > 2 and ch < h * 0.1

            class_name = "button" if is_clickable else ("icon" if is_icon else ("input_field" if is_input else "text_label"))

            det = YOLODetection(
                class_id=0,
                class_name=class_name,
                confidence=0.5,
                x=x, y=y, w=cw, h=ch,
            )
            detections.append(det)

            if class_name == "button":
                buttons.append(det)
            elif class_name == "icon":
                icons.append(det)
            elif class_name == "input_field":
                inputs.append(det)

        bottom_y = int(h * 0.9)
        nav_buttons = [d for d in buttons if d.y > bottom_y]
        for nb in nav_buttons:
            nb.class_name = "nav_bar"

        logger.info(f"Contour detection found {len(detections)} elements")

        return YOLOResult(
            detections=detections,
            buttons=buttons,
            inputs=inputs,
            icons=icons,
            all_elements=detections,
            image_width=w,
            image_height=h,
            success=True,
            engine_used="contour",
        )

    def classify_element_from_text(
        self, text: str, x: int, y: int, w: int, h: int, img_h: int
    ) -> str:
        text_lower = text.lower().strip()

        button_keywords = [
            "send", "submit", "ok", "done", "next", "back", "cancel", "save",
            "share", "post", "comment", "like", "follow", "message", "call",
            "search", "open", "start", "stop", "delete", "edit", "create",
            "add", "remove", "update", "view", "close", "reply", "forward",
            "yes", "no", "confirm", "accept", "decline", "retry", "continue",
            "sign in", "log in", "login", "sign up", "register",
        ]

        input_keywords = [
            "search", "type", "message", "enter", "input", "find",
            "email", "password", "phone", "name", "subject",
        ]

        if any(kw in text_lower for kw in button_keywords):
            return "button"
        if any(kw in text_lower for kw in input_keywords):
            return "input_field"
        if y > img_h * 0.9:
            return "nav_bar"
        return "text_label"


_yolo_detector: Optional[YOLODetector] = None


def get_yolo_detector() -> YOLODetector:
    global _yolo_detector
    if _yolo_detector is None:
        _yolo_detector = YOLODetector()
    return _yolo_detector
