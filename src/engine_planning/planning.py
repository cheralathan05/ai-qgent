import asyncio
import logging
from src.core.conversation_manager import get_conversation_manager
from src.core.intent_engine import get_intent_engine
from src.core.planning.task_planner import get_task_planner
from src.core.planning.execution_planner import get_execution_planner
from src.core.perception import get_perception_engine
from src.core.navigation.navigation_engine import get_navigation_engine

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Conversation engine for Phase 1 - management of conversation flow."""
    
    def __init__(self):
        self.conversation_manager = get_conversation_manager()
    
    async def analyze(self, command: str) -> str:
        """Analyze the conversation and extract the core intent."""
        # For now, just return the command as intent
        return f"Goal: {command}"


class TaskPlanner:
    """Task planner for Phase 8 - decomposes goals into steps."""
    
    def __init__(self):
        pass
    
    async def decompose(self, intent: str, context: dict) -> list:
        """Decompose intent into actionable steps."""
        return []


def get_conversation_engine():
    return ConversationEngine()


def get_task_planner():
    return TaskPlanner()


def get_execution_planner():
    """Execution planner factory function."""
    from src.engine_planning.execution_planner import ExecutionPlanner
    return ExecutionPlanner()
