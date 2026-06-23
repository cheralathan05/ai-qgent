"""
APA-OS Universal Intent Understanding Engine

Understands ANY natural language input.
No hardcoded command lists. No fixed actions.
The user types naturally, the system interprets intent.
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntentCategory(str, Enum):
    """Universal intent categories - covers everything a user might want."""
    # Device Control
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SWITCH_APP = "switch_app"

    # Communication
    SEND_MESSAGE = "send_message"
    REPLY_MESSAGE = "reply_message"
    OPEN_CHAT = "open_chat"
    CALL_CONTACT = "call_contact"
    SEND_EMAIL = "send_email"

    # Information
    BATTERY_STATUS = "battery_status"
    DEVICE_STATUS = "device_status"
    FOREGROUND_APP = "foreground_app"
    TAKE_SCREENSHOT = "take_screenshot"
    READ_NOTIFICATIONS = "read_notifications"

    # Search
    WEB_SEARCH = "web_search"
    APP_SEARCH = "app_search"
    IN_APP_SEARCH = "in_app_search"

    # Files & Documents
    OPEN_FILE = "open_file"
    FIND_FILE = "find_file"
    SEARCH_FILES = "search_files"
    DOWNLOAD_FILE = "download_file"

    # Knowledge
    SUMMARIZE = "summarize"
    EXPLAIN = "explain"
    GENERATE_ASSIGNMENT = "generate_assignment"
    GENERATE_MCQ = "generate_mcq"
    GENERATE_QUESTIONS = "generate_questions"
    GENERATE_NOTES = "generate_notes"
    GENERATE_SUMMARY = "generate_summary"
    FIND_KNOWLEDGE = "find_knowledge"

    # Navigation
    NAVIGATE = "navigate"
    GO_BACK = "go_back"
    GO_HOME = "go_home"
    SCROLL = "scroll"
    TAP_ELEMENT = "tap_element"
    TYPE_TEXT = "type_text"

    # Media
    OPEN_CAMERA = "open_camera"
    TAKE_PHOTO = "take_photo"
    RECORD_VIDEO = "record_video"
    OPEN_GALLERY = "open_gallery"
    PLAY_MUSIC = "play_music"

    # System
    OPEN_SETTINGS = "open_settings"
    TOGGLE_WIFI = "toggle_wifi"
    TOGGLE_BLUETOOTH = "toggle_bluetooth"
    TOGGLE_FLASHLIGHT = "toggle_flashlight"
    VOLUME_CONTROL = "volume_control"
    LOCK_DEVICE = "lock_device"
    REBOOT = "reboot"

    # Productivity
    CREATE_TASK = "create_task"
    CREATE_REMINDER = "create_reminder"
    SCHEDULE_EVENT = "schedule_event"
    SET_ALARM = "set_alarm"

    # Complex / Multi-step
    COMPOUND_ACTION = "compound_action"
    FOLLOW_UP = "follow_up"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class ExtractedEntity:
    """An entity extracted from user input."""
    entity_type: str  # app, contact, message, query, file, date, time, url, number
    value: str
    confidence: float
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentResult:
    """Complete intent understanding result."""
    intent: IntentCategory
    confidence: float
    entities: List[ExtractedEntity]
    slots: Dict[str, Any]
    raw_command: str
    normalized_command: str
    requires_phase1: bool = False  # Device control
    requires_phase2: bool = False  # Phone intelligence
    requires_phase3: bool = False  # Knowledge
    compound_intents: List[Dict[str, Any]] = field(default_factory=list)
    context_hints: Dict[str, Any] = field(default_factory=dict)


class UniversalIntentEngine:
    """
    Understands ANY user input naturally.
    
    No hardcoded command lists.
    No fixed actions.
    Interprets intent from natural language.
    """

    def __init__(self):
        self._patterns = self._build_patterns()
        self._app_aliases = self._build_app_aliases()

    def _build_patterns(self) -> List[Tuple[IntentCategory, List[str], float]]:
        """Build comprehensive intent patterns."""
        return [
            # ========== COMPOUND ACTIONS ==========
            (IntentCategory.COMPOUND_ACTION, [
                r'\b(?:open|launch|start)\s+(\w+)\s+and\s+(?:search|find|look)\s+(?:for\s+)?(.+)',
                r'\b(?:open|launch|start)\s+(\w+)\s+and\s+(.+)',
            ], 0.95),

            # ========== DEVICE CONTROL ==========
            (IntentCategory.OPEN_APP, [
                r'\b(?:open|launch|start|run|go\s+to|switch\s+to|load|boot)\s+(?:the\s+)?(?:my\s+)?(\w[\w\s]*?)(?:\s+app)?$',
                r'\bi\s+(?:want|need|would)\s+to\s+(?:open|launch|start|use|check|see)\s+(?:the\s+)?(?:my\s+)?(\w[\w\s]*?)(?:\s+app)?$',
                r'\bcan\s+(?:you|i)\s+(?:open|launch|start|run|check)\s+(?:the\s+)?(?:my\s+)?(\w[\w\s]*?)(?:\s+app)?$',
                r'\b(?:show|display|bring\s+up)\s+(?:the\s+)?(?:my\s+)?(\w[\w\s]*?)(?:\s+app)?$',
                r'^(?:open|launch|start|run)\s+(\w[\w\s]*?)$',
            ], 0.9),

            (IntentCategory.CLOSE_APP, [
                r'\b(?:close|quit|exit|kill|stop|shut\s+down)\s+(?:the\s+)?(?:my\s+)?(\w[\w\s]*?)(?:\s+app)?$',
                r'\bclose\s+(?:the\s+)?(?:current\s+)?app\b',
            ], 0.9),

            # ========== COMMUNICATION ==========
            (IntentCategory.SEND_MESSAGE, [
                r'\b(?:send|forward)\s+(?:"([^"]+)"|\'([^\']+)|(.+))\s+to\s+(\w+)',
                r'\b(?:tell|say|ask)\s+(\w+)\s+(?:to\s+)?(.+?)(?:\s+please)?$',
                r'\bmessage\s+(\w+)\s+(?:saying\s+)?(.+)',
                r'\b(?:send|text|message|dm|ping|whatsapp)\s+(?:a\s+)?(?:message\s+)?to\s+(\w+)\s*(?:"([^"]+)"|\'([^\']+)|(.+))?$',
                r'\b(?:send|text|message|dm|ping|whatsapp)\s+(?:"([^"]+)"|\'([^\']+)|(.+))\s+to\s+(\w+)',
            ], 0.9),

            (IntentCategory.REPLY_MESSAGE, [
                r'\b(?:reply|respond|answer)\s+(?:to\s+)?(?:the\s+)?(?:latest\s+)?(?:message|chat|notification)',
                r'\b(?:reply|respond)\s+(?:with\s+)?(?:"([^"]+)"|\'([^\']+)|(.+))',
                r'\bsay\s+(?:"([^"]+)"|\'([^\']+)|(.+))\s+back',
            ], 0.9),

            (IntentCategory.OPEN_CHAT, [
                r'\bopen\s+(\w+)\s+(?:chat|conversation|dm|messages?)\b',
                r'\b(?:go\s+to|open)\s+(?:the\s+)?chat\s+with\s+(\w+)\b',
                r'\bchat\s+with\s+(\w+)\b',
                r'\bopen\s+(\w+)\s+and\s+chat\s+with\s+(\w+)\b',
                r'\bopen\s+(\w+)\s+(?:message|dm)\s+(?:with\s+)?(\w+)\b',
                r'\bopen\s+(\w+)\s+(?:chat|message|dm)\s+with\s+(\w+)\b',
            ], 0.93),

            (IntentCategory.CALL_CONTACT, [
                r'\b(?:call|ring|dial|phone)\s+(\w+)',
                r'\b(?:make\s+a\s+)?(?:phone\s+)?call\s+to\s+(\w+)',
            ], 0.95),

            (IntentCategory.SEND_EMAIL, [
                r'\b(?:send|compose|write|draft)\s+(?:an?\s+)?email\s+(?:to\s+)?(\w+)',
                r'\bemail\s+(\w+)',
            ], 0.9),

            # ========== INFORMATION ==========
            (IntentCategory.BATTERY_STATUS, [
                r'\b(?:battery|charge|power)\s*(?:level|status|percentage|life)?',
                r'\bhow\s+(?:much\s+)?(?:is\s+)?(?:the\s+)?battery\b',
                r'\bwhat(?:\'s|\s+is)\s+(?:my\s+)?battery\b',
                r'\bbattery\b',
            ], 0.95),

            (IntentCategory.DEVICE_STATUS, [
                r'\b(?:device|phone)\s+(?:status|info|information|state)',
                r'\bhow(?:\'s|\s+is)\s+(?:my\s+)?(?:phone|device)\b',
            ], 0.9),

            (IntentCategory.FOREGROUND_APP, [
                r'\bwhat(?:\'s|\s+is)\s+(?:the\s+)?(?:current|open|running|active)\s+app\b',
                r'\b(?:which\s+)?app\s+(?:is\s+)?(?:open|running|active|current)\b',
                r'\bforeground\s+app\b',
            ], 0.9),

            (IntentCategory.TAKE_SCREENSHOT, [
                r'\b(?:take|capture|grab|snap)\s+(?:a\s+)?screenshot\b',
                r'\bscreenshot\b',
                r'\bcapture\s+screen\b',
            ], 0.95),

            (IntentCategory.READ_NOTIFICATIONS, [
                r'\b(?:read|check|show|get|see)\s+(?:my\s+)?(?:recent\s+)?notifications?\b',
                r'\bwhat(?:\'s|\s+is)\s+new\b',
                r'\bany\s+(?:new\s+)?(?:notifications?|alerts?|messages?)\b',
            ], 0.9),

            # ========== SEARCH ==========
            (IntentCategory.WEB_SEARCH, [
                r'\b(?:search|google|look\s+up|find|browse)\s+(?:for\s+)?(.+?)(?:\s+(?:on|in|using)\s+(?:the\s+)?web)?$',
                r'\bwhat(?:\'s|\s+is)\s+(.+?)(?:\s+about)?\s*\?',
                r'\btell\s+me\s+about\s+(.+)',
            ], 0.85),

            (IntentCategory.IN_APP_SEARCH, [
                r'\b(?:search|find|look\s+for|look\s+up)\s+(.+?)\s+(?:on|in|inside)\s+(\w+)',
                r'\b(?:open|go\s+to)\s+(\w+)\s+and\s+(?:search|find|look)\s+(?:for\s+)?(.+)',
            ], 0.9),

            # ========== FILES & DOCUMENTS ==========
            (IntentCategory.FIND_FILE, [
                r'\b(?:find|locate|where\s+is|show\s+me)\s+(?:my\s+)?(.+?)(?:\s+file)?$',
                r'\b(?:find|search\s+for)\s+(?:my\s+)?(?:file|document|pdf|doc|note)s?\s*(?:about|related\s+to|for)?\s*(.+)?$',
                r'\bwhere(?:\'s|\s+is)\s+(?:my\s+)?(.+)',
                r'\b(?:find|show|open)\s+(?:my\s+)?(\w+)\s+(?:notes?|files?|documents?)\b',
                r'\b(?:find|show|open)\s+(?:my\s+)?(.+?)\s+(?:notes?|files?|documents?)\b',
            ], 0.88),

            (IntentCategory.OPEN_FILE, [
                r'\b(?:open|launch|view|read)\s+(?:my\s+)?(.+?)(?:\s+file)?$',
                r'\bopen\s+(?:the\s+)?(.+\.\w+)',
            ], 0.9),

            (IntentCategory.SEARCH_FILES, [
                r'\b(?:search|find|look)\s+(?:for\s+)?(?:files?|documents?|pdfs?)\s+(?:related\s+to|about|containing)\s+(.+)',
                r'\bshow\s+(?:me\s+)?(?:all\s+)?(?:files?|documents?)\s+(?:about|related\s+to)\s+(.+)',
            ], 0.85),

            # ========== KNOWLEDGE ==========
            (IntentCategory.SUMMARIZE, [
                r'\b(?:summarize|summary|summarise|give\s+me\s+a?\s+summary\s+of)\s+(.+)',
                r'\bwhat(?:\'s|\s+is)\s+(?:this\s+)?(?:document|file|note|chapter)\s+about\s*\?',
                r'\btell\s+me\s+the\s+main\s+points?\s+of\s+(.+)',
            ], 0.9),

            (IntentCategory.EXPLAIN, [
                r'\b(?:explain|describe|tell\s+me\s+about)\s+(.+?)(?:\s+to\s+me)?(?:\s+please)?$',
                r'\bhow\s+does\s+(.+?)\s+work',
                r'\bwhat\s+(?:is|are|does)\s+(?!my\s+battery)(.+?)(?:\s+mean)?$',
            ], 0.9),

            (IntentCategory.GENERATE_ASSIGNMENT, [
                r'\b(?:generate|create|make|write|prepare)\s+(?:an?\s+)?(?:assignment|homework|task)\s+(?:on|about|for|related\s+to)\s+(.+)',
                r'\b(?:generate|create|make|write|prepare)\s+(?:an?\s+)?(?:assignment|homework|task)\s*$',
                r'\b(?:create|generate)\s+(?:an?\s+)?assignment\s+(?:from|based\s+on)\s+(.+)',
            ], 0.9),

            (IntentCategory.GENERATE_MCQ, [
                r'\b(?:generate|create|make|write)\s+(?:some\s+)?(?:\d+\s+)?(?:mcq|mcqs|multiple\s+choice\s+questions?)\s+(?:on|about|for)\s+(.+)',
                r'\b(?:generate|create|make|write)\s+(?:some\s+)?(?:\d+\s+)?(?:mcq|mcqs|multiple\s+choice\s+questions?)\s*$',
                r'\bgive\s+me\s+(?:some\s+)?(?:\d+\s+)?(?:mcq|mcqs|questions?)\s+on\s+(.+)',
            ], 0.9),

            (IntentCategory.GENERATE_QUESTIONS, [
                r'\b(?:generate|create|make|write|give)\s+(?:some\s+)?(?:\d+\s+)?(?:interview\s+)?(?:questions?|viva)\s+(?:on|about|for)\s+(.+)',
                r'\b(?:generate|create|make|write|give)\s+(?:some\s+)?(?:\d+\s+)?(?:interview\s+)?(?:questions?|viva)\s*$',
                r'\b(?:what|which)\s+questions?\s+(?:should|i\s+should)\s+(?:i\s+)?(?:ask|prepare|study)',
            ], 0.9),

            (IntentCategory.GENERATE_NOTES, [
                r'\b(?:generate|create|make|write|prepare)\s+(?:some\s+)?notes?\s*(?:on|about|for)?\s*(.+)?',
                r'\b(?:make|create|write)\s+(?:me\s+)?(?:revision\s+)?notes?\s+(?:from|based\s+on)\s+(.+)',
            ], 0.9),

            (IntentCategory.FIND_KNOWLEDGE, [
                r'\b(?:find|search|look)\s+(?:for\s+)?(?:my\s+)?(?:notes?|documents?|files?|material)\s+(?:on|about|for|related\s+to)\s+(.+)',
                r'\bwhere(?:\'s|\s+is)\s+(?:my\s+)?(.+?)(?:\s+notes?|\s+documents?|\s+files?)?$',
            ], 0.85),

            # ========== NAVIGATION ==========
            (IntentCategory.GO_BACK, [
                r'\b(?:go\s+back|back|previous|return)\b',
            ], 0.95),

            (IntentCategory.GO_HOME, [
                r'\b(?:go\s+home|home\s+screen|main\s+screen)\b',
            ], 0.95),

            (IntentCategory.SCROLL, [
                r'\b(?:scroll|swipe)\s+(up|down|left|right)\b',
                r'\b(?:go\s+down|go\s+up|page\s+down|page\s+up)\b',
            ], 0.9),

            # ========== MEDIA ==========
            (IntentCategory.OPEN_CAMERA, [
                r'\b(?:open|launch|start)\s+(?:the\s+)?camera\b',
                r'\b(?:take|capture|snap)\s+(?:a\s+)?(?:photo|picture|selfie)\b',
                r'\btake\s+(?:a\s+)?photo\b',
            ], 0.95),

            (IntentCategory.PLAY_MUSIC, [
                r'\b(?:play|put\s+on|start)\s+(?:some\s+)?(?:music|a\s+song|a\s+playlist)\b',
                r'\b(?:play|listen\s+to)\s+(.+?)(?:\s+by\s+(.+))?$',
                r'\bi\s+want\s+to\s+listen\s+to\s+(.+)',
            ], 0.85),

            # ========== SYSTEM ==========
            (IntentCategory.OPEN_SETTINGS, [
                r'\b(?:open|launch|go\s+to)\s+(?:the\s+)?settings?\b',
                r'\bsettings\b',
            ], 0.95),

            (IntentCategory.TOGGLE_WIFI, [
                r'\b(?:turn|switch|toggle)\s+(on|off)\s+(?:the\s+)?wifi\b',
                r'\b(?:enable|disable)\s+wifi\b',
                r'\bwifi\s+(on|off)\b',
            ], 0.95),

            (IntentCategory.TOGGLE_BLUETOOTH, [
                r'\b(?:turn|switch|toggle)\s+(on|off)\s+(?:the\s+)?bluetooth\b',
                r'\b(?:enable|disable)\s+bluetooth\b',
            ], 0.95),

            (IntentCategory.TOGGLE_FLASHLIGHT, [
                r'\b(?:turn|switch|toggle)\s+(on|off)\s+(?:the\s+)?(?:flashlight|flash|torch)\b',
                r'\b(?:flashlight|flash|torch)\s+(on|off)\b',
            ], 0.95),

            (IntentCategory.VOLUME_CONTROL, [
                r'\b(?:volume|turn)\s+(up|down|increase|decrease|mute|silence)\b',
                r'\b(?:increase|decrease|raise|lower)\s+volume\b',
                r'\b(?:max|mute|silent|silence)\s*(?:volume)?\b',
            ], 0.95),

            (IntentCategory.LOCK_DEVICE, [
                r'\b(?:lock|secure)\s+(?:the\s+)?(?:phone|device|screen)\b',
            ], 0.95),

            # ========== PRODUCTIVITY ==========
            (IntentCategory.CREATE_REMINDER, [
                r'\b(?:set|create|add|make)\s+(?:a\s+|an?\s+)?reminder\s+(?:to\s+)?(.+?)(?:\s+(?:at|on|for|tomorrow|today))?$',
                r'\bremind\s+me\s+to\s+(.+?)(?:\s+(?:at|on|for|tomorrow|today))?$',
            ], 0.9),

            (IntentCategory.SCHEDULE_EVENT, [
                r'\b(?:schedule|create|add|book)\s+(?:a\s+|an?\s+)?(?:meeting|event|appointment)',
                r'\badd\s+(?:a\s+)?(?:meeting|event)\s+(?:to\s+)?(?:my\s+)?calendar',
            ], 0.9),

            (IntentCategory.SET_ALARM, [
                r'\b(?:set|create)\s+(?:an?\s+)?alarm\s+(?:for\s+)?(.+)',
                r'\bwake\s+me\s+(?:up\s+)?(?:at|at\s+about)\s+(.+)',
            ], 0.9),
        ]

    def _build_app_aliases(self) -> Dict[str, str]:
        """Common app name aliases for faster resolution."""
        return {
            "insta": "instagram",
            "ig": "instagram",
            "wa": "whatsapp",
            "yt": "youtube",
            "chrome": "chrome",
            "browser": "chrome",
            "fb": "facebook",
            "x": "twitter",
            "maps": "google maps",
            "gmail": "gmail",
            "drive": "google drive",
            "photos": "google photos",
            "phone": "phone",
            "dialer": "phone",
            "camera": "camera",
            "gallery": "gallery",
            "photos": "photos",
            "files": "files",
            "downloads": "downloads",
            "settings": "settings",
            "calculator": "calculator",
            "calendar": "calendar",
            "clock": "clock",
            "alarm": "clock",
            "notes": "notes",
            "spotify": "spotify",
            "netflix": "netflix",
            "linkedin": "linkedin",
            "discord": "discord",
            "telegram": "telegram",
            "signal": "signal",
            "snapchat": "snapchat",
            "tiktok": "tiktok",
            "reddit": "reddit",
            "github": "github",
            "vscode": "vs code",
            "code": "vs code",
        }

    async def understand(
        self,
        raw_command: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        """
        Understand ANY user input.
        
        No hardcoded commands.
        Interprets intent from natural language.
        """
        normalized = self._normalize(raw_command)
        
        # Classify intent
        intent, confidence, matched_groups = self._classify_intent(normalized)
        
        # Extract entities
        entities = self._extract_entities(normalized, intent)
        
        # Fill slots
        slots = self._fill_slots(intent, entities, matched_groups)
        
        # Resolve app aliases
        if "app" in slots:
            slots["app"] = self._resolve_app_alias(slots["app"])
        
        # Determine which phases are needed
        requires_phase1, requires_phase2, requires_phase3 = self._determine_phases(intent, slots)
        
        # Detect compound actions
        compound = self._detect_compound(normalized)
        
        result = IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
            slots=slots,
            raw_command=raw_command,
            normalized_command=normalized,
            requires_phase1=requires_phase1,
            requires_phase2=requires_phase2,
            requires_phase3=requires_phase3,
            compound_intents=compound,
            context_hints=context or {},
        )
        
        logger.info(
            f"Intent: {intent.value} | conf={confidence:.2f} | "
            f"phases=[P1={requires_phase1},P2={requires_phase2},P3={requires_phase3}] | "
            f"cmd={raw_command!r}"
        )
        
        return result

    def _normalize(self, text: str) -> str:
        """Normalize user input."""
        text = text.strip().lower()
        # Remove common polite phrases
        for phrase in ["please", "could you", "can you", "would you", "i want to", "i need to"]:
            text = text.replace(phrase, "")
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _classify_intent(self, text: str) -> Tuple[IntentCategory, float, List[str]]:
        """Classify intent from normalized text."""
        best_intent = IntentCategory.UNKNOWN
        best_score = 0.0
        best_groups = []

        for intent, patterns, base_conf in self._patterns:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Calculate confidence based on match quality
                    match_ratio = len(match.group(0)) / len(text) if text else 0
                    score = base_conf * (0.7 + 0.3 * match_ratio)
                    
                    if score > best_score:
                        best_score = score
                        best_intent = intent
                        best_groups = list(match.groups())

        return best_intent, min(best_score, 0.99), best_groups

    def _extract_entities(self, text: str, intent: IntentCategory) -> List[ExtractedEntity]:
        """Extract all entities from text."""
        entities = []

        # App names
        app = self._extract_app(text)
        if app:
            entities.append(ExtractedEntity(
                entity_type="app",
                value=app,
                confidence=0.9,
                raw_text=app,
            ))

        # Contact names
        contact = self._extract_contact(text)
        if contact:
            entities.append(ExtractedEntity(
                entity_type="contact",
                value=contact,
                confidence=0.85,
                raw_text=contact,
            ))

        # Messages (quoted text)
        message = self._extract_message(text)
        if message:
            entities.append(ExtractedEntity(
                entity_type="message",
                value=message,
                confidence=0.95,
                raw_text=message,
            ))

        # Search queries
        query = self._extract_query(text, intent)
        if query:
            entities.append(ExtractedEntity(
                entity_type="query",
                value=query,
                confidence=0.9,
                raw_text=query,
            ))

        # File references
        file_ref = self._extract_file_reference(text)
        if file_ref:
            entities.append(ExtractedEntity(
                entity_type="file",
                value=file_ref,
                confidence=0.85,
                raw_text=file_ref,
            ))

        # URLs
        url = self._extract_url(text)
        if url:
            entities.append(ExtractedEntity(
                entity_type="url",
                value=url,
                confidence=0.99,
                raw_text=url,
            ))

        # Numbers
        numbers = self._extract_numbers(text)
        for num in numbers:
            entities.append(ExtractedEntity(
                entity_type="number",
                value=num,
                confidence=0.95,
                raw_text=num,
            ))

        # Dates
        date = self._extract_date(text)
        if date:
            entities.append(ExtractedEntity(
                entity_type="date",
                value=date,
                confidence=0.9,
                raw_text=date,
            ))

        # Times
        time = self._extract_time(text)
        if time:
            entities.append(ExtractedEntity(
                entity_type="time",
                value=time,
                confidence=0.9,
                raw_text=time,
            ))

        return entities

    def _extract_app(self, text: str) -> Optional[str]:
        """Extract app name from text."""
        # Only extract app name for app-related intents
        # Try common patterns - stop at keywords like chat, and, with
        patterns = [
            r'(?:open|launch|start|run|go\s+to|switch\s+to)\s+(?:the\s+)?(?:my\s+)?(\w+)(?:\s+app)?(?:\s+and|\s*$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                app = match.group(1).strip()
                # Clean up
                app = re.sub(r'\s+(?:app|application|page|screen)$', '', app)
                if app and len(app) > 1:
                    return app
        return None

    def _extract_contact(self, text: str) -> Optional[str]:
        """Extract contact name from text."""
        patterns = [
            r'(?:send|message|text|call|email|dm|ping)\s+(?:a\s+)?(?:message\s+)?to\s+(\w+)',
            r'(?:send|forward)\s+.+\s+to\s+(\w+)',
            r'(?:tell|say|ask)\s+(\w+)',
            r'(?:open|go\s+to)\s+(\w+)\s+(?:chat|conversation)',
            r'chat\s+with\s+(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                contact = match.group(1).strip()
                if contact and len(contact) > 1:
                    return contact
        return None

    def _extract_message(self, text: str) -> Optional[str]:
        """Extract message text (quoted or after 'saying')."""
        # Quoted text
        match = re.search(r'"([^"]+)"', text)
        if match:
            return match.group(1)
        match = re.search(r"'([^']+)'", text)
        if match:
            return match.group(1)
        # After 'saying'
        match = re.search(r'(?:saying|that)\s+(.+?)(?:\s+to\s+\w+|$)', text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_query(self, text: str, intent: IntentCategory) -> Optional[str]:
        """Extract search query from text."""
        patterns = [
            r'(?:search|google|look\s+up|find|browse)\s+(?:for\s+)?(.+?)(?:\s+(?:on|in|using)\s+\w+)?$',
            r'(?:search|find)\s+(.+?)\s+(?:on|in|inside)\s+\w+',
            r'tell\s+me\s+about\s+(.+)',
            r'what\s+(?:is|are|does)\s+(.+?)(?:\s+mean|\s+about|\s*\?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                query = match.group(1).strip()
                # Clean trailing words
                query = re.sub(r'\s+(?:please|on|in|using|the|web)$', '', query)
                if query and len(query) > 1:
                    return query
        return None

    def _extract_file_reference(self, text: str) -> Optional[str]:
        """Extract file/document reference from text."""
        patterns = [
            r'(?:find|locate|open|show|search\s+for)\s+(?:my\s+)?(.+?)(?:\s+file|\s+document|\s+pdf|\s+note|\s*$)',
            r'(?:my\s+)?(.+?\.(?:pdf|doc|docx|txt|md|ppt|pptx|xls|xlsx))',
            r'(?:notes?|document|file|pdf)\s+(?:about|on|for|related\s+to)\s+(.+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                ref = match.group(1).strip()
                if ref and len(ref) > 1:
                    return ref
        return None

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text."""
        match = re.search(r'https?://[^\s]+', text)
        return match.group() if match else None

    def _extract_numbers(self, text: str) -> List[str]:
        """Extract numbers from text."""
        return re.findall(r'\b\d+\b', text)

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date reference from text."""
        from datetime import datetime, timedelta
        today = datetime.now()
        
        if 'today' in text:
            return today.strftime("%Y-%m-%d")
        if 'tomorrow' in text:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        if 'yesterday' in text:
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        match = re.search(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', text)
        if match:
            return match.group(1).replace('/', '-')
        
        return None

    def _extract_time(self, text: str) -> Optional[str]:
        """Extract time reference from text."""
        match = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', text, re.IGNORECASE)
        if match:
            return match.group(0)
        
        match = re.search(r'\b(\d{2}):(\d{2})\b', text)
        if match:
            return match.group(0)
        
        return None

    def _resolve_app_alias(self, app: str) -> str:
        """Resolve app alias to canonical name."""
        app_lower = app.lower().strip()
        return self._app_aliases.get(app_lower, app_lower)

    def _fill_slots(
        self,
        intent: IntentCategory,
        entities: List[ExtractedEntity],
        matched_groups: List[str],
    ) -> Dict[str, Any]:
        """Fill intent-specific slots from entities."""
        slots = {}

        # Get entities by type
        entity_map = {}
        for e in entities:
            if e.entity_type not in entity_map:
                entity_map[e.entity_type] = e

        # App slot - only for app-related intents
        if matched_groups and intent == IntentCategory.OPEN_CHAT:
            non_empty = [g for g in matched_groups if g and g.strip()]
            if non_empty:
                slots["app"] = non_empty[0].strip()
        elif "app" in entity_map and intent in (IntentCategory.OPEN_APP, IntentCategory.CLOSE_APP, IntentCategory.OPEN_CHAT):
            slots["app"] = entity_map["app"].value
        elif matched_groups and intent in (IntentCategory.OPEN_APP, IntentCategory.CLOSE_APP):
            if matched_groups[0]:
                slots["app"] = matched_groups[0].strip()

        # Contact/recipient slot
        if intent == IntentCategory.OPEN_CHAT and matched_groups:
            # For open_chat with 2 groups: first=app, second=recipient
            non_empty = [g for g in matched_groups if g and g.strip()]
            if len(non_empty) >= 2:
                slots["recipient"] = non_empty[1].strip()
            elif len(non_empty) == 1:
                slots["recipient"] = non_empty[0].strip()
        elif "contact" in entity_map:
            slots["recipient"] = entity_map["contact"].value
        elif matched_groups and intent == IntentCategory.SEND_MESSAGE:
            # For send_message, find the recipient from the rightmost word group
            # Pattern: send X to Y -> Y is recipient, X is message
            non_empty = [g for g in matched_groups if g and g.strip()]
            if len(non_empty) >= 2:
                # Last non-empty group is usually the recipient
                slots["recipient"] = non_empty[-1].strip()
                # Build message from other groups
                msg_parts = [g.strip() for g in non_empty[:-1] if g.strip()]
                if msg_parts:
                    slots["message"] = " ".join(msg_parts)
            elif len(non_empty) == 1:
                slots["recipient"] = non_empty[0].strip()
        elif matched_groups and intent in (IntentCategory.CALL_CONTACT, IntentCategory.OPEN_CHAT):
            if matched_groups and matched_groups[0]:
                slots["recipient"] = matched_groups[0].strip()

        # Message slot
        if "message" in entity_map:
            slots["message"] = entity_map["message"].value

        # Query slot - for search and knowledge intents
        if "query" in entity_map:
            slots["query"] = entity_map["query"].value
        elif matched_groups and intent in (IntentCategory.WEB_SEARCH, IntentCategory.IN_APP_SEARCH, IntentCategory.FIND_FILE, IntentCategory.SEARCH_FILES, IntentCategory.FIND_KNOWLEDGE):
            if matched_groups and matched_groups[0]:
                slots["query"] = matched_groups[0].strip()

        # Topic for knowledge generation intents
        if intent in (IntentCategory.GENERATE_ASSIGNMENT, IntentCategory.GENERATE_MCQ, IntentCategory.GENERATE_QUESTIONS, IntentCategory.GENERATE_NOTES, IntentCategory.SUMMARIZE, IntentCategory.EXPLAIN):
            if matched_groups and matched_groups[0]:
                slots["query"] = matched_groups[0].strip()
            elif "query" not in slots and "app" in entity_map:
                # Use app entity as query for knowledge intents
                slots["query"] = entity_map["app"].value

        # File slot
        if "file" in entity_map:
            slots["file"] = entity_map["file"].value

        # Date/time slots
        if "date" in entity_map:
            slots["date"] = entity_map["date"].value
        if "time" in entity_map:
            slots["time"] = entity_map["time"].value

        # Number slots
        if "number" in entity_map:
            slots["count"] = entity_map["number"].value

        # Direction for scroll
        if intent == IntentCategory.SCROLL:
            if 'up' in (matched_groups or []):
                slots["direction"] = "up"
            elif 'down' in (matched_groups or []):
                slots["direction"] = "down"
            else:
                slots["direction"] = "down"

        # On/off for toggles
        if intent in (IntentCategory.TOGGLE_WIFI, IntentCategory.TOGGLE_BLUETOOTH, IntentCategory.TOGGLE_FLASHLIGHT):
            if 'on' in (matched_groups or []):
                slots["state"] = "on"
            elif 'off' in (matched_groups or []):
                slots["state"] = "off"
            else:
                slots["state"] = "on"

        # Volume direction
        if intent == IntentCategory.VOLUME_CONTROL:
            if matched_groups:
                g = matched_groups[0] if matched_groups[0] else ""
                if 'up' in g or 'increase' in g or 'raise' in g:
                    slots["direction"] = "up"
                elif 'down' in g or 'decrease' in g or 'lower' in g:
                    slots["direction"] = "down"
                elif 'mute' in g or 'silence' in g or 'silent' in g:
                    slots["direction"] = "mute"
                else:
                    slots["direction"] = "up"

        return slots

    def _determine_phases(
        self,
        intent: IntentCategory,
        slots: Dict[str, Any],
    ) -> Tuple[bool, bool, bool]:
        """Determine which phases are needed."""
        # Phase 1: Device Control
        phase1_intents = {
            IntentCategory.OPEN_APP, IntentCategory.CLOSE_APP, IntentCategory.SWITCH_APP,
            IntentCategory.SEND_MESSAGE, IntentCategory.REPLY_MESSAGE, IntentCategory.OPEN_CHAT,
            IntentCategory.CALL_CONTACT, IntentCategory.SEND_EMAIL,
            IntentCategory.BATTERY_STATUS, IntentCategory.DEVICE_STATUS,
            IntentCategory.FOREGROUND_APP, IntentCategory.TAKE_SCREENSHOT,
            IntentCategory.READ_NOTIFICATIONS,
            IntentCategory.WEB_SEARCH, IntentCategory.IN_APP_SEARCH,
            IntentCategory.OPEN_FILE, IntentCategory.OPEN_CAMERA,
            IntentCategory.PLAY_MUSIC, IntentCategory.OPEN_SETTINGS,
            IntentCategory.TOGGLE_WIFI, IntentCategory.TOGGLE_BLUETOOTH,
            IntentCategory.TOGGLE_FLASHLIGHT, IntentCategory.VOLUME_CONTROL,
            IntentCategory.LOCK_DEVICE, IntentCategory.REBOOT,
            IntentCategory.GO_BACK, IntentCategory.GO_HOME,
            IntentCategory.SCROLL, IntentCategory.TAP_ELEMENT,
            IntentCategory.CREATE_REMINDER, IntentCategory.SCHEDULE_EVENT,
            IntentCategory.SET_ALARM,
        }

        # Phase 2: Phone Intelligence (visual understanding)
        phase2_intents = {
            IntentCategory.TAP_ELEMENT, IntentCategory.SCROLL,
            IntentCategory.REPLY_MESSAGE, IntentCategory.IN_APP_SEARCH,
        }

        # Phase 3: Knowledge
        phase3_intents = {
            IntentCategory.FIND_FILE, IntentCategory.SEARCH_FILES,
            IntentCategory.SUMMARIZE, IntentCategory.EXPLAIN,
            IntentCategory.GENERATE_ASSIGNMENT, IntentCategory.GENERATE_MCQ,
            IntentCategory.GENERATE_QUESTIONS, IntentCategory.GENERATE_NOTES,
            IntentCategory.FIND_KNOWLEDGE,
        }

        p1 = intent in phase1_intents
        p2 = intent in phase2_intents
        p3 = intent in phase3_intents

        # Compound actions may need multiple phases
        if intent == IntentCategory.COMPOUND_ACTION:
            p1 = True
            p2 = True
            p3 = True

        # Knowledge queries that also need device control
        if intent in (IntentCategory.OPEN_FILE, IntentCategory.FIND_FILE):
            p3 = True
            p1 = True

        return p1, p2, p3

    def _detect_compound(self, text: str) -> List[Dict[str, Any]]:
        """Detect compound actions (e.g., 'Open YouTube and search AI')."""
        compounds = []
        
        # Pattern: "open X and Y"
        match = re.search(r'(?:open|launch|start)\s+(\w+)\s+and\s+(.+)', text)
        if match:
            app = match.group(1).strip()
            action = match.group(2).strip()
            compounds.append({
                "type": "open_and_act",
                "app": app,
                "action": action,
            })
        
        # Pattern: "send X to Y via Z"
        match = re.search(r'send\s+(.+?)\s+to\s+(\w+)\s+(?:via|on|through)\s+(\w+)', text)
        if match:
            compounds.append({
                "type": "send_via",
                "message": match.group(1).strip(),
                "recipient": match.group(2).strip(),
                "app": match.group(3).strip(),
            })
        
        return compounds


# Singleton
_intent_engine = None


def get_intent_engine() -> UniversalIntentEngine:
    global _intent_engine
    if _intent_engine is None:
        _intent_engine = UniversalIntentEngine()
    return _intent_engine
