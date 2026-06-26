"""Universal Action Recognizer - Accurate NLU for ANY user request.

Combines fast regex patterns (for common commands) with LLM enhancement
(for novel/complex commands). Handles compound, contextual, and ambiguous requests.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ActionCategory(str, Enum):
    APP = "app"
    MESSAGING = "messaging"
    CALL = "call"
    SETTINGS = "settings"
    CONNECTIVITY = "connectivity"
    MEDIA = "media"
    FILE = "file"
    SEARCH = "search"
    NAVIGATION = "navigation"
    SYSTEM = "system"
    NOTIFICATION = "notification"
    SCREEN = "screen"
    KNOWLEDGE = "knowledge"
    AUTOMATION = "automation"
    DOCUMENT = "document"
    DEVICE = "device"
    UNKNOWN = "unknown"


class RecognizedAction(str, Enum):
    # App actions
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SWITCH_APP = "switch_app"
    SEARCH_FOR_APP = "search_for_app"
    LIST_APPS = "list_apps"
    UPDATE_APP = "update_app"

    # Messaging
    SEND_MESSAGE = "send_message"
    REPLY_MESSAGE = "reply_message"
    READ_MESSAGE = "read_message"
    SEARCH_MESSAGE = "search_message"
    OPEN_CHAT = "open_chat"
    SEND_EMAIL = "send_email"

    # Calling
    MAKE_CALL = "make_call"
    ANSWER_CALL = "answer_call"
    END_CALL = "end_call"
    VIDEO_CALL = "video_call"

    # Settings
    OPEN_SETTINGS = "open_settings"
    OPEN_SETTING_SECTION = "open_setting_section"
    TOGGLE_WIFI = "toggle_wifi"
    TOGGLE_BLUETOOTH = "toggle_bluetooth"
    TOGGLE_FLASHLIGHT = "toggle_flashlight"
    TOGGLE_DND = "toggle_dnd"
    TOGGLE_MOBILE_DATA = "toggle_mobile_data"
    TOGGLE_HOTSPOT = "toggle_hotspot"
    TOGGLE_AIRPLANE_MODE = "toggle_airplane_mode"
    TOGGLE_LOCATION = "toggle_location"
    TOGGLE_AUTO_ROTATE = "toggle_auto_rotate"
    ADJUST_BRIGHTNESS = "adjust_brightness"
    SET_VOLUME = "set_volume"
    SET_RINGTONE = "set_ringtone"
    CONNECT_WIFI = "connect_wifi"
    ENABLE_BATTERY_SAVER = "enable_battery_saver"
    DISABLE_BATTERY_SAVER = "disable_battery_saver"

    # Media
    PLAY_MEDIA = "play_media"
    PAUSE_MEDIA = "pause_media"
    NEXT_TRACK = "next_track"
    PREV_TRACK = "prev_track"
    TAKE_PHOTO = "take_photo"
    RECORD_VIDEO = "record_video"
    OPEN_CAMERA = "open_camera"
    OPEN_GALLERY = "open_gallery"

    # File
    OPEN_FILE = "open_file"
    SEARCH_FILE = "search_file"
    DELETE_FILE = "delete_file"
    MOVE_FILE = "move_file"
    RENAME_FILE = "rename_file"
    SHARE_FILE = "share_file"
    LIST_FILES = "list_files"
    OPEN_FOLDER = "open_folder"
    DOWNLOAD_FILE = "download_file"

    # Search
    SEARCH_WEB = "search_web"
    SEARCH_APP = "search_app"
    SEARCH_CONTACTS = "search_contacts"
    SEARCH_FILES = "search_files"

    # Navigation
    GO_BACK = "go_back"
    GO_HOME = "go_home"
    GO_TO_SCREEN = "go_to_screen"
    SCROLL = "scroll"
    REFRESH = "refresh"

    # System
    BATTERY_STATUS = "battery_status"
    DEVICE_INFO = "device_info"
    STORAGE_INFO = "storage_info"
    SCREENSHOT = "screenshot"
    SCREEN_RECORD = "screen_record"
    LOCK_DEVICE = "lock_device"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"
    READ_NOTIFICATIONS = "read_notifications"
    CLEAR_NOTIFICATIONS = "clear_notifications"
    CHECK_NETWORK = "check_network"

    # Knowledge
    ASK_QUESTION = "ask_question"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    EXPLAIN = "explain"
    FIND_INFO = "find_info"

    # Device
    CONNECT_DEVICE = "connect_device"
    DISCONNECT_DEVICE = "disconnect_device"
    PAIR_DEVICE = "pair_device"
    FIND_DEVICE = "find_device"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class RecognizedEntity:
    type: str
    value: str
    confidence: float
    start_pos: int = -1
    end_pos: int = -1

    def to_dict(self) -> dict:
        return {"type": self.type, "value": self.value, "confidence": self.confidence}


@dataclass
class RecognitionResult:
    action: RecognizedAction
    action_category: ActionCategory
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    normalized_text: str = ""
    sub_actions: List["RecognitionResult"] = field(default_factory=list)
    is_compound: bool = False
    requires_phase2: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "category": self.action_category.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "raw_text": self.raw_text[:100],
            "is_compound": self.is_compound,
            "sub_actions": [s.to_dict() for s in self.sub_actions],
            "requires_phase2": self.requires_phase2,
        }


class ActionRecognizer:
    """Universal action recognizer using patterns + LLM enhancement.

    Design:
    - Fast path: regex patterns for 60+ common actions (sub-50ms)
    - Deep path: LLM-based understanding for novel/complex commands
    - Compound detection: breaks "open X and do Y" into sub-actions
    - Context resolution: fills slots from conversation history
    """

    def __init__(self):
        self._llm = None

    async def _get_llm(self):
        if self._llm is None:
            try:
                from services.ollama_service import OllamaService
                from config import Config
                cfg = Config.get_ollama_config()
                if cfg and cfg.host and cfg.port:
                    self._llm = OllamaService(
                        host=cfg.host,
                        port=cfg.port,
                        model=cfg.model,
                        timeout_seconds=cfg.timeout,
                    )
            except Exception as e:
                logger.warning(f"LLM not available for action recognition: {e}")
                self._llm = False
        return self._llm if self._llm is not False else None

    async def recognize(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> RecognitionResult:
        """Recognize action from natural language text.
        
        Steps:
        1. Normalize the text
        2. Try fast regex pattern matching
        3. If low confidence, try LLM enhancement
        4. Handle compound commands
        """
        normalized = self._normalize(text)
        
        # Step 1: Fast regex matching
        result = self._match_patterns(normalized, text)
        
        # Step 2: If confidence too low, try LLM
        if result.confidence < 0.6 and result.action == RecognizedAction.UNKNOWN:
            llm_result = await self._llm_recognize(normalized, text)
            if llm_result and llm_result.confidence > result.confidence:
                result = llm_result

        # Step 3: Apply context from previous conversations
        if context:
            result = self._apply_context(result, context)

        # Step 4: Detect compound commands
        compound = self._detect_compound(normalized, result)
        if compound:
            result = compound

        # Step 5: Extract entities that patterns might have missed
        if not result.entities:
            self._extract_entities_deep(normalized, result)

        result.normalized_text = normalized
        result.raw_text = text

        logger.info(
            f"ActionRecognizer: action={result.action.value}, "
            f"conf={result.confidence:.2f}, entities={result.entities}, "
            f"compound={result.is_compound}"
        )
        return result

    def _normalize(self, text: str) -> str:
        normalized = text.lower().strip()
        # Normalize hyphens and special characters
        normalized = normalized.replace("-", " ").replace("_", " ")
        # Rejoin hyphenated/split words that lose meaning when separated
        compound_words = {
            "wi fi": "wifi",
            "blue tooth": "bluetooth",
            "flash light": "flashlight",
            "air plane": "airplane",
            "screen shot": "screenshot",
            "screen record": "screen_record",
            "do not disturb": "dnd",
            "turn on": "enable",
            "turn off": "disable",
        }
        for phrase, replacement in compound_words.items():
            normalized = normalized.replace(phrase, replacement)
        # Also normalize common abbreviations
        normalized = re.sub(r'\bbt\b', 'bluetooth', normalized)
        polite_patterns = [
            r"^(could you|could you please|can you|can you please|would you|"
            r"would you please|i want to|i wanna|i need to|i'd like to|"
            r"please|hey apa|hello apa|apa|hey)\s+",
            r"\s+(please|now|quickly|asap|urgently)\s*$",
        ]
        for pat in polite_patterns:
            normalized = re.sub(pat, "", normalized)
        # Remove stop words that interfere with pattern matching
        normalized = re.sub(r"\b(?:the|a|an)\b", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        normalized = normalized.strip("?.!,;:")
        return normalized

    def _match_patterns(self, text: str, raw: str) -> RecognitionResult:
        """Fast regex pattern matching for common actions.
        
        Uses priority-ordered patterns. More specific patterns are checked first.
        Returns UNKNOWN with low confidence if no pattern matches.
        """
        best = RecognitionResult(
            action=RecognizedAction.UNKNOWN,
            action_category=ActionCategory.UNKNOWN,
            confidence=0.0,
            raw_text=raw,
            normalized_text=text,
        )

        patterns: List[Tuple[RecognizedAction, ActionCategory, List[str], float, callable]] = [
            # === CONNECTIVITY ===
            (RecognizedAction.TOGGLE_WIFI, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable|switch|activate|deactivate)\s+wifi\b",
                r"\bwifi\s+(?:on|off|enable|disable)\b",
                r"\bconnect\s+(?:to\s+)?wifi\b",
            ], 0.95, self._extract_toggle_state),
            (RecognizedAction.CONNECT_WIFI, ActionCategory.CONNECTIVITY, [
                r"\bconnect\s+to\s+(?:wifi\s+)?(?:network\s+)?[\"']?(.+?)[\"']?(?:\s+password\s+[\"']?(.+?)[\"']?)?$",
            ], 0.9, self._extract_wifi_connect),
            (RecognizedAction.TOGGLE_BLUETOOTH, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable|switch|activate|deactivate)\s+bluetooth\b",
                r"\bbluetooth\s+(?:on|off|enable|disable)\b",
            ], 0.95, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_FLASHLIGHT, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable|switch)\s+(?:flashlight|flash|torch)\b",
                r"\bflashlight\s+(?:on|off)\b",
            ], 0.95, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_MOBILE_DATA, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:mobile\s+)?data\b",
                r"\bmobile\s+data\s+(?:on|off)\b",
            ], 0.9, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_DND, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:dnd|do\s+not\s+disturb|silent\s+mode)\b",
                r"\bdnd\s+(?:on|off)\b",
            ], 0.9, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_AIRPLANE_MODE, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:airplane\s+mode|flight\s+mode)\b",
                r"\bairplane\s+mode\s+(?:on|off)\b",
            ], 0.95, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_LOCATION, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:location|gps)\b",
                r"\blocation\s+(?:on|off)\b",
            ], 0.9, self._extract_toggle_state),
            (RecognizedAction.TOGGLE_HOTSPOT, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:hotspot|tethering)\b",
            ], 0.9, self._detect_toggle_state),
            (RecognizedAction.TOGGLE_AUTO_ROTATE, ActionCategory.CONNECTIVITY, [
                r"\b(?:turn\s+(?:on|off)|enable|disable)\s+(?:auto\s+rotate|screen\s+rotation|auto-rotate)\b",
            ], 0.9, self._detect_toggle_state),

            # === BATTERY SAVER ===
            (RecognizedAction.ENABLE_BATTERY_SAVER, ActionCategory.SETTINGS, [
                r"\b(?:enable|turn\s+on|activate)\s+(?:battery\s+saver|power\s+saving|battery\s+saving)\b",
                r"\bbattery\s+saver\s+on\b",
            ], 0.95, None),
            (RecognizedAction.DISABLE_BATTERY_SAVER, ActionCategory.SETTINGS, [
                r"\b(?:disable|turn\s+off|deactivate)\s+(?:battery\s+saver|power\s+saving|battery\s+saving)\b",
                r"\bbattery\s+saver\s+off\b",
            ], 0.95, None),

            # === SETTINGS ===
            (RecognizedAction.OPEN_SETTINGS, ActionCategory.SETTINGS, [
                r"\bopen\s+settings\b", r"\blaunch\s+settings\b",
                r"\bgo\s+to\s+settings\b", r"\bsettings\s+app\b",
            ], 0.95, None),
            (RecognizedAction.OPEN_SETTING_SECTION, ActionCategory.SETTINGS, [
                r"\bopen\s+(?:settings\s+)?(?:for\s+)?(.+?)(?:\s+settings)?\s*(?:please)?$",
                r"\bgo\s+to\s+(.+?)\s+settings\b",
                r"\bnavigate\s+to\s+(.+?)\s+in\s+settings\b",
            ], 0.85, self._extract_setting_section),
            (RecognizedAction.ADJUST_BRIGHTNESS, ActionCategory.SETTINGS, [
                r"\b(?:set|adjust|change|increase|decrease|lower|raise)\s+(?:the\s+)?brightness\b",
                r"\bbrightness\s+(?:up|down|to\s+\d+)",
            ], 0.9, self._extract_brightness),
            (RecognizedAction.SET_VOLUME, ActionCategory.SETTINGS, [
                r"\b(?:set|adjust|change|increase|decrease|lower|raise|turn\s+(?:up|down))\s+(?:the\s+)?volume\b",
                r"\bvolume\s+(?:up|down|to\s+\d+)",
                r"\b(?:louder|quieter|mute|unmute|silent)\b",
            ], 0.9, self._extract_volume),
            (RecognizedAction.SET_RINGTONE, ActionCategory.SETTINGS, [
                r"\b(?:set|change)\s+(?:ringtone|ring\s+tone|notification\s+sound)\b",
                r"\bringtone\s+(?:to|mode)\b",
            ], 0.85, None),

            # === SYSTEM ===
            (RecognizedAction.BATTERY_STATUS, ActionCategory.SYSTEM, [
                r"\bbattery\b", r"\bcharge\b", r"\bpower\s+level\b",
                r"\bhow\s+much\s+battery\b", r"\bbattery\s+level\b",
                r"\bhow\s+long\s+will\s+battery\b",
            ], 0.95, None),
            (RecognizedAction.DEVICE_INFO, ActionCategory.SYSTEM, [
                r"\bdevice\s+info\b", r"\bphone\s+info\b",
                r"\bsystem\s+info\b", r"\babout\s+(?:phone|device)\b",
                r"\bwhat\s+(?:phone|device|model)\s+(?:do\s+)?(?:i\s+)?have\b",
            ], 0.85, None),
            (RecognizedAction.STORAGE_INFO, ActionCategory.SYSTEM, [
                r"\b(?:storage|memory|disk)\s+(?:info|space|usage|status)\b",
                r"\bhow\s+much\s+(?:storage|space)\b",
                r"\bfree\s+(?:storage|space)\b",
            ], 0.9, None),
            (RecognizedAction.SCREENSHOT, ActionCategory.SCREEN, [
                r"\bscreenshot\b", r"\bscreen\s*capture\b",
                r"\bcapture\s+(?:the\s+)?screen\b",
                r"\btake\s+(?:a\s+)?screenshot\b",
            ], 0.95, None),
            (RecognizedAction.SCREEN_RECORD, ActionCategory.SCREEN, [
                r"\bscreen\s+record\b", r"\brecord\s+(?:the\s+)?screen\b",
                r"\bscreen\s+recording\b", r"\bstart\s+screen\s+recording\b",
            ], 0.95, None),
            (RecognizedAction.LOCK_DEVICE, ActionCategory.SYSTEM, [
                r"\block\s+(?:the\s+)?(?:phone|device|screen)\b",
            ], 0.95, None),
            (RecognizedAction.READ_NOTIFICATIONS, ActionCategory.NOTIFICATION, [
                r"\b(?:read|check|show|get)\s+(?:my\s+)?notifications?\b",
                r"\bwhat'?s?\s+(?:new|notified)\b",
                r"\bnotification\s+(?:bar|panel|list)\b",
                r"\bshow\s+(?:me\s+)?alerts?\b",
            ], 0.9, None),
            (RecognizedAction.CLEAR_NOTIFICATIONS, ActionCategory.NOTIFICATION, [
                r"\b(?:clear|dismiss|remove)\s+(?:all\s+)?notifications?\b",
            ], 0.9, None),
            (RecognizedAction.CHECK_NETWORK, ActionCategory.SYSTEM, [
                r"\b(?:check|test|show)\s+(?:network|internet|connection)\s+(?:status|speed)\b",
                r"\bis\s+(?:my\s+)?(?:network|internet|wifi)\s+(?:working|connected)\b",
                r"\bnetwork\s+speed\b",
            ], 0.85, None),

            # === SCREEN NAVIGATION ===
            (RecognizedAction.GO_BACK, ActionCategory.NAVIGATION, [
                r"\bgo\s+back\b", r"\bback\b", r"\bprevious\s+screen\b",
                r"\bnavigate\s+back\b", r"\breturn\b",
            ], 0.95, None),
            (RecognizedAction.GO_HOME, ActionCategory.NAVIGATION, [
                r"\bgo\s+home\b", r"\bhome\s+screen\b",
                r"\bgo\s+to\s+(?:the\s+)?home\b",
            ], 0.95, None),
            (RecognizedAction.SCROLL, ActionCategory.NAVIGATION, [
                r"\bscroll\s+(?:up|down|left|right)\b",
            ], 0.9, None),
            (RecognizedAction.REFRESH, ActionCategory.NAVIGATION, [
                r"\brefresh\b", r"\breload\b", r"\bpull\s+to\s+refresh\b",
            ], 0.9, None),

            # === APP ACTIONS ===
            (RecognizedAction.OPEN_APP, ActionCategory.APP, [
                r"\bopen\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
                r"\blaunch\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
                r"\bstart\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
                r"\brun\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
                r"\bgo\s+to\s+(\w+(?:\s+\w+)?)\s*$",
                r"\bswitch\s+to\s+(\w+(?:\s+\w+)?)\s*$",
            ], 0.9, self._extract_app),
            (RecognizedAction.CLOSE_APP, ActionCategory.APP, [
                r"\bclose\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
                r"\bquit\s+(\w+(?:\s+\w+)?)\s*$",
                r"\bkill\s+(\w+(?:\s+\w+)?)\s*$",
                r"\bexit\s+(\w+(?:\s+\w+)?)\s*$",
                r"\bstop\s+(\w+(?:\s+\w+)?)\s*(?:app\s*)?$",
            ], 0.9, self._extract_app),

            # === MESSAGING ===
            (RecognizedAction.SEND_MESSAGE, ActionCategory.MESSAGING, [
                r"\bsend\s+(?:a\s+)?(?:message|text|dm|whatsapp)\s+to\s+(.+?)(?:\s+(?:say|that|saying|with text)\s+(.+?))?$",
                r"\bmessage\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\btext\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\bdm\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\btell\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\bwhatsapp\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\bsend\s+(.+?)\s+to\s+(\w+(?:\s+\w+)?)$",
            ], 0.9, self._extract_message),
            (RecognizedAction.REPLY_MESSAGE, ActionCategory.MESSAGING, [
                r"\breply\b(?:\s+to\s+(.+?))?(?:\s+(?:saying|with|that)\s+(.+?))?$",
                r"\brespond\b(?:\s+to\s+(.+?))?(?:\s+(?:saying|with|that)\s+(.+?))?$",
                r"\banswer\s+(.+?)(?:\s+(?:saying|with|that)\s+(.+?))?$",
            ], 0.85, self._extract_reply),
            (RecognizedAction.OPEN_CHAT, ActionCategory.MESSAGING, [
                r"\bopen\s+(?:chat|conversation|dm)\s+with\s+(\w+(?:\s+\w+)?)",
                r"\bchat\s+with\s+(\w+(?:\s+\w+)?)",
                r"\bgo\s+to\s+(.+?)\s*(?:chat|conversation|dm)",
                r"\bopen\s+(?:\w+\s+)?(?:chat|conversation|dm)\b(?:\s+with\s+(\w+))?",
            ], 0.9, self._extract_chat),
            (RecognizedAction.SEND_EMAIL, ActionCategory.MESSAGING, [
                r"\b(?:send|compose|draft)\s+(?:an?\s+)?email\s+to\s+(.+?)(?:\s+(?:about|subject|saying)\s+(.+?))?$",
                r"\bemail\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
                r"\bgmail\s+(\w+(?:\s+\w+)?)\s+(.+?)$",
            ], 0.9, self._extract_email),

            # === CALLING ===
            (RecognizedAction.MAKE_CALL, ActionCategory.CALL, [
                r"\bcall\s+(\w+(?:\s+\w+)?)(?:\s*(?:at|on)\s*([\d\+\-\(\)\s]+))?$",
                r"\bring\s+(\w+(?:\s+\w+)?)",
                r"\bdial\s+(\w+(?:\s+\w+)?)",
                r"\bphone\s+(\w+(?:\s+\w+)?)",
            ], 0.95, self._extract_call),
            (RecognizedAction.VIDEO_CALL, ActionCategory.CALL, [
                r"\b(?:video\s+call|facetime|videochat)\s+(\w+(?:\s+\w+)?)",
            ], 0.9, self._extract_call),

            # === MEDIA ===
            (RecognizedAction.OPEN_CAMERA, ActionCategory.MEDIA, [
                r"\bopen\s+(?:the\s+)?(?:camera|photo)\s*(?:app\s*)?$",
                r"\blaunch\s+(?:the\s+)?camera\b",
            ], 0.95, None),
            (RecognizedAction.TAKE_PHOTO, ActionCategory.MEDIA, [
                r"\btake\s+(?:a\s+)?(?:photo|picture|selfie|snap)\b",
                r"\bshoot\s+(?:a\s+)?(?:photo|picture)\b",
                r"\bclick\s+(?:a\s+)?(?:photo|picture|selfie)\b",
            ], 0.9, None),
            (RecognizedAction.OPEN_GALLERY, ActionCategory.MEDIA, [
                r"\bopen\s+(?:the\s+)?(?:gallery|photos?)\s*(?:app\s*)?$",
                r"\bshow\s+(?:my\s+)?(?:photos?|gallery|pictures)\b",
                r"\bview\s+(?:my\s+)?(?:photos?|gallery)\b",
            ], 0.9, None),
            (RecognizedAction.PLAY_MEDIA, ActionCategory.MEDIA, [
                r"\bplay\s+(?:some\s+)?(?:music|song|video|audio|track|playlist)\b",
                r"\bplay\s+(?:\w+\s+)?(?:by|from)\s+\w+",
                r"\bplay\s+(?:me\s+)?(.+)$",
                r"\b(start|resume)\s+(?:playing\s+)?(?:the\s+)?(?:music|song|video|audio)\b",
            ], 0.85, self._extract_media),
            (RecognizedAction.SHARE_FILE, ActionCategory.FILE, [
                r"\bshare\s+(?:this\s+)?(?:file|pdf|doc|document|photo|image|picture|video)\s*(?:with\s+(.+?))?",
                r"\bshare\s+(.+?)\s+(?:with|to)\s+(.+?)$",
                r"\bsend\s+(?:this\s+)?(?:file|pdf|doc|document)\s*(?:to|via)\s+(.+?)$",
            ], 0.85, self._extract_share_file),

            # === FILE ===
            (RecognizedAction.OPEN_FILE, ActionCategory.FILE, [
                r"\bopen\s+(?:the\s+)?(?:file|document|pdf)\s+[\"']?(.+?)[\"']?(?:\s+(?:in|with)\s+(.+?))?$",
                r"\bfind\s+(?:and\s+)?open\s+(.+?)$",
                r"\bopen\s+(?:my\s+)?(.+?\.\w+)$",
            ], 0.85, self._extract_file),
            (RecognizedAction.SEARCH_FILE, ActionCategory.FILE, [
                r"\b(?:find|search|locate)\s+(?:the\s+)?(?:file|document|pdf|download)\s+[\"']?(.+?)[\"']?",
                r"\b(?:find|search|locate)\s+(?:my\s+)?(?:downloads?|documents?|files?)\b",
                r"\bwhere\s+is\s+(?:my\s+)?(.+?)(?:\s+(?:file|document|pdf))?\s*$",
            ], 0.85, self._extract_search_file),
            (RecognizedAction.DELETE_FILE, ActionCategory.FILE, [
                r"\b(?:delete|remove|trash)\s+(?:the\s+)?(?:file|photo|image|video|document)\s+[\"']?(.+?)[\"']?",
                r"\bdelete\s+(?:duplicate|similar)\s+(?:photos?|images?|pictures)\b",
            ], 0.85, self._extract_file),
            (RecognizedAction.LIST_FILES, ActionCategory.FILE, [
                r"\b(?:list|show)\s+(?:my\s+)?(?:files?|documents?|downloads?)\b",
            ], 0.85, None),
            (RecognizedAction.OPEN_FOLDER, ActionCategory.FILE, [
                r"\bopen\s+(?:the\s+)?(?:downloads?|documents?|folder|directory)\b",
                r"\bshow\s+(?:my\s+)?(?:downloads?|documents?)\b",
            ], 0.85, None),

            # === SEARCH ===
            (RecognizedAction.SEARCH_WEB, ActionCategory.SEARCH, [
                r"\b(?:search|google|look\s+up|browse|find)\s+(?:the\s+)?(?:web\s+)?(?:for\s+)?(.+?)(?:\s+(?:on|using)\s+(?:google|chrome|web|browser))?\s*$",
                r"\bsearch\s+(?:for\s+)?(.+?)\s+on\s+(?:google|chrome|web)\s*$",
                r"\bgoogle\s+(.+?)$",
            ], 0.85, self._extract_search_query),
            (RecognizedAction.SEARCH_APP, ActionCategory.SEARCH, [
                r"\bsearch\s+(?:for\s+)?(.+?)\s+(?:in|on|using)\s+(.+?)$",
                r"\b(?:in|on|open)\s+(\w+(?:\s+\w+)?)\s+(?:and\s+)?(?:search|find|look)\s+(?:for\s+)?(.+?)$",
                r"\b(?:search|find|look)\s+(?:for\s+)?(.+?)\s+(?:in|on)\s+(.+?)$",
            ], 0.85, self._extract_search_in_app),

            # === KNOWLEDGE ===
            (RecognizedAction.ASK_QUESTION, ActionCategory.KNOWLEDGE, [
                r"\b(?:what|who|where|when|why|how)\s+(?:is|are|was|were|do|does|did|can|could|will|would)",
                r"\btell\s+me\s+(?:about|what|who|where|when|why|how)",
                r"\bexplain\s+(.+?)$",
                r"\bwhat\s+is\s+(.+?)$",
                r"\bwho\s+is\s+(.+?)$",
                r"\bhow\s+(?:to|do|does|can|would)\s+(.+?)$",
                r"\bwhere\s+is\s+(.+?)$",
                r"\bdefine\s+(.+?)$",
            ], 0.8, self._extract_question),

            # === GO TO SCREEN ===
            (RecognizedAction.GO_TO_SCREEN, ActionCategory.NAVIGATION, [
                r"\bnavigate\s+to\s+(.+?)$",
                r"\bgo\s+to\s+(?:the\s+)?(?:(\w+)\s+)?(?:app\s+)?(?:and\s+go\s+to\s+)?(.+?)$",
                r"\bopen\s+(\w+(?:\s+\w+)?)\s+(?:and\s+)?(?:go\s+to|navigate\s+to|open)\s+(.+?)$",
            ], 0.8, self._extract_screen_target),
        ]

        for action, category, regex_list, base_conf, extractor in patterns:
            for pattern in regex_list:
                m = re.search(pattern, text)
                if m:
                    score = base_conf
                    entities = {}
                    if extractor:
                        entities = extractor(m, text)
                    # For specific toggle state, check if on/off
                    if category == ActionCategory.CONNECTIVITY:
                        state = self._detect_toggle_state(text)
                        if state is not None:
                            if "off" in action.value and state == "on":
                                score *= 0.5
                            elif "on" in action.value and state == "off":
                                score *= 0.5
                            entities["state"] = state
                    if score > best.confidence:
                        best = RecognitionResult(
                            action=action,
                            action_category=category,
                            confidence=score,
                            entities=entities,
                            raw_text=raw,
                            normalized_text=text,
                        )

        return best

    # ===== Entity Extractors =====

    def _extract_toggle_state(self, m: re.Match, text: str) -> dict:
        state = self._detect_toggle_state(text)
        return {"state": state or "on"}

    def _detect_toggle_state(self, text: str) -> Optional[str]:
        if re.search(r"\b(?:turn\s+)?on\b", text) and not re.search(r"\bturn\s+off\b", text):
            return "on"
        if re.search(r"\b(?:turn\s+)?off|disable|deactivate\b", text):
            return "off"
        if re.search(r"\benable|activate\b", text):
            return "on"
        return None

    def _extract_app(self, m: re.Match, text: str) -> dict:
        app = m.group(1).strip() if m.lastindex and m.group(1) else ""
        app = re.sub(r"\s+app$", "", app)
        known = self._lookup_app(app)
        return {"app": known or app, "app_raw": app}

    def _extract_message(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1:
            recipient = m.group(1).strip()
            entities["recipient"] = recipient
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            msg = m.group(2).strip().strip("\"'")
            entities["message"] = msg
        # If no message captured from pattern, try extracting from entire text
        if "message" not in entities:
            msg_match = re.search(r"\b(?:say|saying|with text|that says?)\s+\"?(.+?)\"?\s*(?:please|now)?$", text)
            if msg_match:
                entities["message"] = msg_match.group(1).strip().strip("\"'")
        # Detect app from text
        for app_keyword in ["whatsapp", "instagram", "telegram", "messenger", "sms", "messages"]:
            if app_keyword in text.lower():
                entities["app"] = app_keyword
                break
        return entities

    def _extract_reply(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["recipient"] = m.group(1).strip()
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            entities["message"] = m.group(2).strip().strip("\"'")
        # Extract message from "reply saying ..." pattern
        if "message" not in entities:
            msg_match = re.search(r"\b(?:saying|with|that)\s+\"?(.+?)\"?\s*$", text)
            if msg_match:
                entities["message"] = msg_match.group(1).strip().strip("\"'")
        return entities

    def _extract_chat(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["recipient"] = m.group(1).strip()
        for app_keyword in ["whatsapp", "instagram", "telegram", "messenger"]:
            if app_keyword in text.lower():
                entities["app"] = app_keyword
                break
        return entities

    def _extract_call(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            name_or_num = m.group(1).strip()
            if re.match(r"^[\d\+\-\(\)\s]{7,}$", name_or_num):
                entities["phone"] = re.sub(r"[^\d+]", "", name_or_num)
            else:
                entities["recipient"] = name_or_num
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            num = re.sub(r"[^\d+]", "", m.group(2))
            if num:
                entities["phone"] = num
        return entities

    def _extract_email(self, m: re.Match, text: str) -> dict:
        entities = {"app": "gmail"}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["recipient"] = m.group(1).strip()
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            entities["subject"] = m.group(2).strip().strip("\"'")
        match = re.search(r"\b(?:about|subject|with subject)\s+\"?(.+?)\"?\s*$", text)
        if match and "subject" not in entities:
            entities["subject"] = match.group(1).strip().strip("\"'")
        return entities

    def _extract_search_query(self, m: re.Match, text: str) -> dict:
        query = m.group(1).strip().strip("\"'") if m.lastindex and m.group(1) else ""
        return {"query": query}

    def _extract_search_in_app(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 2:
            if m.lastindex >= 2:
                app_part = m.group(1).strip() if m.group(1) else ""
                query_part = m.group(2).strip() if m.group(2) else ""
                entities["app"] = app_part
                entities["query"] = query_part
        if "query" not in entities and m.lastindex and m.lastindex >= 1:
            entities["query"] = m.group(1).strip().strip("\"'")
        return entities

    def _extract_share_file(self, m: re.Match, text: str) -> dict:
        entities = {}
        # Extract recipient
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            entities["recipient"] = m.group(2).strip()
        elif m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["recipient"] = m.group(1).strip()
        # Extract file from "this <file>" pattern
        file_match = re.search(r"\b(?:this|the)\s+(.+?)(?:\s+(?:with|to|via)\s|$)", text)
        if file_match:
            entities["file"] = file_match.group(1).strip()
        # Detect app for sharing
        for app_keyword in ["whatsapp", "telegram", "gmail", "email"]:
            if app_keyword in text.lower():
                entities["app"] = app_keyword
                break
        return entities

    def _extract_file(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["file"] = m.group(1).strip().strip("\"'")
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            entities["app"] = m.group(2).strip()
        return entities

    def _extract_search_file(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["query"] = m.group(1).strip().strip("\"'")
        # Detect file type
        for ftype in ["pdf", "doc", "docx", "xls", "jpg", "png", "mp4", "txt"]:
            if ftype in text.lower():
                entities["type"] = ftype
                break
        return entities

    def _extract_media(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["query"] = m.group(1).strip()
        if "song" in text.lower() or "music" in text.lower():
            entities["type"] = "audio"
        elif "video" in text.lower():
            entities["type"] = "video"
        for app_keyword in ["spotify", "youtube", "music", "gaana", "wynk"]:
            if app_keyword in text.lower():
                entities["app"] = app_keyword
                break
        return entities

    def _extract_question(self, m: re.Match, text: str) -> dict:
        query = m.group(1).strip() if m.lastindex and m.group(1) else text
        return {"query": query}

    def _extract_screen_target(self, m: re.Match, text: str) -> dict:
        """Extract app and screen from 'open X and go to Y' patterns."""
        entities = {}
        # Try to parse "open X and go to Y"
        compound = re.search(r"\bopen\s+(\w+(?:\s+\w+)?)\s+(?:and\s+)?(?:go\s+to|navigate\s+to|open)\s+(.+?)$", text)
        if compound:
            entities["app"] = compound.group(1).strip()
            entities["target_screen"] = compound.group(2).strip()
        elif m.lastindex and m.lastindex >= 1:
            # Find the last non-None group
            target = None
            for i in range(m.lastindex, 0, -1):
                g = m.group(i)
                if g is not None:
                    target = g.strip()
                    break
            if target is None:
                # Use the entire match minus the prefix
                matched = m.group(0)
                for prefix in ["navigate to ", "go to ", "open "]:
                    if matched.lower().startswith(prefix):
                        target = matched[len(prefix):].strip()
                        break
            if target:
                for known_app in ["instagram", "whatsapp", "settings", "youtube", "gmail", "telegram"]:
                    if known_app in target.lower():
                        entities["app"] = known_app
                        entities["target_screen"] = target
                        break
                if "app" not in entities:
                    entities["target_screen"] = target
        return entities

    def _extract_setting_section(self, m: re.Match, text: str) -> dict:
        section = m.group(1).strip() if m.lastindex and m.group(1) else "general"
        section_map = {
            "wifi": "wifi", "bluetooth": "bluetooth", "display": "display",
            "sound": "sound", "notification": "notification", "battery": "battery",
            "storage": "storage", "apps": "apps", "about": "about",
            "network": "network", "security": "security", "lock": "security",
            "wallpaper": "display", "brightness": "display",
        }
        for key, mapped in section_map.items():
            if key in section.lower():
                return {"section": mapped}
        return {"section": section}

    def _extract_brightness(self, m: re.Match, text: str) -> dict:
        entities = {}
        num_match = re.search(r"\b(\d+)\s*(?:%|percent)?", text)
        if num_match:
            entities["level"] = num_match.group(1)
        if re.search(r"\b(?:increase|raise|up|brighter|higher)\b", text):
            entities["direction"] = "up"
        elif re.search(r"\b(?:decrease|lower|down|dimmer|darker)\b", text):
            entities["direction"] = "down"
        return entities

    def _extract_volume(self, m: re.Match, text: str) -> dict:
        entities = {}
        num_match = re.search(r"\b(\d+)\b", text)
        if num_match:
            entities["level"] = num_match.group(1)
        if re.search(r"\b(?:increase|raise|up|louder|higher|max)\b", text):
            entities["direction"] = "up"
        elif re.search(r"\b(?:decrease|lower|down|quieter|mute|silent)\b", text):
            entities["direction"] = "down"
        if re.search(r"\bmute\b|\bsilent\b", text):
            entities["level"] = "0"
        return entities

    def _extract_wifi_connect(self, m: re.Match, text: str) -> dict:
        entities = {}
        if m.lastindex and m.lastindex >= 1 and m.group(1):
            entities["network"] = m.group(1).strip().strip("\"'")
        if m.lastindex and m.lastindex >= 2 and m.group(2):
            entities["password"] = m.group(2).strip().strip("\"'")
        return entities

    # ===== LLM Enhancement =====

    async def _llm_recognize(self, text: str, raw: str) -> Optional[RecognitionResult]:
        llm = await self._get_llm()
        if not llm:
            return None

        prompt = f"""You are an action recognition system for a mobile device AI assistant.
Given a user command, identify the action and extract parameters.

Available actions:
- open_app, close_app, switch_app
- send_message, reply_message, open_chat, send_email
- make_call, video_call
- open_settings, open_setting_section
- toggle_wifi, toggle_bluetooth, toggle_flashlight, toggle_dnd, toggle_mobile_data, toggle_hotspot, toggle_airplane_mode, toggle_location, toggle_auto_rotate
- enable_battery_saver, disable_battery_saver
- adjust_brightness, set_volume
- connect_wifi (with network and optional password)
- play_media, take_photo, open_camera, open_gallery
- search_web, search_file, search_app
- open_file, delete_file, share_file, list_files
- screenshot, screen_record, lock_device, reboot, battery_status, device_info, storage_info
- read_notifications, clear_notifications
- go_back, go_home, go_to_screen, scroll, refresh
- ask_question, summarize, explain, translate, find_info
- unknown

Respond with JSON:
{{"action": "action_name", "confidence": 0.0-1.0, "entities": {{"key": "value"}}, "category": "category_name"}}

User: {text}
JSON:"""
        try:
            result = await asyncio.wait_for(llm.generate_json(prompt), timeout=10.0)
            if "action" in result:
                action_name = result["action"]
                confidence = float(result.get("confidence", 0.5))
                entities = result.get("entities", {})
                category = result.get("category", "unknown")
                try:
                    action_enum = RecognizedAction(action_name)
                except ValueError:
                    action_enum = RecognizedAction.UNKNOWN
                try:
                    cat_enum = ActionCategory(category)
                except ValueError:
                    cat_enum = ActionCategory.UNKNOWN
                return RecognitionResult(
                    action=action_enum,
                    action_category=cat_enum,
                    confidence=confidence,
                    entities=entities,
                    raw_text=raw,
                    normalized_text=text,
                )
        except Exception as e:
            logger.warning(f"LLM recognition failed: {e}")
        return None

    # ===== Compound Commands =====

    def _detect_compound(self, text: str, first_result: RecognitionResult) -> Optional[RecognitionResult]:
        """Detect compound commands like 'open X and do Y'."""
        # Check for "and" followed by another action
        compound_patterns = [
            (r"\bopen\s+(\w+(?:\s+\w+)?)\s+and\s+(go\s+to|navigate\s+to|open)\s+(.+?)$",
             RecognizedAction.OPEN_APP, RecognizedAction.GO_TO_SCREEN),
            (r"\bopen\s+(\w+(?:\s+\w+)?)\s+and\s+(?:then\s+)?(search|find|look)\s+(?:for\s+)?(.+?)$",
             RecognizedAction.OPEN_APP, RecognizedAction.SEARCH_APP),
            (r"\b(?:search|find|look)\s+(?:for\s+)?(.+?)\s+(?:in|on|using)\s+(\w+(?:\s+\w+)?)$",
             RecognizedAction.SEARCH_APP, RecognizedAction.SEARCH_APP),
        ]
        for pattern, first_action, second_action in compound_patterns:
            m = re.search(pattern, text)
            if m:
                sub1 = RecognitionResult(
                    action=first_action, action_category=ActionCategory.APP,
                    confidence=0.9, entities={},
                )
                sub2 = RecognitionResult(
                    action=second_action, action_category=ActionCategory.SEARCH,
                    confidence=0.85, entities={},
                )
                # Parse sub-entity from compound match
                if first_action == RecognizedAction.OPEN_APP and m.lastindex and m.lastindex >= 1:
                    sub1.entities["app"] = m.group(1).strip()
                if second_action == RecognizedAction.GO_TO_SCREEN and m.lastindex and m.lastindex >= 3:
                    sub2.entities["target_screen"] = m.group(3).strip()
                    sub2.entities["app"] = m.group(1).strip()
                if second_action == RecognizedAction.SEARCH_APP:
                    if m.lastindex and m.lastindex == 2:
                        sub2.entities["query"] = m.group(1).strip()
                        sub1.entities["app"] = m.group(2).strip()
                    elif m.lastindex and m.lastindex >= 3:
                        sub1.entities["app"] = m.group(1).strip()
                        sub2.entities["query"] = m.group(3).strip()
                        sub2.entities["app"] = m.group(1).strip()

                return RecognitionResult(
                    action=first_action,
                    action_category=ActionCategory.APP,
                    confidence=0.85,
                    entities=sub1.entities,
                    raw_text=text,
                    is_compound=True,
                    sub_actions=[sub1, sub2],
                )
        return None

    def _apply_context(self, result: RecognitionResult, context: Dict[str, Any]) -> RecognitionResult:
        """Fill in missing entities from conversation context."""
        if not result.entities.get("app") and context.get("last_app"):
            result.entities["app"] = context["last_app"]
            result.confidence = min(result.confidence + 0.1, 1.0)
        if not result.entities.get("recipient") and context.get("last_recipient"):
            result.entities["recipient"] = context["last_recipient"]
            result.confidence = min(result.confidence + 0.1, 1.0)
        if result.action == RecognizedAction.UNKNOWN and context.get("last_intent"):
            try:
                result.action = RecognizedAction(context["last_intent"])
                result.confidence = 0.6
            except ValueError:
                pass
        return result

    def _extract_entities_deep(self, text: str, result: RecognitionResult) -> None:
        """Deep entity extraction for patterns that the regex missed."""
        # Detect app names from any position
        if not result.entities.get("app"):
            for known in ["whatsapp", "instagram", "telegram", "youtube", "gmail",
                          "chrome", "settings", "camera", "spotify", "facebook",
                          "twitter", "linkedin", "messenger", "discord",
                          "calculator", "clock", "calendar", "maps", "photos",
                          "drive", "files", "phone", "dialer"]:
                if known in text.lower():
                    result.entities["app"] = known
                    break

    def _lookup_app(self, name: str) -> Optional[str]:
        """Look up app name in known apps mapping."""
        from understanding.entity_extractor import KNOWN_APPS
        name_lower = name.strip().lower()
        if name_lower in KNOWN_APPS:
            return name_lower
        for alias, pkg in KNOWN_APPS.items():
            if name_lower in alias or alias in name_lower:
                return alias
        return None


_recognizer: Optional[ActionRecognizer] = None


def get_action_recognizer() -> ActionRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = ActionRecognizer()
    return _recognizer
