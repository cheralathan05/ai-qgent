"""
Command Understanding & NLU
Parses user commands and resolves ambiguities
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """High-level intent types"""
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SEND_MESSAGE = "send_message"
    MAKE_CALL = "call_contact"
    SEARCH = "search"
    NAVIGATE = "navigate"
    OPEN_CHAT = "open_chat"
    TAKE_SCREENSHOT = "take_screenshot"
    BATTERY_STATUS = "battery_status"
    FOREGROUND_APP = "foreground_app"
    OPEN_FOLDER = "open_folder"
    OPEN_FILE = "open_file"
    OPEN_SETTINGS = "open_settings"
    WEB_SEARCH = "web_search"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Extracted entity"""
    type: str  # app, contact, text, url, search_query
    value: str
    confidence: float
    context: Optional[Dict[str, Any]] = None


@dataclass
class IntentResult:
    """Intent extraction result"""
    intent: IntentType
    confidence: float
    entities: List[Entity]
    slots: Dict[str, str]
    raw_command: str
    normalized_command: str
    context: Optional[Dict[str, Any]] = None


KNOWN_APPS = {
    "instagram": "com.instagram.android",
    "insta": "com.instagram.android",
    "ig": "com.instagram.android",
    "whatsapp": "com.whatsapp",
    "wa": "com.whatsapp",
    "chrome": "com.android.chrome",
    "browser": "com.android.chrome",
    "youtube": "com.google.android.youtube",
    "yt": "com.google.android.youtube",
    "settings": "com.android.settings",
    "gmail": "com.google.android.gm",
    "maps": "com.google.android.apps.maps",
    "google maps": "com.google.android.apps.maps",
    "camera": "com.android.camera",
    "phone": "com.android.dialer",
    "dialer": "com.android.dialer",
    "calculator": "com.android.calculator2",
    "calendar": "com.google.android.calendar",
    "play store": "com.android.vending",
    "spotify": "com.spotify.music",
    "twitter": "com.twitter.android",
    "x": "com.twitter.android",
    "facebook": "com.facebook.katana",
    "fb": "com.facebook.katana",
    "messages": "com.google.android.apps.messaging",
    "sms": "com.google.android.apps.messaging",
    "clock": "com.google.android.deskclock",
    "files": "com.android.documentsui",
    "drive": "com.google.android.apps.docs",
    "photos": "com.google.android.apps.photos",
    "vscode": "vscode",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
}

KNOWN_CONTACTS = {
    "guru", "mom", "dad", "brother", "sister", "friend",
    "john", "jane", "alice", "bob", "cheralathan", "chera",
}


class EntityExtractor:
    """Extracts entities from user commands"""

    def __init__(self):
        self.normalizer = CommandNormalizer()
        self.intent_classifier = IntentClassifier()

    def extract_app(self, text: str) -> Optional[Entity]:
        text_lower = re.sub(r'[?.,!;:]+', '', text.lower().strip())
        for name_len in (2, 1):
            words = text_lower.split()
            for i in range(len(words) - name_len + 1):
                phrase = " ".join(words[i:i + name_len])
                if phrase in KNOWN_APPS:
                    return Entity(type="app", value=phrase, confidence=0.95)

        # Fallback: extract unknown app name after trigger phrases
        trigger_patterns = [
            r'\b(?:open|launch|start|run)\s+(\w+)',
            r'\bgo\s+to\s+(\w+)',
            r'\bswitch\s+to\s+(\w+)',
            r'\bcheck\s+(?:on\s+)?(\w+)',
        ]
        for pattern in trigger_patterns:
            m = re.search(pattern, text_lower)
            if m:
                app_name = m.group(1).strip()
                # Strip trailing noise words
                app_name = re.sub(r'\s+(?:app|application|page|screen)$', '', app_name)
                if app_name:
                    return Entity(type="app", value=app_name, confidence=0.8)
        return None

    def extract_contact(self, text: str) -> Optional[Entity]:
        text_lower = text.lower()
        for contact in KNOWN_CONTACTS:
            pattern = re.compile(r'\b' + re.escape(contact) + r'\b', re.IGNORECASE)
            if pattern.search(text_lower):
                return Entity(type="contact", value=contact, confidence=0.9)

        patterns = [
            r"(?:message|call|text|email|dm|ping)\s+(\w+)",
            r"(?:to|from)\s+(\w+)",
        ]
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                return Entity(type="contact", value=m.group(1), confidence=0.85)
        return None

    def extract_text_message(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()
        m = re.search(r'"([^"]+)"', text)
        if m:
            return Entity(type="text", value=m.group(1), confidence=0.99)
        m = re.search(r"'([^']+)'", text)
        if m:
            return Entity(type="text", value=m.group(1), confidence=0.99)

        stop_words = {"please", "now", "quickly", "urgent"}

        patterns = [
            r"(?:say|send|text|message|reply)\s+(.+?)\s+to\s+\w+",
            r"(?:tell)\s+(?:\w+\s+)?(.+?)\s+to\s+\w+",
        ]
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                val = m.group(1).strip()
                val = " ".join(w for w in val.split() if w not in stop_words)
                if val and val not in KNOWN_CONTACTS:
                    return Entity(type="text", value=val, confidence=0.85)
        return None

    def extract_url(self, text: str) -> Optional[Entity]:
        m = re.search(r"https?://[^\s]+", text)
        if m:
            return Entity(type="url", value=m.group(), confidence=0.99)
        return None

    def extract_search_query(self, text: str) -> Optional[Entity]:
        patterns = [
            r"(?:search|find|google|look up|look for)\s+([\w\s]+?)(?:\s+(?:on|in|using)\s+\w+)?$",
            r"(?:search|find|google)\s+(?:for\s+)?([\w\s]+?)(?:\s+(?:on|in|using)\s+\w+)?$",
            r"(?:go\s+to\s+\w+\s+and\s+(?:open|find|search|look)\s+)([\w\s]+)",
            r"(?:open\s+\w+\s+and\s+(?:search|find|look)\s+)([\w\s]+)",
        ]
        text_lower = text.lower().strip()
        for pat in patterns:
            m = re.search(pat, text_lower)
            if m:
                val = m.group(1).strip().rstrip(".")
                if val:
                    return Entity(type="search_query", value=val, confidence=0.9)
        return None

    def extract_all(self, text: str) -> List[Entity]:
        entities = []
        for extractor in [
            self.extract_text_message,
            self.extract_contact,
            self.extract_app,
            self.extract_url,
            self.extract_search_query,
        ]:
            entity = extractor(text)
            if entity:
                if not any(e.type == entity.type and e.value == entity.value for e in entities):
                    entities.append(entity)
        return entities

    def _fill_slots(self, intent: IntentType, entities: List[Entity]) -> Dict[str, str]:
        slots: Dict[str, str] = {}
        if intent == IntentType.OPEN_APP:
            app = next((e for e in entities if e.type == "app"), None)
            if app:
                slots["app"] = app.value
            else:
                contact = next((e for e in entities if e.type == "contact"), None)
                if contact:
                    slots["app"] = contact.value
        elif intent == IntentType.CLOSE_APP:
            app = next((e for e in entities if e.type == "app"), None)
            if app:
                slots["app"] = app.value
        elif intent == IntentType.SEND_MESSAGE:
            contact = next((e for e in entities if e.type == "contact"), None)
            text_ent = next((e for e in entities if e.type == "text"), None)
            app = next((e for e in entities if e.type == "app"), None)
            if contact:
                slots["recipient"] = contact.value
            if text_ent:
                slots["message"] = text_ent.value
            if app:
                slots["app"] = app.value
        elif intent == IntentType.MAKE_CALL:
            contact = next((e for e in entities if e.type == "contact"), None)
            if contact:
                slots["recipient"] = contact.value
        elif intent == IntentType.OPEN_CHAT:
            contact = next((e for e in entities if e.type == "contact"), None)
            app = next((e for e in entities if e.type == "app"), None)
            if contact:
                slots["recipient"] = contact.value
            if app:
                slots["app"] = app.value
            elif contact:
                slots["app"] = contact.value
        elif intent == IntentType.SEARCH:
            query = next((e for e in entities if e.type == "search_query"), None)
            app = next((e for e in entities if e.type == "app"), None)
            if query:
                slots["query"] = query.value
            if app:
                slots["app"] = app.value
        elif intent == IntentType.WEB_SEARCH:
            query = next((e for e in entities if e.type == "search_query"), None)
            if query:
                slots["query"] = query.value
        elif intent == IntentType.OPEN_FOLDER:
            slots["folder"] = "downloads"
        return slots


class IntentClassifier:
    """Classifies user intent using priority-ordered regex patterns."""

    INTENT_PATTERNS: List[Tuple[IntentType, List[str], float]] = [
        (IntentType.BATTERY_STATUS, [
            r"\bbattery\b", r"\bcharge\b", r"\bpower\s+level\b",
            r"\bhow much battery\b", r"\bbattery level\b",
            r"\bhow long will (?:the )?battery\b",
        ], 0.95),
        (IntentType.TAKE_SCREENSHOT, [
            r"\bscreenshot\b", r"\bscreen\s*capture\b", r"\bsnap\b",
            r"\bcapture\s+screen\b",
        ], 0.95),
        (IntentType.FOREGROUND_APP, [
            r"\bforeground\s+app\b", r"\bwhat'?s?\s+(?:open|running|active)\b",
            r"\bwhat\s+app\s+(?:is\s+)?(?:open|running|active)\b",
            r"\bcurrent\s+app\b",
        ], 0.9),
        (IntentType.MAKE_CALL, [
            r"\bcall\s+\w+", r"\bring\s+\w+", r"\bdial\s+\w+",
            r"\bphone\s+\w+",
        ], 0.95),
        (IntentType.SEND_MESSAGE, [
            r"\bsend\b.*\bto\b", r"\bmessage\s+\w+", r"\btext\s+\w+",
            r"\bsay\b.*\bto\b", r"\btell\b.*\bto\b",
            r"\bdm\s+\w+", r"\bwhatsapp\s+\w+",
            r"\breply\b", r"\brespond\b",
        ], 0.9),
        (IntentType.OPEN_CHAT, [
            r"\bopen\s+\w+\s+chat\b", r"\bopen\s+chat\b",
            r"\bchat\s+with\b", r"\bopen\s+(?:instagram|whatsapp)\s+(?:dm|message|chat)\b",
            r"\bgo\s+to\s+\w+\s+chat\b",
        ], 0.9),
        (IntentType.WEB_SEARCH, [
            r"\bsearch\s+(?:the\s+)?web\b", r"\bgoogle\b(?!.*\b(?:play|chrome)\b)",
            r"\bbrowse\b", r"\blook\s+up\b",
        ], 0.85),
        (IntentType.SEARCH, [
            r"\bsearch\b", r"\bfind\b", r"\blook\s+for\b",
            r"\bsearch\s+for\b",
            r"\bgo\s+to\s+\w+\s+and\s+(?:open|find|search|look)\b",
            r"\bopen\s+\w+\s+and\s+(?:search|find|look)\b",
        ], 0.85),
        (IntentType.OPEN_SETTINGS, [
            r"\bsettings\b", r"\bconfigure\b", r"\bpreferences\b",
            r"\bopen\s+settings\b", r"\blaunch\s+settings\b",
        ], 0.95),
        (IntentType.OPEN_FOLDER, [
            r"\bopen\s+(?:my\s+)?(?:downloads|documents|folder|directory)\b",
            r"\bshow\s+(?:my\s+)?(?:downloads|documents|files?)\b",
        ], 0.9),
        (IntentType.OPEN_FILE, [
            r"\bopen\s+file\b", r"\blaunch\s+file\b",
            r"\bopen\s+(?:the\s+)?\w+\.\w+\b",
        ], 0.85),
        (IntentType.CLOSE_APP, [
            r"\bclose\b", r"\bquit\b", r"\bexit\b", r"\bstop\b",
            r"\bkill\b",
        ], 0.9),
        (IntentType.OPEN_APP, [
            r"\bopen\b", r"\blaunch\b", r"\bstart\b", r"\brun\b",
            r"\bswitch\s+to\b", r"\bgo\s+to\b",
            r"\bi\s+want\s+to\s+(?:open|launch|start|check|see|use)\b",
            r"\bcan\s+(?:you|i)\s+(?:open|launch|start|run|check)\b",
            r"\bi\s+want\s+to\s+check\b",
            r"\bcheck\s+(?:on\s+)?(?:my\s+)?\w+",
            r"\bopen\s+(?:my\s+)?\w+\s+app\b",
            r"\bcould\s+you\s+(?:open|launch|start|run|check)\b",
        ], 0.85),
    ]

    def classify(self, text: str) -> Tuple[IntentType, float]:
        text_lower = text.lower().strip()
        best_intent = IntentType.UNKNOWN
        best_score = 0.0

        for intent, patterns, base_conf in self.INTENT_PATTERNS:
            score = 0.0
            for pat in patterns:
                if re.search(pat, text_lower):
                    score = max(score, base_conf)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent, best_score


class CommandNormalizer:
    """Normalizes commands to standard format."""

    REPLACEMENTS = [
        (r"\bcould you\b", ""),
        (r"\bcan you\b", ""),
        (r"\bcan i\b", ""),
        (r"\bwould you\b", ""),
        (r"\bi want to\b", ""),
        (r"\bi wanna\b", ""),
        (r"\bi need to\b", ""),
        (r"\bi'd like to\b", ""),
        (r"\bplease\b", ""),
        (r"\bhey apa\b", ""),
        (r"\bhello apa\b", ""),
        (r"\bapa\b", ""),
        (r"\bassistant\b", ""),
        (r"\bcould you please\b", ""),
        (r"\bwould you please\b", ""),
        (r"\bmy\b", ""),
        (r"\bthe\b", ""),
        (r"\ba\b", ""),
        (r"\ban\b", ""),
        (r"\b on (?:my )?(?:phone|device|laptop|computer)\b", ""),
    ]

    @staticmethod
    def normalize(text: str) -> str:
        normalized = " ".join(text.split()).lower()
        for pat, replacement in CommandNormalizer.REPLACEMENTS:
            normalized = re.sub(pat, replacement, normalized)
        normalized = " ".join(normalized.split())
        normalized = normalized.strip("?.!,;:")
        return normalized


class AmbiguityResolver:
    def __init__(self, contact_db=None, app_db=None):
        self.contact_db = contact_db
        self.app_db = app_db

    async def resolve_contact(self, partial_name: str) -> Optional[str]:
        if not self.contact_db:
            return partial_name
        matches = await self.contact_db.search_contacts(partial_name)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return matches[0]
        return partial_name

    async def resolve_app(self, partial_name: str) -> Optional[str]:
        if not self.app_db:
            return partial_name
        if partial_name in KNOWN_APPS:
            return KNOWN_APPS[partial_name]
        matches = await self.app_db.search_app(partial_name)
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return matches[0]
        return partial_name


class CommandUnderstandingEngine:
    """Complete command understanding pipeline."""

    def __init__(self, contact_db=None, app_db=None):
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.normalizer = CommandNormalizer()
        self.ambiguity_resolver = AmbiguityResolver(contact_db, app_db)

    async def understand(self, raw_command: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        normalized = self.normalizer.normalize(raw_command)
        intent, confidence = self.intent_classifier.classify(normalized)
        entities = self.entity_extractor.extract_all(normalized)
        resolved_entities = []
        for entity in entities:
            if entity.type == "contact":
                resolved_value = await self.ambiguity_resolver.resolve_contact(entity.value)
                entity.value = resolved_value
            elif entity.type == "app":
                resolved_value = await self.ambiguity_resolver.resolve_app(entity.value)
                entity.value = resolved_value
            resolved_entities.append(entity)

        slots = self._fill_slots(intent, resolved_entities)

        logger.info(
            f"Understood command: intent={intent.value}, "
            f"confidence={confidence}, entities={len(resolved_entities)}, slots={slots}"
        )

        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=resolved_entities,
            slots=slots,
            raw_command=raw_command,
            normalized_command=normalized,
            context=context,
        )

    def _fill_slots(self, intent: IntentType, entities: List[Entity]) -> Dict[str, str]:
        return self.entity_extractor._fill_slots(intent, entities)


command_engine = None


def get_command_understanding_engine(contact_db=None, app_db=None) -> CommandUnderstandingEngine:
    global command_engine
    if command_engine is None:
        command_engine = CommandUnderstandingEngine(contact_db, app_db)
    return command_engine
