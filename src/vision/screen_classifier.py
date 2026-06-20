import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

import cv2
import numpy as np

from vision.ui_detector import DetectedUIElement, UIDetectionResult
from vision.layout_detector import LayoutResult, LayoutSection, SectionType
from vision.ocr_service import OCRResult

logger = logging.getLogger(__name__)


class ScreenType(str, Enum):
    ANDROID_HOME = "android_home"
    LOCK_SCREEN = "lock_screen"
    SETTINGS = "settings"
    APP_DRAWER = "app_drawer"
    INSTAGRAM_FEED = "instagram_feed"
    INSTAGRAM_PROFILE = "instagram_profile"
    INSTAGRAM_DM = "instagram_dm"
    INSTAGRAM_DM_CHAT = "instagram_dm_chat"
    INSTAGRAM_STORY = "instagram_story"
    INSTAGRAM_REELS = "instagram_reels"
    WHATSAPP_CHAT = "whatsapp_chat"
    WHATSAPP_INBOX = "whatsapp_inbox"
    WHATSAPP_STATUS = "whatsapp_status"
    WHATSAPP_CALLS = "whatsapp_calls"
    CHROME_SEARCH = "chrome_search"
    CHROME_WEBPAGE = "chrome_webpage"
    CHROME_TABS = "chrome_tabs"
    YOUTUBE_FEED = "youtube_feed"
    YOUTUBE_VIDEO = "youtube_video"
    YOUTUBE_SEARCH = "youtube_search"
    YOUTUBE_SHORTS = "youtube_shorts"
    GMAIL_INBOX = "gmail_inbox"
    GMAIL_EMAIL = "gmail_email"
    GOOGLE_MAPS = "google_maps"
    TELEGRAM_CHAT = "telegram_chat"
    TELEGRAM_INBOX = "telegram_inbox"
    DISCORD_CHAT = "discord_chat"
    LINKEDIN_FEED = "linkedin_feed"
    TWITTER_FEED = "twitter_feed"
    FACEBOOK_FEED = "facebook_feed"
    MESSENGER_CHAT = "messenger_chat"
    SPOTIFY_HOME = "spotify_home"
    CAMERA = "camera"
    GALLERY = "gallery"
    DIALER = "dialer"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


@dataclass
class ScreenClassificationResult:
    screen_type: ScreenType
    app_name: Optional[str] = None
    screen_name: Optional[str] = None
    confidence: float = 0.0
    detected_elements: List[DetectedUIElement] = field(default_factory=list)
    text_content: str = ""
    classification_reason: str = ""
    classified_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_type": self.screen_type.value,
            "app_name": self.app_name,
            "screen_name": self.screen_name,
            "confidence": self.confidence,
            "elements_count": len(self.detected_elements),
            "text_content": self.text_content[:200],
            "classification_reason": self.classification_reason,
            "classified_at": self.classified_at.isoformat(),
        }


SCREEN_SIGNATURES: Dict[ScreenType, Dict[str, Any]] = {
    ScreenType.ANDROID_HOME: {
        "apps": [], "indicators": ["google", "search", "assistant", "at a glance"],
        "no_indicators": [], "min_buttons": 0, "has_bottom_bar": True,
    },
    ScreenType.LOCK_SCREEN: {
        "apps": [], "indicators": ["enter pin", "password", "pattern", "swipe", "emergency"],
        "no_indicators": [], "min_buttons": 0,
    },
    ScreenType.SETTINGS: {
        "apps": ["settings"], "indicators": ["setting", "preference", "about phone", "display", "sound", "network", "bluetooth"],
        "no_indicators": [], "min_buttons": 2,
    },
    ScreenType.APP_DRAWER: {
        "apps": [], "indicators": ["app drawer", "all apps"],
        "no_indicators": ["setting"], "min_buttons": 6,
    },
    ScreenType.INSTAGRAM_FEED: {
        "apps": ["instagram"], "indicators": ["home", "feed", "like", "comment", "post", "story", "suggested"],
        "no_indicators": ["direct", "message inbox"], "min_buttons": 3,
    },
    ScreenType.INSTAGRAM_PROFILE: {
        "apps": ["instagram"], "indicators": ["profile", "follower", "following", "edit profile", "post"],
        "no_indicators": ["feed", "home"], "min_buttons": 2,
    },
    ScreenType.INSTAGRAM_DM: {
        "apps": ["instagram"], "indicators": ["direct", "inbox", "message", "requests", "primary", "general"],
        "no_indicators": ["feed", "home", "profile"], "min_buttons": 1,
    },
    ScreenType.INSTAGRAM_DM_CHAT: {
        "apps": ["instagram"], "indicators": ["message", "type a message", "send", "chat", "seen"],
        "no_indicators": ["inbox", "feed", "home"], "min_buttons": 1,
    },
    ScreenType.INSTAGRAM_STORY: {
        "apps": ["instagram"], "indicators": ["reply", "send message", "story"],
        "no_indicators": [], "min_buttons": 1,
    },
    ScreenType.INSTAGRAM_REELS: {
        "apps": ["instagram"], "indicators": ["reels", "like", "comment", "share", "save"],
        "no_indicators": ["feed", "home", "profile"], "min_buttons": 2,
    },
    ScreenType.WHATSAPP_INBOX: {
        "apps": ["whatsapp"], "indicators": ["chats", "calls", "status", "broadcast", "groups"],
        "no_indicators": ["type a message"], "min_buttons": 2,
    },
    ScreenType.WHATSAPP_CHAT: {
        "apps": ["whatsapp"], "indicators": ["type a message", "send", "chat", "message", "seen", "online"],
        "no_indicators": ["chats list", "calls"], "min_buttons": 1,
    },
    ScreenType.WHATSAPP_STATUS: {
        "apps": ["whatsapp"], "indicators": ["status", "my status", "recent updates", "viewed"],
        "no_indicators": ["type a message"], "min_buttons": 1,
    },
    ScreenType.WHATSAPP_CALLS: {
        "apps": ["whatsapp"], "indicators": ["calls", "missed", "incoming", "outgoing"],
        "no_indicators": ["type a message", "chats"], "min_buttons": 1,
    },
    ScreenType.CHROME_SEARCH: {
        "apps": ["chrome"], "indicators": ["search", "google", "google search", "url", "address bar"],
        "no_indicators": ["setting"], "min_buttons": 1,
    },
    ScreenType.CHROME_WEBPAGE: {
        "apps": ["chrome"], "indicators": ["http", "https", "www", ".com", "site"],
        "no_indicators": ["google search"], "min_buttons": 1,
    },
    ScreenType.CHROME_TABS: {
        "apps": ["chrome"], "indicators": ["tab", "incognito", "new tab"],
        "no_indicators": [], "min_buttons": 1,
    },
    ScreenType.YOUTUBE_FEED: {
        "apps": ["youtube"], "indicators": ["home", "shorts", "subscription", "trending", "video"],
        "no_indicators": ["subscribe", "like", "comment", "share"], "min_buttons": 3,
    },
    ScreenType.YOUTUBE_VIDEO: {
        "apps": ["youtube"], "indicators": ["subscribe", "like", "comment", "share", "save", "download"],
        "no_indicators": ["home", "shorts", "subscription"], "min_buttons": 3,
    },
    ScreenType.YOUTUBE_SEARCH: {
        "apps": ["youtube"], "indicators": ["search", "results for", "filter"],
        "no_indicators": ["subscribe", "like"], "min_buttons": 1,
    },
    ScreenType.YOUTUBE_SHORTS: {
        "apps": ["youtube"], "indicators": ["shorts"],
        "no_indicators": ["home", "subscription"], "min_buttons": 1,
    },
    ScreenType.GMAIL_INBOX: {
        "apps": ["gmail"], "indicators": ["inbox", "primary", "social", "promotions", "mail"],
        "no_indicators": [], "min_buttons": 2,
    },
    ScreenType.GMAIL_EMAIL: {
        "apps": ["gmail"], "indicators": ["reply", "reply all", "forward", "compose", "subject"],
        "no_indicators": ["inbox", "primary"], "min_buttons": 2,
    },
    ScreenType.GOOGLE_MAPS: {
        "apps": ["maps"], "indicators": ["map", "search here", "directions", "traffic", "satellite"],
        "no_indicators": [], "min_buttons": 1,
    },
    ScreenType.CAMERA: {
        "apps": ["camera"], "indicators": ["shutter", "capture", "video", "photo", "gallery", "flash"],
        "no_indicators": [], "min_buttons": 2,
    },
    ScreenType.GALLERY: {
        "apps": ["gallery"], "indicators": ["album", "photo", "image", "gallery", "camera roll"],
        "no_indicators": [], "min_buttons": 1,
    },
    ScreenType.DIALER: {
        "apps": ["dialer", "phone"], "indicators": ["dial", "call", "contacts", "recent", "keypad"],
        "no_indicators": [], "min_buttons": 2,
    },
    ScreenType.NOTIFICATION: {
        "apps": [], "indicators": ["notification", "clear", "dismiss", "reply"],
        "no_indicators": [], "min_buttons": 1,
    },
}

APP_PACKAGE_ALIASES: Dict[str, str] = {
    "com.instagram.android": "instagram",
    "com.whatsapp": "whatsapp",
    "com.android.chrome": "chrome",
    "com.google.android.youtube": "youtube",
    "com.android.settings": "settings",
    "com.google.android.gm": "gmail",
    "com.google.android.apps.maps": "maps",
    "com.android.camera": "camera",
    "com.android.dialer": "dialer",
    "com.google.android.apps.messaging": "messages",
    "com.twitter.android": "twitter",
    "com.facebook.katana": "facebook",
    "com.spotify.music": "spotify",
}


def _get_dynamic_aliases() -> Dict[str, str]:
    """Augment APP_PACKAGE_ALIASES with dynamically discovered apps."""
    try:
        from services.app_resolver import get_app_resolver
        resolver = get_app_resolver()
        if resolver.is_ready():
            extra = {}
            for pkg, info in resolver.package_map.items():
                for name in info.normalized_names:
                    extra[pkg] = name
                    break
                if pkg not in extra:
                    extra[pkg] = info.app_label.lower()
            return extra if extra else APP_PACKAGE_ALIASES
    except Exception:
        pass
    return APP_PACKAGE_ALIASES


class ScreenClassifier:
    def __init__(self):
        pass

    async def classify(
        self,
        image: Optional[np.ndarray] = None,
        foreground_app: Optional[str] = None,
        text_content: str = "",
        ui_result: Optional[UIDetectionResult] = None,
        layout_result: Optional[LayoutResult] = None,
    ) -> ScreenClassificationResult:
        app_name = self._resolve_app_name(foreground_app) if foreground_app else None
        elements = ui_result.elements if ui_result else []
        text = text_content or (ui_result.text_content if ui_result else "")
        has_bottom_bar = layout_result.has_section(SectionType.BOTTOM_BAR) if layout_result else False

        text_lower = text.lower()
        button_count = len([e for e in elements if e.element_type == "button"])
        input_count = len([e for e in elements if e.element_type == "input"])

        best_match = ScreenType.UNKNOWN
        best_confidence = 0.2
        best_reason = ""

        for screen_type, sig in SCREEN_SIGNATURES.items():
            score = 0.0
            reasons = []

            app_match = (not sig.get("apps")) or (app_name and app_name in sig["apps"])
            if not app_match:
                continue

            indicator_matches = [ind for ind in sig.get("indicators", []) if ind in text_lower]
            if indicator_matches:
                score += min(0.5, len(indicator_matches) * 0.15)
                reasons.append(f"indicators: {indicator_matches}")

            no_indicator_matches = [ind for ind in sig.get("no_indicators", []) if ind in text_lower]
            if no_indicator_matches:
                score -= len(no_indicator_matches) * 0.2
                reasons.append(f"excluded: {no_indicator_matches}")

            min_btns = sig.get("min_buttons", 0)
            if button_count >= min_btns:
                score += 0.1
            elif min_btns > 0 and button_count < min_btns:
                score -= 0.1

            if sig.get("has_bottom_bar") and has_bottom_bar:
                score += 0.1
            elif sig.get("has_bottom_bar") is not None and not has_bottom_bar and sig["has_bottom_bar"]:
                score -= 0.05

            if app_name:
                score += 0.1

            if input_count > 0 and screen_type in (
                ScreenType.WHATSAPP_CHAT, ScreenType.INSTAGRAM_DM_CHAT,
                ScreenType.CHROME_SEARCH, ScreenType.YOUTUBE_SEARCH,
            ):
                score += 0.1

            if screen_type == ScreenType.APP_DRAWER and button_count >= 8:
                score += 0.2

            if score > best_confidence or (score == best_confidence and screen_type == ScreenType.UNKNOWN):
                best_confidence = score
                best_match = screen_type
                best_reason = "; ".join(reasons)

        if best_match == ScreenType.UNKNOWN and app_name:
            best_reason = f"app={app_name} but no screen pattern matched"
            best_confidence = 0.3

        if best_match == ScreenType.UNKNOWN and not app_name:
            if "lock" in text_lower or "enter" in text_lower:
                best_match = ScreenType.LOCK_SCREEN
                best_confidence = 0.4
                best_reason = "lock screen keywords detected"
            elif "setting" in text_lower:
                best_match = ScreenType.SETTINGS
                best_confidence = 0.3
                best_reason = "settings keywords detected"
            elif "google" in text_lower or "search" in text_lower:
                best_match = ScreenType.CHROME_SEARCH
                best_confidence = 0.3
                best_reason = "google/search keywords detected"

        return ScreenClassificationResult(
            screen_type=best_match,
            app_name=app_name,
            screen_name=best_match.value,
            confidence=best_confidence,
            detected_elements=elements,
            text_content=text,
            classification_reason=best_reason,
        )

    def _resolve_app_name(self, package: str) -> Optional[str]:
        if not package:
            return None
        clean = package.strip()
        aliases = _get_dynamic_aliases()
        if clean in aliases:
            return aliases[clean]
        if "." in clean:
            parts = clean.split(".")
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] not in ("android", "google", "com", "app"):
                    return parts[i].lower()
        return clean.lower()


_screen_classifier: Optional[ScreenClassifier] = None


def get_screen_classifier() -> ScreenClassifier:
    global _screen_classifier
    if _screen_classifier is None:
        _screen_classifier = ScreenClassifier()
    return _screen_classifier
