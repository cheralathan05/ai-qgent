import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from services.adb_service import get_adb_service, find_adb_binary

logger = logging.getLogger(__name__)

CAPTURE_DIR = os.path.join(tempfile.gettempdir(), "apa_screen_captures")


@dataclass
class ScreenCaptureResult:
    image: Optional[np.ndarray] = None
    filepath: Optional[str] = None
    width: int = 0
    height: int = 0
    captured_at: datetime = field(default_factory=datetime.utcnow)
    device_id: str = ""
    success: bool = False
    error: str = ""


class ScreenCaptureService:
    def __init__(self):
        os.makedirs(CAPTURE_DIR, exist_ok=True)

    def _save_to_disk(self, image: np.ndarray) -> str:
        filename = f"screen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(CAPTURE_DIR, filename)
        cv2.imwrite(filepath, image)
        return filepath

    async def capture_from_adb(self, device_id: str) -> ScreenCaptureResult:
        try:
            adb = get_adb_service(find_adb_binary())
            png_data = await adb.take_screenshot(device_id)
            if not png_data:
                return ScreenCaptureResult(success=False, error="Empty screenshot data", device_id=device_id)
            nparr = np.frombuffer(png_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return ScreenCaptureResult(success=False, error="Failed to decode screenshot", device_id=device_id)
            height, width = image.shape[:2]
            filepath = self._save_to_disk(image)
            return ScreenCaptureResult(
                image=image, filepath=filepath,
                width=width, height=height,
                captured_at=datetime.utcnow(),
                device_id=device_id, success=True,
            )
        except Exception as e:
            logger.error(f"Screen capture failed for {device_id}: {e}")
            return ScreenCaptureResult(success=False, error=str(e), device_id=device_id)

    async def capture_from_file(self, filepath: str) -> ScreenCaptureResult:
        try:
            image = cv2.imread(filepath)
            if image is None:
                return ScreenCaptureResult(success=False, error=f"Cannot read {filepath}")
            height, width = image.shape[:2]
            return ScreenCaptureResult(
                image=image, filepath=filepath,
                width=width, height=height,
                captured_at=datetime.utcnow(),
                device_id="file", success=True,
            )
        except Exception as e:
            return ScreenCaptureResult(success=False, error=str(e))

    async def capture_from_pil(self, pil_image: Image.Image) -> ScreenCaptureResult:
        try:
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            height, width = image.shape[:2]
            filepath = self._save_to_disk(image)
            return ScreenCaptureResult(
                image=image, filepath=filepath,
                width=width, height=height,
                captured_at=datetime.utcnow(),
                device_id="pil", success=True,
            )
        except Exception as e:
            return ScreenCaptureResult(success=False, error=str(e))

    @staticmethod
    def preprocess(image: np.ndarray, grayscale: bool = True, denoise: bool = True) -> np.ndarray:
        processed = image.copy()
        if grayscale and len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        if denoise:
            processed = cv2.fastNlMeansDenoising(processed) if len(processed.shape) == 2 else cv2.fastNlMeansDenoisingColored(processed)
        return processed

    @staticmethod
    def resize_for_analysis(image: np.ndarray, max_width: int = 1080) -> np.ndarray:
        h, w = image.shape[:2]
        if w <= max_width:
            return image
        ratio = max_width / w
        new_size = (max_width, int(h * ratio))
        return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)

    @staticmethod
    def extract_region(image: np.ndarray, x: int, y: int, w: int, h: int) -> Optional[np.ndarray]:
        img_h, img_w = image.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(img_w, x + w), min(img_h, y + h)
        if x2 <= x1 or y2 <= y1:
            return None
        return image[y1:y2, x1:x2]

    def clean_old_captures(self, max_age_hours: int = 24):
        now = datetime.utcnow().timestamp()
        for fname in os.listdir(CAPTURE_DIR):
            fpath = os.path.join(CAPTURE_DIR, fname)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < now - max_age_hours * 3600:
                try:
                    os.remove(fpath)
                except OSError:
                    pass


_screen_capture_service: Optional[ScreenCaptureService] = None


def get_screen_capture_service() -> ScreenCaptureService:
    global _screen_capture_service
    if _screen_capture_service is None:
        _screen_capture_service = ScreenCaptureService()
    return _screen_capture_service
