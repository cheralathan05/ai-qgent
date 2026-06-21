import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from context.engine import get_context_engine
from memory.engine import get_memory_engine
from knowledge_graph.engine import get_knowledge_graph
from agents.knowledge_agent import get_knowledge_agent
from agents.reasoning_agent import get_reasoning_agent
from understanding.entity_extractor import get_command_understanding_engine

from interconnection.models import AssistantContext, AssistantReply
from interconnection.workflow import InterconnectionWorkflow

logger = logging.getLogger(__name__)


class AssistantLayer:
    """Sits above all three phases. Knows the global state and generates intelligent replies."""

    def __init__(self):
        self.context_engine = get_context_engine()
        self.memory_engine = get_memory_engine()
        self.knowledge_graph = get_knowledge_graph()
        self.knowledge_agent = get_knowledge_agent()
        self.reasoning_agent = get_reasoning_agent()
        self.command_engine = get_command_understanding_engine()
        self.workflow = InterconnectionWorkflow()

    def get_global_context(self) -> AssistantContext:
        ctx = AssistantContext()
        snapshot = self.context_engine.get_current()
        if snapshot:
            ctx.current_device_id = snapshot.current_device_id or ""
            ctx.current_device_type = snapshot.current_device_type or ""
            ctx.current_app = snapshot.current_app or ""
            ctx.current_screen = snapshot.current_screen or ""
            ctx.current_workflow_id = snapshot.current_workflow_id or ""
            ctx.current_knowledge_context = snapshot.current_knowledge_context or ""
            ctx.last_command = snapshot.last_command or ""
            ctx.last_intent = snapshot.last_intent or ""
            ctx.last_target = snapshot.last_target or ""
            ctx.current_documents = list(snapshot.recent_documents)[-10:] if snapshot.recent_documents else []
        try:
            kg_stats = self.knowledge_graph.get_entity_count()
            ctx.metadata["knowledge_graph_entities"] = kg_stats
        except Exception:
            pass
        return ctx

    async def process_command(
        self,
        command: str,
        user_id: str = "default",
        device_id: Optional[str] = None,
    ) -> AssistantReply:
        start = datetime.utcnow()

        reply = AssistantReply()
        reply.intent = "unknown"

        try:
            result = await self.workflow.execute(
                command=command,
                user_id=user_id,
                device_id=device_id,
            )

            reply.message = result.assistant_reply
            reply.success = result.success
            reply.intent = result.intent
            reply.target = result.target
            reply.phase1_result = result.phase1
            reply.phase2_result = result.phase2
            reply.phase3_result = result.phase3
            reply.assistant_context = result.context

        except Exception as e:
            logger.error(f"Assistant layer error: {e}")
            reply.message = "I encountered an error processing your request."
            reply.success = False

        reply.duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        return reply

    def get_context_summary(self) -> Dict[str, Any]:
        ctx = self.get_global_context()
        return ctx.to_dict()


def get_assistant_layer():
    return AssistantLayer()
