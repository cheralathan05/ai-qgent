import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DetectedText:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    def __post_init__(self):
        if self.bbox and (self.x == 0 or self.y == 0):
            self.x, self.y, self.w, self.h = self.bbox


@dataclass
class OCRResult:
    texts: List[DetectedText] = field(default_factory=list)
    full_text: str = ""
    processed_at: datetime = field(default_factory=datetime.utcnow)
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    error: str = ""

    def get_texts_by_confidence(self, min_confidence: float = 0.3) -> List[DetectedText]:
        return [t for t in self.texts if t.confidence >= min_confidence]

    def has_text(self, text: str, case_sensitive: bool = False) -> bool:
        search = text if case_sensitive else text.lower()
        full = self.full_text if case_sensitive else self.full_text.lower()
        return search in full

    def find_text(self, text: str, case_sensitive: bool = False) -> List[DetectedText]:
        search = text if case_sensitive else text.lower()
        results = []
        for t in self.texts:
            t_text = t.text if case_sensitive else t.text.lower()
            if search in t_text:
                results.append(t)
        return results


class OCRService:
    def __init__(self, languages: Optional[List[str]] = None):
        self._reader = None
        self._languages = languages or ["en"]

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self._languages, gpu=False)
                logger.info(f"EasyOCR reader initialized for {self._languages}")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
        return self._reader

    async def extract_text(self, image: np.ndarray) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(success=False, error="Empty image")
        h, w = image.shape[:2]
        reader = self._get_reader()
        if reader is None:
            return OCRResult(
                full_text="", success=False,
                error="No OCR engine available",
                image_width=w, image_height=h,
            )
        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = reader.readtext(rgb)
            texts = []
            all_text_parts = []
            for bbox, text, confidence in results:
                if confidence < 0.2:
                    continue
                pts = bbox
                x = int(min(p[0] for p in pts))
                y = int(min(p[1] for p in pts))
                x2 = int(max(p[0] for p in pts))
                y2 = int(max(p[1] for p in pts))
                texts.append(DetectedText(
                    text=text.strip(),
                    confidence=float(confidence),
                    bbox=(x, y, x2 - x, y2 - y),
                    x=x, y=y, w=x2 - x, h=y2 - y,
                ))
                all_text_parts.append(text.strip())
            return OCRResult(
                texts=texts,
                full_text=" | ".join(all_text_parts),
                image_width=w, image_height=h,
                success=True,
            )
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return OCRResult(
                full_text="", success=False,
                error=str(e), image_width=w, image_height=h,
            )

    async def extract_text_from_file(self, filepath: str) -> OCRResult:
        image = cv2.imread(filepath)
        if image is None:
            return OCRResult(success=False, error=f"Cannot read {filepath}")
        return await self.extract_text(image)

    @staticmethod
    def visualize_ocr(image: np.ndarray, ocr_result: OCRResult) -> np.ndarray:
        vis = image.copy()
        for dt in ocr_result.texts:
            color = (0, 255, 0) if dt.confidence > 0.7 else (0, 255, 255)
            cv2.rectangle(vis, (dt.x, dt.y), (dt.x + dt.w, dt.y + dt.h), color, 2)
            cv2.putText(vis, f"{dt.text} ({dt.confidence:.2f})", (dt.x, dt.y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        return vis


_ocr_service: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
