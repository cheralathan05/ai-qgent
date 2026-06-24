"""Memory Agent - Element position caching and retrieval.

Caches successful UI element positions per app/screen to speed up
subsequent operations. Invalidates cache when screen changes detected.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".apa_os", "element_cache")
CACHE_TTL_HOURS = 24


@dataclass
class CachedElement:
    """A cached UI element position."""
    element_type: str
    text: str
    x: int
    y: int
    w: int
    h: int
    confidence: float
    app_name: str
    screen_type: str
    cached_at: float = field(default_factory=time.time)
    hit_count: int = 0
    last_verified: float = 0.0

    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    def is_expired(self, ttl_hours: float = CACHE_TTL_HOURS) -> bool:
        return (time.time() - self.cached_at) > ttl_hours * 3600

    def to_dict(self) -> dict:
        return {
            "element_type": self.element_type,
            "text": self.text,
            "x": self.x, "y": self.y, "w": self.w, "h": self.h,
            "confidence": self.confidence,
            "app_name": self.app_name,
            "screen_type": self.screen_type,
            "cached_at": self.cached_at,
            "hit_count": self.hit_count,
            "last_verified": self.last_verified,
        }


@dataclass
class ScreenCache:
    """Cache for a specific app/screen combination."""
    app_name: str
    screen_type: str
    elements: List[CachedElement] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def find_element(
        self, element_type: Optional[str] = None, text: Optional[str] = None
    ) -> Optional[CachedElement]:
        candidates = self.elements
        if element_type:
            candidates = [e for e in candidates if e.element_type == element_type]
        if text:
            text_lower = text.lower()
            candidates = [e for e in candidates if text_lower in e.text.lower()]
        if candidates:
            candidates.sort(key=lambda e: e.confidence, reverse=True)
            return candidates[0]
        return None

    def find_elements(
        self, element_type: Optional[str] = None, text: Optional[str] = None
    ) -> List[CachedElement]:
        candidates = self.elements
        if element_type:
            candidates = [e for e in candidates if e.element_type == element_type]
        if text:
            text_lower = text.lower()
            candidates = [e for e in candidates if text_lower in e.text.lower()]
        return candidates


class MemoryAgent:
    """Caches and retrieves UI element positions for faster navigation."""

    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self._cache: Dict[str, ScreenCache] = {}
        self._load_cache()

    def _cache_key(self, app_name: str, screen_type: str) -> str:
        return f"{app_name}:{screen_type}"

    def _load_cache(self):
        try:
            cache_file = os.path.join(CACHE_DIR, "element_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    data = json.load(f)
                for key, screen_data in data.items():
                    elements = [
                        CachedElement(**e) for e in screen_data.get("elements", [])
                    ]
                    self._cache[key] = ScreenCache(
                        app_name=screen_data.get("app_name", ""),
                        screen_type=screen_data.get("screen_type", ""),
                        elements=elements,
                        last_updated=screen_data.get("last_updated", 0),
                    )
                logger.info(f"Loaded element cache: {len(self._cache)} screens")
        except Exception as e:
            logger.warning(f"Failed to load element cache: {e}")

    def _save_cache(self):
        try:
            cache_file = os.path.join(CACHE_DIR, "element_cache.json")
            data = {}
            for key, screen_cache in self._cache.items():
                data[key] = {
                    "app_name": screen_cache.app_name,
                    "screen_type": screen_cache.screen_type,
                    "elements": [e.to_dict() for e in screen_cache.elements],
                    "last_updated": screen_cache.last_updated,
                }
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save element cache: {e}")

    def cache_element(
        self,
        app_name: str,
        screen_type: str,
        element_type: str,
        text: str,
        x: int, y: int, w: int, h: int,
        confidence: float = 0.8,
    ):
        """Cache a verified element position."""
        key = self._cache_key(app_name, screen_type)
        if key not in self._cache:
            self._cache[key] = ScreenCache(
                app_name=app_name, screen_type=screen_type
            )

        screen_cache = self._cache[key]

        # Check if similar element already cached
        for existing in screen_cache.elements:
            if (existing.element_type == element_type and
                existing.text.lower() == text.lower() and
                abs(existing.x - x) < 50 and abs(existing.y - y) < 50):
                existing.x = x
                existing.y = y
                existing.w = w
                existing.h = h
                existing.confidence = max(existing.confidence, confidence)
                existing.last_verified = time.time()
                existing.hit_count += 1
                self._save_cache()
                return

        screen_cache.elements.append(CachedElement(
            element_type=element_type,
            text=text,
            x=x, y=y, w=w, h=h,
            confidence=confidence,
            app_name=app_name,
            screen_type=screen_type,
        ))
        screen_cache.last_updated = time.time()
        self._save_cache()

    def find_cached_element(
        self,
        app_name: str,
        screen_type: str,
        element_type: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Optional[CachedElement]:
        """Find a cached element position."""
        key = self._cache_key(app_name, screen_type)
        screen_cache = self._cache.get(key)
        if not screen_cache:
            return None

        # Clean expired entries
        screen_cache.elements = [
            e for e in screen_cache.elements if not e.is_expired()
        ]

        element = screen_cache.find_element(element_type, text)
        if element:
            element.hit_count += 1
            logger.info(
                f"Cache HIT for '{text or element_type}' in {app_name}/{screen_type} "
                f"at ({element.x}, {element.y}) [hits={element.hit_count}]"
            )
        return element

    def find_cached_send_button(
        self, app_name: str, screen_type: str
    ) -> Optional[CachedElement]:
        return self.find_cached_element(app_name, screen_type, "send_button")

    def find_cached_search_bar(
        self, app_name: str, screen_type: str
    ) -> Optional[CachedElement]:
        return self.find_cached_element(app_name, screen_type, "search_bar")

    def find_cached_input_field(
        self, app_name: str, screen_type: str
    ) -> Optional[CachedElement]:
        return self.find_cached_element(app_name, screen_type, "input_field")

    def invalidate_screen(self, app_name: str, screen_type: str):
        """Invalidate cache for a specific screen."""
        key = self._cache_key(app_name, screen_type)
        if key in self._cache:
            del self._cache[key]
            self._save_cache()
            logger.info(f"Invalidated cache for {app_name}/{screen_type}")

    def clear_expired(self):
        """Remove all expired cache entries."""
        for key, screen_cache in list(self._cache.items()):
            screen_cache.elements = [
                e for e in screen_cache.elements if not e.is_expired()
            ]
            if not screen_cache.elements:
                del self._cache[key]
        self._save_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        total_elements = sum(len(sc.elements) for sc in self._cache.values())
        total_hits = sum(
            e.hit_count for sc in self._cache.values() for e in sc.elements
        )
        return {
            "total_screens": len(self._cache),
            "total_elements": total_elements,
            "total_hits": total_hits,
            "screens": {
                k: {"elements": len(v.elements), "app": v.app_name}
                for k, v in self._cache.items()
            },
        }


_memory_agent: Optional[MemoryAgent] = None


def get_memory_agent() -> MemoryAgent:
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent
