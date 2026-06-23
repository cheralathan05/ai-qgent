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
    engine_used: str = ""
    processing_time_ms: float = 0.0

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
        self._tesseract_available = None
        self._languages = languages or ["en"]
        self._ocr_enabled = os.environ.get("OCR_ENABLED", "true").lower() != "false"
        self._engines_checked = False
        self._available_engines: List[str] = []

    def _check_engines(self):
        """Check which OCR engines are available at startup."""
        if self._engines_checked:
            return

        # Check EasyOCR
        try:
            import easyocr
            self._available_engines.append("easyocr")
            logger.info("OCR engine available: EasyOCR")
        except ImportError:
            logger.warning("OCR engine NOT available: EasyOCR (not installed)")

        # Check Tesseract
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
        """Return OCR engine status for health checks."""
        self._check_engines()
        return {
            "ocr_enabled": self._ocr_enabled,
            "engines": self._available_engines,
            "easyocr_available": "easyocr" in self._available_engines,
            "tesseract_available": "tesseract" in self._available_engines,
        }

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                logger.info("Initializing EasyOCR reader...")
                self._reader = easyocr.Reader(self._languages, gpu=False)
                logger.info(f"EasyOCR reader initialized for {self._languages}")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}, will try Tesseract fallback")
                self._reader = "tesseract_fallback"
        return self._reader

    def _tesseract_ocr(self, image: np.ndarray) -> List[tuple]:
        """Fallback OCR using Tesseract via pytesseract."""
        try:
            import pytesseract
            from PIL import Image as PILImage
            pil_image = PILImage.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
            results = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = int(data["conf"][i]) / 100.0 if data["conf"][i] != "-1" else 0.0
                if text and conf >= 0.2:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    if w > 0 and h > 0:
                        results.append((
                            [(x, y), (x+w, y), (x+w, y+h), (x, y+h)],
                            text, conf
                        ))
            logger.info(f"Tesseract detected {len(results)} text regions")
            return results
        except ImportError:
            logger.warning("pytesseract not installed - Tesseract fallback unavailable")
            return []
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            return []

    def _preprocess_for_ocr(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess image for better OCR results.

        Returns:
            (gray, binary) - grayscale and binarized versions
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive threshold for better text detection
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Also create Otsu threshold
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return gray, binary

    def _easyocr_extract(self, image: np.ndarray, reader) -> List[DetectedText]:
        """Run EasyOCR on an image and return DetectedText list."""
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
                texts.append(DetectedText(
                    text=text.strip(),
                    confidence=float(confidence),
                    bbox=(x, y, x2 - x, y2 - y),
                    x=x, y=y, w=x2 - x, h=y2 - y,
                ))
        except Exception as e:
            logger.warning(f"EasyOCR extraction failed: {e}")
        return texts

    async def extract_text(self, image: np.ndarray) -> OCRResult:
        if not self._ocr_enabled:
            return OCRResult(
                success=False, error="OCR is disabled (OCR_ENABLED=false)",
                image_width=image.shape[1] if image is not None and image.size > 0 else 0,
                image_height=image.shape[0] if image is not None and image.size > 0 else 0,
            )

        if image is None or image.size == 0:
            return OCRResult(success=False, error="Empty image")

        self._check_engines()

        h, w = image.shape[:2]
        start_time = time.time()

        logger.info(f"OCR START - image size: {w}x{h}, engines available: {self._available_engines}")

        if not self._available_engines:
            elapsed = (time.time() - start_time) * 1000
            return OCRResult(
                success=False,
                error="No OCR engines available. Install easyocr or pytesseract.",
                image_width=w, image_height=h,
                processing_time_ms=elapsed,
            )

        # Preprocess
        gray, binary = self._preprocess_for_ocr(image)

        # Strategy 1: EasyOCR on original image
        reader = self._get_reader()
        if reader and reader != "tesseract_fallback":
            logger.info("OCR: Trying EasyOCR on original image...")
            texts = self._easyocr_extract(image, reader)

            # Strategy 2: EasyOCR on enhanced/preprocessed image
            if not texts:
                logger.info("OCR: EasyOCR found nothing on original, trying preprocessed...")
                texts = self._easyocr_extract(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), reader)

            # Strategy 3: EasyOCR on binary image
            if not texts:
                logger.info("OCR: Trying EasyOCR on binary image...")
                texts = self._easyocr_extract(cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR), reader)

            # Strategy 4: EasyOCR on sharpened image
            if not texts:
                logger.info("OCR: Trying EasyOCR on sharpened image...")
                kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
                sharpened = cv2.filter2D(image, -1, kernel)
                texts = self._easyocr_extract(sharpened, reader)

            if texts:
                elapsed = (time.time() - start_time) * 1000
                full_text = " | ".join(t.text for t in texts)
                logger.info(f"OCR RESULT (EasyOCR) - text_count={len(texts)}, time={elapsed:.0f}ms")
                logger.info(f"OCR text preview: {full_text[:200]}")
                return OCRResult(
                    texts=texts,
                    full_text=full_text,
                    image_width=w, image_height=h,
                    success=True,
                    engine_used="easyocr",
                    processing_time_ms=elapsed,
                )

        # Strategy 5: Tesseract fallback
        if "tesseract" in self._available_engines:
            logger.info("OCR: Trying Tesseract fallback...")
            tesseract_results = self._tesseract_ocr(image)
            if tesseract_results:
                texts = []
                all_text_parts = []
                for bbox, text, confidence in tesseract_results:
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
                elapsed = (time.time() - start_time) * 1000
                full_text = " | ".join(all_text_parts)
                logger.info(f"OCR RESULT (Tesseract) - text_count={len(texts)}, time={elapsed:.0f}ms")
                return OCRResult(
                    texts=texts,
                    full_text=full_text,
                    image_width=w, image_height=h,
                    success=True,
                    engine_used="tesseract",
                    processing_time_ms=elapsed,
                )

        # No text found by any engine
        elapsed = (time.time() - start_time) * 1000
        logger.warning(f"OCR: No text detected in {w}x{h} image after {elapsed:.0f}ms")
        return OCRResult(
            texts=[],
            full_text="",
            image_width=w, image_height=h,
            success=False,
            error="No text detected in image",
            engine_used="none",
            processing_time_ms=elapsed,
        )

    async def extract_text_from_file(self, filepath: str) -> OCRResult:
        logger.info(f"OCR: Reading file {filepath}")
        image = cv2.imread(filepath)
        if image is None:
            return OCRResult(success=False, error=f"Cannot read {filepath}")
        logger.info(f"OCR: File loaded - {image.shape[1]}x{image.shape[0]}")
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
