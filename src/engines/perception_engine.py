import asyncio
import logging
import time
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from services.adb_service import get_adb_service, find_adb_binary
from vision.screen_capture import get_screen_capture_service
from vision.ocr_service import get_ocr_service
from vision.ui_detector import get_ui_detector
from vision.screen_classifier import get_screen_classifier, ScreenType
from .models import PerceivedState, VisualElement

logger = logging.getLogger(__name__)

class PerceptionEngine:
    """
    Synthesizes Android Accessibility, UI Automator, and Vision data
    into a unified PerceivedState.
    """
    def __init__(self):
        self.adb = get_adb_service(find_adb_binary())
        self.capture_svc = get_screen_capture_service()
        self.ocr_svc = get_ocr_service()
        self.ui_detector = get_ui_detector()
        self.classifier = get_screen_classifier()

    async def perceive(self, device_id: str) -> PerceivedState:
        """Perform a full perception cycle."""
        start_time = time.time()

        # 1. Capture Screen and Base Metadata
        capture = await self.capture_svc.capture_from_adb(device_id)
        if not capture.success or capture.image is None:
            logger.error(f"Failed to capture screen for {device_id}: {capture.error}")
            return PerceivedState(device_id=device_id, confidence=0.0)

        # 2. Accessibility Tree / UI Automator Dump
        # We use dumpsys accessibility and uiautomator dump as primary semantic sources
        acc_elements = await self._extract_accessibility_elements(device_id)

        # 3. Vision Analysis
        ocr_result = await self.ocr_svc.extract_text(capture.image)
        ui_result = await self.ui_detector.detect_elements(capture.image)

        # 4. Screen Classification
        classification = await self.classifier.classify(
            image=capture.image,
            text_content=ocr_result.full_text,
            ui_result=ui_result,
        )

        # 5. Merge Perception Data
        # We merge accessibility nodes with visual detections
        merged_elements = self._merge_elements(acc_elements, ui_result.elements, ocr_result.texts)

        # 6. Gather Device State
        current_app = await self.adb.get_foreground_app(device_id)

        return PerceivedState(
            device_id=device_id,
            current_app=current_app,
            screen_type=classification.screen_type.value if hasattr(classification, 'screen_type') else "unknown",
            elements=merged_elements,
            full_text=ocr_result.full_text,
            confidence=classification.confidence,
            timestamp=start_time
        )

    async def _extract_accessibility_elements(self, device_id: str) -> List[VisualElement]:
        """
        Extracts UI elements using ADB dumpsys and UIAutomator.
        This provides the 'semantic' layer of perception.
        """
        elements = []
        try:
            # Method A: UIAutomator XML Dump (most reliable for structure)
            # This requires a temporary file on the device
            await self.adb.shell(device_id, "uiautomator dump /sdcard/view.xml")
            xml_content = await self.adb.shell(device_id, "cat /sdcard/view.xml")

            # Simple regex-based parsing for the sake of implementation
            # In a production system, we'd use an XML parser.
            # We look for nodes with text or content-desc
            nodes = re.findall(r'<node[^>]*text="([^"]*)"[^>]*>', xml_content)
            for i, text in enumerate(nodes):
                if text:
                    elements.append(VisualElement(
                        label=text,
                        bbox=[0, 0, 0, 0], # Bboxes would be parsed from bounds="[x,y][x,y]"
                        confidence=1.0,
                        element_type="accessibility_node",
                        source="accessibility",
                        content_description=text
                    ))

            # Method B: dumpsys accessibility (for focused element/state)
            acc_dump = await self.adb.shell(device_id, "dumpsys accessibility")
            # Look for "Focused" or "Selected" elements
            if "mFocused" in acc_dump:
                # Extract focused element info if possible
                pass

        except Exception as e:
            logger.warning(f"Accessibility extraction failed: {e}")

        return elements

    def _merge_elements(self, acc_elements: List[VisualElement],
                        ui_elements: List[Any],
                        ocr_texts: List[Any]) -> List[VisualElement]:
        """
        Combines Accessibility nodes, UI detections, and OCR text
        into a single, deduplicated list of VisualElements.
        """
        final_elements = []

        # 1. Add Accessibility elements (high confidence, semantic)
        final_elements.extend(acc_elements)

        # 2. Add UI detected elements (YOLO/Contours)
        for el in ui_elements:
            # el is likely a detected element object from ui_detector.py
            # we convert it to VisualElement
            final_elements.append(VisualElement(
                label=getattr(el, 'text', 'ui_element'),
                bbox=getattr(el, 'bbox', [0,0,0,0]),
                confidence=getattr(el, 'confidence', 0.5),
                element_type=getattr(el, 'type', 'unknown'),
                source="vision"
            ))

        # 3. Add OCR text regions as elements
        for txt in ocr_texts:
            # txt has .text, .x, .y, .w, .h
            final_elements.append(VisualElement(
                label=txt.text,
                bbox=[txt.x, txt.y, txt.w, txt.h],
                confidence=txt.confidence,
                element_type="text_region",
                source="ocr"
            ))

        # Simple deduplication based on label and position could be added here
        return final_elements

def get_perception_engine() -> PerceptionEngine:
    return PerceptionEngine()
