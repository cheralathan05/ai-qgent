"""
Command Understanding & NLU
Parses user commands and resolves ambiguities
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime, timedelta

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
    SEND_EMAIL = "send_email"
    SCHEDULE_EVENT = "schedule_event"
    REMINDER = "reminder"
    PLAY_MUSIC = "play_music"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    WIFI_ON = "wifi_on"
    WIFI_OFF = "wifi_off"
    BLUETOOTH_ON = "bluetooth_on"
    BLUETOOTH_OFF = "bluetooth_off"
    FLASH_ON = "flash_on"
    FLASH_OFF = "flash_off"
    SCREENSHOT = "screenshot"
    REBOOT = "reboot"
    LOCK_DEVICE = "lock_device"
    OPEN_CAMERA = "open_camera"
    READ_NOTIFICATIONS = "read_notifications"
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
    "telegram": "org.telegram.messenger",
    "discord": "com.discord",
    "linkedin": "com.linkedin.android",
    "messenger": "com.facebook.orca",
    "snapchat": "com.snapchat.android",
}

KNOWN_CONTACTS = {
    "guru", "mom", "dad", "brother", "sister", "friend",
    "john", "jane", "alice", "bob", "cheralathan", "chera",
    "alex", "sarah", "mike", "emma", "david", "lisa",
    "james", "mary", "robert", "patricia", "tom", "jerry",
    "sam", "chris", "ashley", "jessica", "daniel", "amanda",
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
            r"(?:tell|ask|notify)\s+(\w+)",
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

        stop_words = {"please", "now", "quickly", "urgent", "asap"}

        patterns = [
            r"(?:say|send|text|message|reply)\s+(.+?)\s+to\s+\w+",
            r"(?:tell)\s+(?:\w+\s+)?(.+?)\s+to\s+\w+",
            r"(?:say|speak)\s+(.+?)$",
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

    def extract_date(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()

        today = datetime.now()
        day_names = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                     "friday": 4, "saturday": 5, "sunday": 6}

        date_patterns = [
            (r'\btoday\b', today.strftime("%Y-%m-%d"), 0.99),
            (r'\bnow\b', today.strftime("%Y-%m-%d"), 0.99),
            (r'\btonight\b', today.strftime("%Y-%m-%d"), 0.95),
            (r'\btomorrow\b', (today + timedelta(days=1)).strftime("%Y-%m-%d"), 0.99),
            (r'\bday after tomorrow\b', (today + timedelta(days=2)).strftime("%Y-%m-%d"), 0.95),
            (r'\bnext\s+week\b', (today + timedelta(weeks=1)).strftime("%Y-%m-%d"), 0.9),
            (r'\bnext\s+month\b', (today + timedelta(days=30)).strftime("%Y-%m-%d"), 0.85),
        ]
        for pattern, date_val, conf in date_patterns:
            if re.search(pattern, text_lower):
                return Entity(type="date", value=date_val, confidence=conf)

        for day_name, day_idx in day_names.items():
            m = re.search(r'\bnext\s+' + day_name + r'\b', text_lower)
            if m:
                days_ahead = (day_idx - today.weekday()) % 7
                if days_ahead <= 0:
                    days_ahead += 7
                result = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                return Entity(type="date", value=result, confidence=0.95)

            m = re.search(r'\bthis\s+(?:coming\s+)?' + day_name + r'\b', text_lower)
            if m:
                days_ahead = (day_idx - today.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                result = (today + timedelta(days=days_ahead - 7)).strftime("%Y-%m-%d")
                if days_ahead > 0:
                    result = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                return Entity(type="date", value=result, confidence=0.9)

            m = re.search(r'\b' + day_name + r'\b', text_lower)
            if m:
                days_ahead = (day_idx - today.weekday()) % 7
                if days_ahead == 0:
                    result = today.strftime("%Y-%m-%d")
                else:
                    result = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                return Entity(type="date", value=result, confidence=0.85)

        # ISO dates: 2024-03-15, 2024/03/15
        m = re.search(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b', text)
        if m:
            return Entity(type="date", value=m.group(1).replace("/", "-"), confidence=0.99)

        # US dates: March 15, 2024 or Mar 15, 2024
        m = re.search(r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})\b', text, re.IGNORECASE)
        if m:
            month_names = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                          "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
            month_abbr = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                         "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
            raw_month = re.search(r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b', text, re.IGNORECASE).group(1).lower()[:3]
            month_num = month_abbr.get(raw_month, 1)
            day = int(m.group(1))
            year = int(m.group(2))
            try:
                result = f"{year:04d}-{month_num:02d}-{day:02d}"
                return Entity(type="date", value=result, confidence=0.99)
            except Exception:
                pass

        # Month day (no year): March 15
        m = re.search(r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b', text, re.IGNORECASE)
        if m:
            month_abbr = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                         "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
            raw_month = re.search(r'\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b', text, re.IGNORECASE).group(1).lower()[:3]
            month_num = month_abbr.get(raw_month, 1)
            day = int(m.group(1))
            year = today.year
            try:
                result = f"{year:04d}-{month_num:02d}-{day:02d}"
                return Entity(type="date", value=result, confidence=0.95)
            except Exception:
                pass

        # DD/MM/YYYY or MM/DD/YYYY
        m = re.search(r'\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b', text)
        if m:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if year < 100:
                year += 2000
            try:
                result = f"{year:04d}-{month:02d}-{day:02d}"
                return Entity(type="date", value=result, confidence=0.95)
            except Exception:
                pass

        return None

    def extract_time(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()

        # 12-hour with am/pm: 3pm, 3:30pm, 3:30 pm
        m = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', text_lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            ampm = m.group(3).lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                result = f"{hour:02d}:{minute:02d}"
                return Entity(type="time", value=result, confidence=0.99)

        # 24-hour: 15:30, 09:15
        m = re.search(r'\b(\d{2}):(\d{2})\b', text)
        if m:
            hour, minute = int(m.group(1)), int(m.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                result = f"{hour:02d}:{minute:02d}"
                return Entity(type="time", value=result, confidence=0.99)

        # Named times
        time_keywords = [
            (r'\bmorning\b', "08:00", 0.85),
            (r'\bnoon\b', "12:00", 0.95),
            (r'\bafternoon\b', "14:00", 0.85),
            (r'\bevening\b', "18:00", 0.85),
            (r'\bnight\b', "20:00", 0.85),
            (r'\bmidnight\b', "00:00", 0.95),
            (r'\bdawn\b', "06:00", 0.85),
            (r'\bdusk\b', "19:00", 0.85),
            (r'\bsunrise\b', "06:30", 0.8),
            (r'\bsunset\b', "18:30", 0.8),
        ]
        for pattern, time_val, conf in time_keywords:
            if re.search(pattern, text_lower):
                return Entity(type="time", value=time_val, confidence=conf)

        # "at 5" or "at 5 o'clock"
        m = re.search(r'\bat\s+(\d{1,2})\s*(?::00)?\s*(?:o\s*clock)?\b', text_lower)
        if m:
            hour = int(m.group(1))
            if 1 <= hour <= 12:
                result = f"{hour:02d}:00"
                return Entity(type="time", value=result, confidence=0.8)

        return None

    def extract_location(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()

        location_keywords = {
            "home", "work", "office", "school", "gym", "store", "market",
            "airport", "station", "hospital", "library", "park", "bank",
            "restaurant", "cafe", "cinema", "theater", "mall", "church",
            "temple", "mosque", "pharmacy", "clinic", "hotel", "garage",
        }

        words = text_lower.split()
        for word in words:
            word_clean = re.sub(r'[?.,!;:]+', '', word)
            if word_clean in location_keywords:
                return Entity(type="location", value=word_clean, confidence=0.9)

        # "in/at/to/from <location>" patterns
        location_triggers = [
            r'(?:go|come|head|drive|walk|travel|navigate|move)\s+(?:to|towards?)\s+([\w\s]+?)(?:\s+(?:please|now|quickly|asap))?$',
            r'(?:at|in|to|from|near|around)\s+(?:the\s+)?(\w+(?:\s+\w+)?)(?:\s+(?:please|now|quickly|asap))?$',
            r'(?:where\s+is|find|locate)\s+(?:the\s+)?(\w+(?:\s+\w+)?)',
        ]
        for pat in location_triggers:
            m = re.search(pat, text_lower)
            if m:
                loc = m.group(1).strip()
                if loc and not any(kw in loc for kw in ["please", "now", "quickly", "asap", "the"]):
                    return Entity(type="location", value=loc, confidence=0.8)

        return None

    def extract_command_type(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()

        command_patterns = [
            (r'\b(?:run|execute)\s+(?:command\s+)?`([^`]+)`', "shell", 0.99),
            (r'\b(?:run|execute)\s+(?:command\s+)?["\']([^"\']+)["\']', "shell", 0.95),
            (r'\brun\s+(?:a\s+)?(?:command|script|program|executable)\b', "shell", 0.9),
            (r'\bexecute\s+(?:a\s+)?(?:command|script)\b', "shell", 0.9),
            (r'\b(?:list|show)\s+files\b', "filesystem", 0.85),
            (r'\b(?:list|show)\s+directory\b', "filesystem", 0.85),
            (r'\b(?:list|show)\s+process(?:es)?\b', "system", 0.85),
            (r'\b(?:check|show)\s+(?:disk|memory|cpu|storage)\s+(?:usage|status|space)\b', "system", 0.85),
            (r'\b(?:install|uninstall|remove)\s+(?:package|app|program|software)\b', "package", 0.9),
            (r'\b(?:create|delete|remove|copy|move|rename)\s+(?:file|folder|directory)\b', "filesystem", 0.85),
            (r'\b(?:shutdown|poweroff|halt)\b', "system", 0.95),
            (r'\brestart|reboot\b', "system", 0.95),
            (r'\bopen\s+(?:terminal|cmd|command\s+prompt|console|shell)\b', "shell", 0.95),
            (r'\b(?:switch|turn)\s+(?:on|off)\s+(?:wifi|bluetooth|flashlight|flash)\b', "toggle", 0.9),
            (r'\bincrease|decrease\s+volume\b', "control", 0.9),
            (r'\b(?:take|capture)\s+screenshot\b', "system", 0.95),
            (r'\block\s+(?:the\s+)?(?:phone|device|screen)\b', "system", 0.95),
        ]

        for pattern, cmd_type, conf in command_patterns:
            m = re.search(pattern, text_lower)
            if m:
                return Entity(type="command", value=cmd_type, confidence=conf)

        return None

    def extract_number(self, text: str) -> Optional[Entity]:
        m = re.search(r'\b(\d+)\b', text)
        if m:
            return Entity(type="number", value=m.group(1), confidence=0.99)

        number_words = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
            "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
            "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
            "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
            "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
            "eighty": "80", "ninety": "90", "hundred": "100", "thousand": "1000",
        }
        text_lower = text.lower().strip()
        for word, num in number_words.items():
            if re.search(r'\b' + word + r'\b', text_lower):
                return Entity(type="number", value=num, confidence=0.9)

        return None

    def extract_email(self, text: str) -> Optional[Entity]:
        m = re.search(r'[\w.%-]+@[\w.-]+\.[a-zA-Z]{2,}', text)
        if m:
            return Entity(type="email", value=m.group(), confidence=0.99)
        return None

    def extract_phone(self, text: str) -> Optional[Entity]:
        text_clean = re.sub(r'[()\-\s.]+', '', text)

        patterns = [
            r'\b\d{10}\b',
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\+?\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                digits = re.sub(r'[^\d]', '', m.group())
                if len(digits) >= 10:
                    return Entity(type="phone", value=digits, confidence=0.99)

        # contextual: "call 123-456-7890"
        m = re.search(r'(?:call|dial|phone|text|message|sms)\s+(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', text, re.IGNORECASE)
        if m:
            digits = re.sub(r'[^\d]', '', m.group(1))
            return Entity(type="phone", value=digits, confidence=0.95)

        return None

    def extract_duration(self, text: str) -> Optional[Entity]:
        text_lower = text.lower().strip()

        patterns = [
            (r'\b(\d+)\s*(?:min|mins|minutes?)\b', 1, 0.99),
            (r'\b(\d+)\s*(?:hr|hrs|hours?)\b', 60, 0.99),
            (r'\b(\d+)\s*(?:sec|secs|seconds?)\b', 1/60, 0.99),
            (r'\b(\d+)\s*(?:day|days?)\b', 1440, 0.95),
            (r'\b(\d+)\s*(?:week|weeks?)\b', 10080, 0.95),
            (r'\b(?:half|half an|half a)\s*hour\b', 30, 0.95),
            (r'\b(?:quarter|quarter of an?)\s*hour\b', 15, 0.9),
        ]

        for pattern, multiplier, conf in patterns:
            m = re.search(pattern, text_lower)
            if m:
                if m.group(1):
                    minutes = int(m.group(1)) * multiplier
                else:
                    minutes = multiplier
                return Entity(type="duration", value=str(minutes), confidence=conf)

        # "an hour", "a minute"
        word_durations = [
            (r'\ban?\s+hour\b', 60, 0.95),
            (r'\ban?\s+minute\b', 1, 0.95),
            (r'\ba\s+second\b', 1/60, 0.9),
            (r'\ban?\s+day\b', 1440, 0.9),
            (r'\ba\s+week\b', 10080, 0.9),
        ]
        for pattern, minutes, conf in word_durations:
            if re.search(pattern, text_lower):
                return Entity(type="duration", value=str(minutes), confidence=conf)

        return None

    def extract_all(self, text: str) -> List[Entity]:
        entities = []
        for extractor in [
            self.extract_text_message,
            self.extract_contact,
            self.extract_app,
            self.extract_url,
            self.extract_search_query,
            self.extract_date,
            self.extract_time,
            self.extract_location,
            self.extract_command_type,
            self.extract_number,
            self.extract_email,
            self.extract_phone,
            self.extract_duration,
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
            phone = next((e for e in entities if e.type == "phone"), None)
            if contact:
                slots["recipient"] = contact.value
            elif phone:
                slots["recipient"] = phone.value
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
        elif intent == IntentType.SEND_EMAIL:
            contact = next((e for e in entities if e.type == "contact"), None)
            email = next((e for e in entities if e.type == "email"), None)
            text_ent = next((e for e in entities if e.type == "text"), None)
            subject_ent = next((e for e in entities if e.type == "subject"), None)
            if contact:
                slots["recipient"] = contact.value
            elif email:
                slots["recipient"] = email.value
            if text_ent:
                slots["body"] = text_ent.value
            if subject_ent:
                slots["subject"] = subject_ent.value
        elif intent == IntentType.SCHEDULE_EVENT:
            date_ent = next((e for e in entities if e.type == "date"), None)
            time_ent = next((e for e in entities if e.type == "time"), None)
            text_ent = next((e for e in entities if e.type == "text"), None)
            duration_ent = next((e for e in entities if e.type == "duration"), None)
            if date_ent:
                slots["date"] = date_ent.value
            if time_ent:
                slots["time"] = time_ent.value
            if text_ent:
                slots["title"] = text_ent.value
            if duration_ent:
                slots["duration_minutes"] = duration_ent.value
        elif intent == IntentType.REMINDER:
            text_ent = next((e for e in entities if e.type == "text"), None)
            date_ent = next((e for e in entities if e.type == "date"), None)
            time_ent = next((e for e in entities if e.type == "time"), None)
            if text_ent:
                slots["message"] = text_ent.value
            if date_ent:
                slots["date"] = date_ent.value
            if time_ent:
                slots["time"] = time_ent.value
        elif intent == IntentType.PLAY_MUSIC:
            text_ent = next((e for e in entities if e.type == "text"), None)
            app = next((e for e in entities if e.type == "app"), None)
            if text_ent:
                slots["query"] = text_ent.value
            if app:
                slots["app"] = app.value
        elif intent == IntentType.VOLUME_UP:
            number_ent = next((e for e in entities if e.type == "number"), None)
            slots["level"] = number_ent.value if number_ent else "10"
        elif intent == IntentType.VOLUME_DOWN:
            number_ent = next((e for e in entities if e.type == "number"), None)
            slots["level"] = number_ent.value if number_ent else "10"
        elif intent == IntentType.WIFI_ON:
            slots["state"] = "on"
        elif intent == IntentType.WIFI_OFF:
            slots["state"] = "off"
        elif intent == IntentType.BLUETOOTH_ON:
            slots["state"] = "on"
        elif intent == IntentType.BLUETOOTH_OFF:
            slots["state"] = "off"
        elif intent == IntentType.FLASH_ON:
            slots["state"] = "on"
        elif intent == IntentType.FLASH_OFF:
            slots["state"] = "off"
        elif intent in (IntentType.TAKE_SCREENSHOT, IntentType.SCREENSHOT):
            pass
        elif intent == IntentType.REBOOT:
            pass
        elif intent == IntentType.LOCK_DEVICE:
            pass
        elif intent == IntentType.OPEN_CAMERA:
            slots["app"] = "camera"
        elif intent == IntentType.READ_NOTIFICATIONS:
            pass
        elif intent == IntentType.OPEN_SETTINGS:
            text_ent = next((e for e in entities if e.type == "text"), None)
            if text_ent:
                slots["section"] = text_ent.value
        return slots


class IntentClassifier:
    """Classifies user intent using priority-ordered regex patterns."""

    INTENT_PATTERNS: List[Tuple[IntentType, List[str], float]] = [
        (IntentType.BATTERY_STATUS, [
            r"\bbattery\b", r"\bcharge\b", r"\bpower\s+level\b",
            r"\bhow much battery\b", r"\bbattery level\b",
            r"\bhow long will (?:the )?battery\b",
        ], 0.95),
        (IntentType.VOLUME_UP, [
            r"\bvolume\s*up\b", r"\bincrease\s+volume\b", r"\blouder\b",
            r"\bturn\s+up\b(?=.*volume)", r"\braise\s+volume\b",
            r"\bmax\s+volume\b", r"\b(maximize|increase)\s+(?:the\s+)?volume\b",
        ], 0.95),
        (IntentType.VOLUME_DOWN, [
            r"\bvolume\s*down\b", r"\bdecrease\s+volume\b", r"\bquieter\b",
            r"\bturn\s+down\b(?=.*volume)", r"\blower\s+volume\b",
            r"\bmute\b", r"\bsilent\b", r"\bsilence\b",
        ], 0.95),
        (IntentType.WIFI_ON, [
            r"\bturn\s+on\s+wifi\b", r"\benable\s+wifi\b", r"\bwifi\s+on\b",
            r"\bswitch\s+on\s+wifi\b", r"\bactivate\s+wifi\b",
            r"\bconnect\s+to\s+wifi\b",
        ], 0.95),
        (IntentType.WIFI_OFF, [
            r"\bturn\s+off\s+wifi\b", r"\bdisable\s+wifi\b", r"\bwifi\s+off\b",
            r"\bswitch\s+off\s+wifi\b", r"\bdeactivate\s+wifi\b",
            r"\bdisconnect\s+wifi\b",
        ], 0.95),
        (IntentType.BLUETOOTH_ON, [
            r"\bturn\s+on\s+bluetooth\b", r"\benable\s+bluetooth\b",
            r"\bbluetooth\s+on\b", r"\bswitch\s+on\s+bluetooth\b",
            r"\bactivate\s+bluetooth\b", r"\bconnect\s+bluetooth\b",
        ], 0.95),
        (IntentType.BLUETOOTH_OFF, [
            r"\bturn\s+off\s+bluetooth\b", r"\bdisable\s+bluetooth\b",
            r"\bbluetooth\s+off\b", r"\bswitch\s+off\s+bluetooth\b",
            r"\bdeactivate\s+bluetooth\b",
        ], 0.95),
        (IntentType.FLASH_ON, [
            r"\bturn\s+on\s+(?:flashlight|flash)\b", r"\benable\s+(?:flashlight|flash)\b",
            r"\bflashlight\s+on\b", r"\bflash\s+on\b",
            r"\bswitch\s+on\s+(?:flashlight|flash)\b",
            r"\bactivate\s+(?:flashlight|flash)\b",
        ], 0.95),
        (IntentType.FLASH_OFF, [
            r"\bturn\s+off\s+(?:flashlight|flash)\b", r"\bdisable\s+(?:flashlight|flash)\b",
            r"\bflashlight\s+off\b", r"\bflash\s+off\b",
            r"\bswitch\s+off\s+(?:flashlight|flash)\b",
            r"\bdeactivate\s+(?:flashlight|flash)\b",
        ], 0.95),
        (IntentType.TAKE_SCREENSHOT, [
            r"\bscreenshot\b", r"\bscreen\s*capture\b", r"\bsnap\b",
            r"\bcapture\s+screen\b",
        ], 0.95),
        (IntentType.SCREENSHOT, [
            r"\btake\s+a\s+screenshot\b", r"\bcapture\s+screenshot\b",
            r"\bgrab\s+(?:a\s+)?screenshot\b",
        ], 0.95),
        (IntentType.REBOOT, [
            r"\breboot\b", r"\brestart\b", r"\breset\b",
            r"\bturn\s+(?:the\s+)?(?:phone|device)\s+off\s+and\s+on\b",
            r"\bpower\s+cycle\b",
        ], 0.95),
        (IntentType.LOCK_DEVICE, [
            r"\block\s+(?:the\s+)?(?:phone|device|screen)\b",
            r"\block\s+device\b", r"\block\s+screen\b",
            r"\block\s+phone\b",
        ], 0.95),
        (IntentType.READ_NOTIFICATIONS, [
            r"\b(?:read|check|show|get)\s+(?:my\s+)?notifications?\b",
            r"\bwhat'?s?\s+(?:new|notified)\b",
            r"\b(?:read|check)\s+(?:the\s+)?notification\s+(?:bar|panel|center|tray)\b",
            r"\bnotification\s+(?:status|list)\b",
            r"\bshow\s+(?:me\s+)?(?:my\s+)?(?:recent\s+)?alerts?\b",
        ], 0.9),
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
        (IntentType.SEND_EMAIL, [
            r"\b(?:send|compose|draft|write)\s+(?:an?\s+)?email\b",
            r"\bemail\s+\w+", r"\bmail\s+\w+",
            r"\bsend\s+(?:an?\s+)?(?:email|mail)\s+to\b",
            r"\bcompose\s+(?:an?\s+)?(?:email|mail)\b",
            r"\bgmail\s+\w+",
        ], 0.95),
        (IntentType.SCHEDULE_EVENT, [
            r"\b(?:schedule|create|add|make|set\s+up)\s+(?:an?\s+)?(?:event|meeting|appointment)\b",
            r"\b(?:schedule|create|add|make|set)\s+(?:a\s+)?(?:calendar\s+)?event\b",
            r"\badd\s+to\s+(?:my\s+)?calendar\b",
            r"\bplan\s+(?:a|an)\s+(?:meeting|event|appointment)\b",
            r"\b(?:fix|set|book)\s+(?:a|an)\s+appointment\b",
        ], 0.9),
        (IntentType.REMINDER, [
            r"\b(?:set|create|add|make)\s+(?:a\s+|an?\s+)?reminder\b",
            r"\bremind\s+(?:me|us)\b", r"\breminder\s+to\b",
            r"\bdon'?t\s+let\s+me\s+forget\b",
            r"\b(?:set|create|add)\s+(?:a\s+|an?\s+)?(?:timer|alarm)\b",
        ], 0.9),
        (IntentType.PLAY_MUSIC, [
            r"\bplay\s+(?:some|my|a)?\s*(?:song|music|track|audio|playlist)\b",
            r"\bplay\s+\w+(?:\s+\w+)?\s+(?:by|from)\b",
            r"\bmusic\b", r"\bsong\b",
            r"\b(?:shuffle|skip|pause|resume)\s+(?:the\s+)?music\b",
            r"\b(?:start|play)\s+(?:a\s+)?playlist\b",
            r"\bplay\s+(?:me\s+)?(?:some\s+)?music\b",
            r"\bi\s+want\s+to\s+listen\s+to\b",
        ], 0.85),
        (IntentType.OPEN_CAMERA, [
            r"\bopen\s+(?:the\s+)?(?:camera|photo|video)\s+(?:app|mode)?\b",
            r"\blaunch\s+(?:the\s+)?camera\b",
            r"\bshoot\s+(?:a\s+)?(?:photo|picture|video)\b",
            r"\btake\s+(?:a\s+)?(?:photo|picture|selfie|snap)\b",
            r"\bopen\s+camera\b",
        ], 0.95),
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
