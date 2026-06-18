"""Workflow engine wrapper for executing commands."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Manages workflow execution lifecycle."""

    def __init__(self):
        self.orchestrator = None

    def get_orchestrator(self, session=None, adb_client=None, ollama_client=None):
        from orchestrator import get_workflow_orchestrator
        self.orchestrator = get_workflow_orchestrator(
            session=session,
            adb_client=adb_client,
            ollama_client=ollama_client,
        )
        return self.orchestrator


workflow_engine = WorkflowEngine()


def get_workflow_engine(session=None, adb_client=None, ollama_client=None):
    return workflow_engine.get_orchestrator(session=session, adb_client=adb_client, ollama_client=ollama_client)
