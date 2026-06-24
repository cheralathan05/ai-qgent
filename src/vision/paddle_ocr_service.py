"""PaddleOCR-based OCR service with fallback chain.

Provides significantly better accuracy than EasyOCR for mobile UI text detection.
Engine chain: PaddleOCR -> EasyOCR -> Tesseract
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PaddleDetectedText:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    angle: float = 0.0

    def __post_init__(self):
        if self.bbox and (self.x == 0 or self.y == 0):
            self.x, self.y, self.w, self.h = self.bbox


@dataclass
class PaddleOCRResult:
    texts: List[PaddleDetectedText] = field(default_factory=list)
    full_text: str = ""
    processed_at: datetime = field(default_factory=datetime.utcnow)
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    error: str = ""
    engine_used: str = ""
    processing_time_ms: float = 0.0
    confidence_avg: float = 0.0

    def get_texts_by_confidence(self, min_confidence: float = 0.3) -> List[PaddleDetectedText]:
        return [t for t in self.texts if t.confidence >= min_confidence]

    def has_text(self, text: str, case_sensitive: bool = False) -> bool:
        search = text if case_sensitive else text.lower()
        full = self.full_text if case_sensitive else self.full_text.lower()
        return search in full

    def find_text(self, text: str, case_sensitive: bool = False) -> List[PaddleDetectedText]:
        search = text if case_sensitive else text.lower()
        results = []
        for t in self.texts:
            t_text = t.text if case_sensitive else t.text.lower()
            if search in t_text:
                results.append(t)
        return results

    def find_text_near(
        self, text: str, x: int, y: int, max_distance: int = 200, case_sensitive: bool = False
    ) -> Optional[PaddleDetectedText]:
        matches = self.find_text(text, case_sensitive)
        if not matches:
            return None
        best = None
        best_dist = float("inf")
        for m in matches:
            cx, cy = m.x + m.w // 2, m.y + m.h // 2
            dist = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5
            if dist < best_dist and dist <= max_distance:
                best_dist = dist
                best = m
        return best

    def find_text_in_region(
        self, x1: int, y1: int, x2: int, y2: int, case_sensitive: bool = False
    ) -> List[PaddleDetectedText]:
        results = []
        for t in self.texts:
            tx, ty = t.x + t.w // 2, t.y + t.h // 2
            if x1 <= tx <= x2 and y1 <= ty <= y2:
                results.append(t)
        return results


class PaddleOCRService:
    """Multi-engine OCR service with PaddleOCR as primary engine.

    Falls back to EasyOCR and Tesseract if PaddleOCR is unavailable.
    """

    def __init__(self, languages: Optional[List[str]] = None):
        self._paddle_reader = None
        self._easyocr_reader = None
        self._tesseract_available = None
        self._languages = languages or ["en"]
        self._ocr_enabled = os.environ.get("OCR_ENABLED", "true").lower() != "false"
        self._engines_checked = False
        self._available_engines: List[str] = []
        self._primary_engine = "paddleocr"

    def _check_engines(self):
        if self._engines_checked:
            return

        try:
            from paddleocr import PaddleOCR
            self._available_engines.append("paddleocr")
            logger.info("OCR engine available: PaddleOCR")
        except ImportError:
            logger.warning("OCR engine NOT available: PaddleOCR (not installed)")

        try:
            import easyocr
            self._available_engines.append("easyocr")
            logger.info("OCR engine available: EasyOCR")
        except ImportError:
            logger.warning("OCR engine NOT available: EasyOCR (not installed)")

        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._available_engines.append("tesseract")
            logger.info("OCR engine available: Tesseract")
        except Exception:
            logger.warning("OCR engine NOT available: Tesseract (not installed or not in PATH)")

        self._engines_checked = True

        if not self._available_engines:
            logger.error("NO OCR ENGINES AVAILABLE - OCR will always return empty results")

    def get_engine_status(self) -> dict:
        self._check_engines()
        return {
            "ocr_enabled": self._ocr_enabled,
            "engines": self._available_engines,
            "paddle_available": "paddleocr" in self._available_engines,
            "easyocr_available": "easyocr" in self._available_engines,
            "tesseract_available": "tesseract" in self._available_engines,
            "primary_engine": self._primary_engine,
        }

    def _get_paddle_reader(self):
        if self._paddle_reader is None:
            try:
                from paddleocr import PaddleOCR
                logger.info("Initializing PaddleOCR...")
                self._paddle_reader = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    use_gpu=False,
                    show_log=False,
                    det=True,
                    rec=True,
                    cls=True,
                )
                logger.info("PaddleOCR initialized successfully")
            except Exception as e:
                logger.warning(f"PaddleOCR initialization failed: {e}")
                self._paddle_reader = False
        return self._paddle_reader

    def _get_easyocr_reader(self):
        if self._easyocr_reader is None:
            try:
                import easyocr
                logger.info("Initializing EasyOCR reader...")
                self._easyocr_reader = easyocr.Reader(self._languages, gpu=False)
                logger.info(f"EasyOCR reader initialized for {self._languages}")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
                self._easyocr_reader = False
        return self._easyocr_reader

    def _preprocess_for_ocr(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        gray = cv2.fastNlMeansDenoising(gray, h=10)

        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        return gray, binary

    def _paddle_extract(self, image: np.ndarray, reader) -> List[PaddleDetectedText]:
        texts = []
        try:
            if len(image.shape) == 2:
                rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            result = reader.ocr(rgb, cls=True)

            if not result or not result[0]:
                return texts

            for line in result[0]:
                bbox_points = line[0]
                text = line[1][0]
                confidence = float(line[1][1])

                if confidence < 0.15:
                    continue

                xs = [int(p[0]) for p in bbox_points]
                ys = [int(p[1]) for p in bbox_points]
                x = min(xs)
                y = min(ys)
                x2 = max(xs)
                y2 = max(ys)
                w = x2 - x
                h = y2 - y

                if w <= 0 or h <= 0:
                    continue

                texts.append(PaddleDetectedText(
                    text=text.strip(),
                    confidence=confidence,
                    bbox=(x, y, w, h),
                    x=x, y=y, w=w, h=h,
                ))

        except Exception as e:
            logger.warning(f"PaddleOCR extraction failed: {e}")
        return texts

    def _easyocr_extract(self, image: np.ndarray, reader) -> List[PaddleDetectedText]:
        texts = []
        try:
            if len(image.shape) == 2:
                rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            results = reader.readtext(rgb)
            for bbox, text, confidence in results:
                if confidence < 0.15:
                    continue
                pts = bbox
                x = int(min(p[0] for p in pts))
                y = int(min(p[1] for p in pts))
                x2 = int(max(p[0] for p in pts))
                y2 = int(max(p[1] for p in pts))
                texts.append(PaddleDetectedText(
                    text=text.strip(),
                    confidence=float(confidence),
                    bbox=(x, y, x2 - x, y2 - y),
                    x=x, y=y, w=x2 - x, h=y2 - y,
                ))
        except Exception as e:
            logger.warning(f"EasyOCR extraction failed: {e}")
        return texts

    def _tesseract_extract(self, image: np.ndarray) -> List[PaddleDetectedText]:
        texts = []
        try:
            import pytesseract
            from PIL import Image as PILImage

            pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = int(data["conf"][i]) / 100.0 if data["conf"][i] != "-1" else 0.0
                if text and conf >= 0.2:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    if w > 0 and h > 0:
                        texts.append(PaddleDetectedText(
                            text=text.strip(),
                            confidence=conf,
                            bbox=(x, y, w, h),
                            x=x, y=y, w=w, h=h,
                        ))
        except ImportError:
            logger.warning("pytesseract not installed")
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
        return texts

    async def extract_text(self, image: np.ndarray) -> PaddleOCRResult:
        if not self._ocr_enabled:
            return PaddleOCRResult(
                success=False, error="OCR is disabled (OCR_ENABLED=false)",
                image_width=image.shape[1] if image is not None and image.size > 0 else 0,
                image_height=image.shape[0] if image is not None and image.size > 0 else 0,
            )

        if image is None or image.size == 0:
            return PaddleOCRResult(success=False, error="Empty image")

        self._check_engines()

        h, w = image.shape[:2]
        start_time = time.time()

        logger.info(f"OCR START - image size: {w}x{h}, engines: {self._available_engines}")

        if not self._available_engines:
            elapsed = (time.time() - start_time) * 1000
            return PaddleOCRResult(
                success=False,
                error="No OCR engines available",
                image_width=w, image_height=h,
                processing_time_ms=elapsed,
            )

        gray, binary = self._preprocess_for_ocr(image)

        # Strategy 1: PaddleOCR on original (best accuracy)
        if "paddleocr" in self._available_engines:
            reader = self._get_paddle_reader()
            if reader and reader is not False:
                logger.info("OCR: Trying PaddleOCR on original image...")
                texts = self._paddle_extract(image, reader)

                if not texts:
                    logger.info("OCR: PaddleOCR found nothing, trying preprocessed...")
                    texts = self._paddle_extract(
                        cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), reader
                    )

                if not texts:
                    logger.info("OCR: Trying PaddleOCR on binary image...")
                    texts = self._paddle_extract(
                        cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR), reader
                    )

                if texts:
                    elapsed = (time.time() - start_time) * 1000
                    full_text = " | ".join(t.text for t in texts)
                    avg_conf = sum(t.confidence for t in texts) / len(texts) if texts else 0
                    logger.info(
                        f"OCR RESULT (PaddleOCR) - text_count={len(texts)}, "
                        f"avg_confidence={avg_conf:.2f}, time={elapsed:.0f}ms"
                    )
                    return PaddleOCRResult(
                        texts=texts,
                        full_text=full_text,
                        image_width=w, image_height=h,
                        success=True,
                        engine_used="paddleocr",
                        processing_time_ms=elapsed,
                        confidence_avg=avg_conf,
                    )

        # Strategy 2: EasyOCR fallback
        if "easyocr" in self._available_engines:
            reader = self._get_easyocr_reader()
            if reader and reader is not False:
                logger.info("OCR: Trying EasyOCR on original image...")
                texts = self._easyocr_extract(image, reader)

                if not texts:
                    logger.info("OCR: Trying EasyOCR on preprocessed...")
                    texts = self._easyocr_extract(
                        cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), reader
                    )

                if texts:
                    elapsed = (time.time() - start_time) * 1000
                    full_text = " | ".join(t.text for t in texts)
                    avg_conf = sum(t.confidence for t in texts) / len(texts) if texts else 0
                    logger.info(
                        f"OCR RESULT (EasyOCR) - text_count={len(texts)}, "
                        f"avg_confidence={avg_conf:.2f}, time={elapsed:.0f}ms"
                    )
                    return PaddleOCRResult(
                        texts=texts,
                        full_text=full_text,
                        image_width=w, image_height=h,
                        success=True,
                        engine_used="easyocr",
                        processing_time_ms=elapsed,
                        confidence_avg=avg_conf,
                    )

        # Strategy 3: Tesseract fallback
        if "tesseract" in self._available_engines:
            logger.info("OCR: Trying Tesseract fallback...")
            texts = self._tesseract_extract(image)
            if texts:
                elapsed = (time.time() - start_time) * 1000
                full_text = " | ".join(t.text for t in texts)
                avg_conf = sum(t.confidence for t in texts) / len(texts) if texts else 0
                logger.info(
                    f"OCR RESULT (Tesseract) - text_count={len(texts)}, "
                    f"avg_confidence={avg_conf:.2f}, time={elapsed:.0f}ms"
                )
                return PaddleOCRResult(
                    texts=texts,
                    full_text=full_text,
                    image_width=w, image_height=h,
                    success=True,
                    engine_used="tesseract",
                    processing_time_ms=elapsed,
                    confidence_avg=avg_conf,
                )

        elapsed = (time.time() - start_time) * 1000
        logger.warning(f"OCR: No text detected in {w}x{h} image after {elapsed:.0f}ms")
        return PaddleOCRResult(
            texts=[],
            full_text="",
            image_width=w, image_height=h,
            success=False,
            error="No text detected in image",
            engine_used="none",
            processing_time_ms=elapsed,
        )

    async def extract_text_from_file(self, filepath: str) -> PaddleOCRResult:
        logger.info(f"OCR: Reading file {filepath}")
        image = cv2.imread(filepath)
        if image is None:
            return PaddleOCRResult(success=False, error=f"Cannot read {filepath}")
        return await self.extract_text(image)

    @staticmethod
    def visualize_ocr(image: np.ndarray, ocr_result: PaddleOCRResult) -> np.ndarray:
        vis = image.copy()
        for dt in ocr_result.texts:
            color = (0, 255, 0) if dt.confidence > 0.7 else (0, 255, 255)
            cv2.rectangle(vis, (dt.x, dt.y), (dt.x + dt.w, dt.y + dt.h), color, 2)
            cv2.putText(
                vis, f"{dt.text} ({dt.confidence:.2f})", (dt.x, dt.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1,
            )
        return vis


_paddle_ocr_service: Optional[PaddleOCRService] = None


def get_paddle_ocr_service() -> PaddleOCRService:
    global _paddle_ocr_service
    if _paddle_ocr_service is None:
        _paddle_ocr_service = PaddleOCRService()
    return _paddle_ocr_service
