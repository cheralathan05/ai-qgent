from interconnection.models import (
    UnifiedCommandResult,
    Phase1Result,
    Phase2Result,
    Phase3Result,
    AssistantContext,
    AssistantReply,
)
from interconnection.workflow import InterconnectionWorkflow
from interconnection.assistant import AssistantLayer
from interconnection.planner import UnifiedPlanner

def get_interconnection_workflow():
    return InterconnectionWorkflow()

def get_assistant_layer():
    return AssistantLayer()

def get_unified_planner():
    return UnifiedPlanner()
