"""Contact resolution service for APA-OS."""

import re
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Contact:
    name: str
    display_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    username: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "phone": self.phone,
            "email": self.email,
            "username": self.username,
        }


BUILTIN_CONTACTS: Dict[str, Contact] = {
    "guru": Contact(
        name="guru",
        display_name="Guru",
        phone="+1234567890",
        username={"whatsapp": "guru", "instagram": "guru_insta"},
    ),
    "mom": Contact(
        name="mom",
        display_name="Mom",
        phone="+1987654321",
    ),
    "dad": Contact(
        name="dad",
        display_name="Dad",
        phone="+1567890123",
    ),
    "alex": Contact(
        name="alex",
        display_name="Alex",
        phone="+1122334455",
        username={"whatsapp": "alex_wa"},
    ),
    "sarah": Contact(
        name="sarah",
        display_name="Sarah",
        phone="+1555666777",
        username={"instagram": "sarah_gram"},
    ),
}


class ContactStore:
    def __init__(self):
        self._contacts: Dict[str, Contact] = {}
        for name, contact in BUILTIN_CONTACTS.items():
            self._contacts[name.lower()] = contact

    def resolve(self, name: str) -> Optional[Contact]:
        if not name:
            return None
        key = name.strip().lower()
        if key in self._contacts:
            return self._contacts[key]
        for c in self._contacts.values():
            if c.display_name.lower() == key:
                return c
            if c.phone and re.sub(r"\D", "", c.phone) == re.sub(r"\D", "", key):
                return c
            for platform_uname in c.username.values():
                if platform_uname.lower() == key:
                    return c
        return None

    def get_all(self) -> List[Contact]:
        return list(self._contacts.values())

    def add(self, name: str, display_name: str, phone: Optional[str] = None, email: Optional[str] = None) -> Contact:
        contact = Contact(name=name.lower(), display_name=display_name, phone=phone, email=email)
        self._contacts[name.lower()] = contact
        logger.info(f"Added contact: {display_name} ({phone})")
        return contact

    def get_phone(self, name: str) -> Optional[str]:
        contact = self.resolve(name)
        return contact.phone if contact else None

    def get_username(self, name: str, platform: str) -> Optional[str]:
        contact = self.resolve(name)
        if contact and platform.lower() in contact.username:
            return contact.username[platform.lower()]
        return None


_contact_store: Optional[ContactStore] = None


def get_contact_store() -> ContactStore:
    global _contact_store
    if _contact_store is None:
        _contact_store = ContactStore()
    return _contact_store
