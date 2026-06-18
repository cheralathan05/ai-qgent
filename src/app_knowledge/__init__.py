"""Layer 5: App Knowledge System - stores known screens, buttons, menus, and workflows per app."""

from .app_knowledge import AppKnowledge, AppDefinition, get_app_knowledge

__all__ = ["AppKnowledge", "AppDefinition", "get_app_knowledge"]
