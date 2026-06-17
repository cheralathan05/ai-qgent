"""
Command Understanding & NLU
Parses user commands and resolves ambiguities
"""

import logging
import asyncio
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
    MAKE_CALL = "make_call"
    SEARCH = "search"
    NAVIGATE = "navigate"
    OPEN_DEVICE = "open_device"
    UNLOCK_DEVICE = "unlock_device"
    GET_INFO = "get_info"
    SETTINGS = "settings"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Extracted entity"""
    type: str  # app, contact, text, url, etc.
    value: str
    confidence: float
    context: Optional[Dict[str, Any]] = None


@dataclass
class IntentResult:
    """Intent extraction result"""
    intent: IntentType
    confidence: float
    entities: List[Entity]
    slots: Dict[str, str]  # Filled slots
    raw_command: str
    normalized_command: str


class EntityExtractor:
    """Extracts entities from user commands"""

    def __init__(self):
        self.normalizer = CommandNormalizer()
    
    # Common app name variations
    APP_ALIASES = {
        "insta": "instagram",
        "ig": "instagram",
        "fb": "facebook",
        "whatsapp": "whatsapp",
        "wa": "whatsapp",
        "gmail": "gmail",
        "gm": "gmail",
        "maps": "google_maps",
        "music": "spotify",
        "youtube": "youtube",
        "yt": "youtube",
        "twitter": "twitter",
        "x": "twitter",
        "chrome": "chrome",
        "browser": "chrome",
        "settings": "android_settings",
    }
    
    # Common contact patterns
    CONTACT_PATTERNS = [
        r"(?:message|call|text|email|dm)\s+(\w+)",
        r"(?:to|from)\s+(\w+)",
        r"(?:guru|mom|dad|friend|brother|sister|john|jane)\b",
    ]
    
    def extract_app(self, text: str) -> Optional[Entity]:
        """Extract app name from text"""
        text_lower = text.lower()
        
        # Check aliases first
        for alias, real_name in self.APP_ALIASES.items():
            if alias in text_lower:
                return Entity(
                    type="app",
                    value=real_name,
                    confidence=0.95,
                    context={"alias": alias}
                )
        
        # Check full package names
        package_pattern = r"com\.[\w\.]+"
        match = re.search(package_pattern, text)
        if match:
            return Entity(
                type="app",
                value=match.group(),
                confidence=0.98,
                context={"package": match.group()}
            )
        
        return None
    
    def extract_contact(self, text: str) -> Optional[Entity]:
        """Extract contact name"""
        text_lower = text.lower()
        
        for pattern in self.CONTACT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                contact = match.group(1) if match.lastindex else match.group()
                return Entity(
                    type="contact",
                    value=contact,
                    confidence=0.85,
                    context={"pattern": pattern}
                )
        
        return None
    
    def extract_text(self, text: str, delimiter: str = "\"") -> Optional[Entity]:
        """Extract text message content"""
        pattern = f'{delimiter}([^{delimiter}]+){delimiter}'
        match = re.search(pattern, text)
        if match:
            return Entity(
                type="text",
                value=match.group(1),
                confidence=0.99,
            )
        
        return None
    
    def extract_url(self, text: str) -> Optional[Entity]:
        """Extract URL"""
        url_pattern = r"https?://[^\s]+"
        match = re.search(url_pattern, text)
        if match:
            return Entity(
                type="url",
                value=match.group(),
                confidence=0.99,
            )
        
        return None
    
    def extract_all(self, text: str) -> List[Entity]:
        """Extract all entities"""
        entities = []
        
        for extractor in [
            self.extract_app,
            self.extract_contact,
            self.extract_text,
            self.extract_url,
        ]:
            entity = extractor(text)
            if entity:
                entities.append(entity)
        
        return entities

    def _fill_slots(self, intent: IntentType, entities: List[Entity]) -> Dict[str, str]:
        """Fill intent slots from extracted entities."""
        slots: Dict[str, str] = {}

        if intent == IntentType.OPEN_APP:
            app = next((entity for entity in entities if entity.type == "app"), None)
            if app:
                slots["app"] = app.value

        elif intent == IntentType.SEND_MESSAGE:
            contact = next((entity for entity in entities if entity.type == "contact"), None)
            text = next((entity for entity in entities if entity.type == "text"), None)
            if contact:
                slots["recipient"] = contact.value
            if text:
                slots["message"] = text.value

        elif intent == IntentType.MAKE_CALL:
            contact = next((entity for entity in entities if entity.type == "contact"), None)
            if contact:
                slots["recipient"] = contact.value

        return slots


class IntentClassifier:
    """Classifies user intent"""
    
    INTENT_KEYWORDS = {
        IntentType.OPEN_APP: ["open", "launch", "start", "run"],
        IntentType.CLOSE_APP: ["close", "quit", "exit", "stop"],
        IntentType.SEND_MESSAGE: ["message", "text", "send", "dm", "email"],
        IntentType.MAKE_CALL: ["call", "ring", "dial"],
        IntentType.SEARCH: ["search", "find", "look", "google"],
        IntentType.NAVIGATE: ["go", "navigate", "open"],
        IntentType.OPEN_DEVICE: ["open", "turn on"],
        IntentType.UNLOCK_DEVICE: ["unlock", "open"],
        IntentType.GET_INFO: ["show", "tell", "what", "how"],
        IntentType.SETTINGS: ["settings", "config", "set"],
    }
    
    def classify(self, text: str) -> Tuple[IntentType, float]:
        """
        Classify intent from text
        
        Args:
            text: User input
            
        Returns:
            (IntentType, confidence)
        """
        text_lower = text.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            if score > 0:
                scores[intent] = score
        
        if not scores:
            return IntentType.UNKNOWN, 0.0
        
        # Get highest score
        intent = max(scores, key=scores.get)
        confidence = min(scores[intent] / len(text.split()), 1.0)
        
        return intent, confidence


class CommandNormalizer:
    """Normalizes commands to standard format"""
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize command text
        
        Args:
            text: Raw user input
            
        Returns:
            Normalized command
        """
        # Remove extra whitespace
        normalized = " ".join(text.split())
        
        # Convert to lowercase for processing
        normalized = normalized.lower()
        
        # Remove common filler words
        fillers = ["please", "can you", "could you", "would you", "can i"]
        for filler in fillers:
            normalized = normalized.replace(filler, "")
        
        # Clean up whitespace again
        normalized = " ".join(normalized.split())
        
        return normalized


class AmbiguityResolver:
    """Resolves ambiguous commands"""
    
    def __init__(self, contact_db=None, app_db=None):
        """
        Initialize resolver with optional databases
        
        Args:
            contact_db: Contact database for name resolution
            app_db: App database for app name resolution
        """
        self.contact_db = contact_db
        self.app_db = app_db
    
    async def resolve_contact(self, partial_name: str) -> Optional[str]:
        """
        Resolve partial contact name to full contact
        
        Args:
            partial_name: Partial or ambiguous contact name
            
        Returns:
            Full contact name
        """
        if not self.contact_db:
            return partial_name
        
        # Find matching contacts
        matches = await self.contact_db.search_contacts(partial_name)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return most recent
            return matches[0]
        
        return partial_name
    
    async def resolve_app(self, partial_name: str) -> Optional[str]:
        """
        Resolve partial app name to full package name
        
        Args:
            partial_name: Partial or aliased app name
            
        Returns:
            Full package name
        """
        if not self.app_db:
            return partial_name
        
        # Try aliases
        matches = await self.app_db.search_app(partial_name)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return most popular
            return matches[0]
        
        return partial_name


class CommandUnderstandingEngine:
    """Complete command understanding pipeline"""
    
    def __init__(self, contact_db=None, app_db=None):
        self.entity_extractor = EntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.normalizer = CommandNormalizer()
        self.ambiguity_resolver = AmbiguityResolver(contact_db, app_db)
    
    async def understand(self, raw_command: str) -> IntentResult:
        """
        Understand user command
        
        Args:
            raw_command: Raw user input
            
        Returns:
            IntentResult with parsed intent and entities
        """
        # Normalize command
        normalized = self.normalizer.normalize(raw_command)
        
        # Classify intent
        intent, confidence = self.intent_classifier.classify(normalized)
        
        # Extract entities
        entities = self.entity_extractor.extract_all(normalized)
        
        # Resolve ambiguities
        resolved_entities = []
        for entity in entities:
            if entity.type == "contact":
                resolved_value = await self.ambiguity_resolver.resolve_contact(entity.value)
                entity.value = resolved_value
            elif entity.type == "app":
                resolved_value = await self.ambiguity_resolver.resolve_app(entity.value)
                entity.value = resolved_value
            
            resolved_entities.append(entity)
        
        # Fill slots
        slots = self._fill_slots(intent, resolved_entities)
        
        logger.info(
            f"Understood command: intent={intent.value}, "
            f"confidence={confidence}, entities={len(resolved_entities)}"
        )
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=resolved_entities,
            slots=slots,
            raw_command=raw_command,
            normalized_command=normalized,
        )
    
    def _fill_slots(self, intent: IntentType, entities: List[Entity]) -> Dict[str, str]:
        """Fill intent slots from entities"""
        slots = {}
        
        if intent == IntentType.OPEN_APP:
            app = next((e for e in entities if e.type == "app"), None)
            if app:
                slots["app"] = app.value
        
        elif intent == IntentType.SEND_MESSAGE:
            contact = next((e for e in entities if e.type == "contact"), None)
            text = next((e for e in entities if e.type == "text"), None)
            if contact:
                slots["recipient"] = contact.value
            if text:
                slots["message"] = text.value
        
        elif intent == IntentType.MAKE_CALL:
            contact = next((e for e in entities if e.type == "contact"), None)
            if contact:
                slots["recipient"] = contact.value
        
        return slots


# Global instance
command_engine = None


def get_command_understanding_engine(contact_db=None, app_db=None) -> CommandUnderstandingEngine:
    """Get or create command understanding engine"""
    global command_engine
    if command_engine is None:
        command_engine = CommandUnderstandingEngine(contact_db, app_db)
    return command_engine
