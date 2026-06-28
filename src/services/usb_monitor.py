"""
USB Monitor - Background worker that checks ADB device connectivity every 2 seconds.
Detects disconnections and updates the PairingWorkflow state machine accordingly.
"""

import asyncio
import logging
from datetime import datetime

from services.pairing_workflow_service import get_pairing_workflow_service, WorkflowState, TERMINAL_STATES
from database.connection import get_db_session
from database.auth_models import PairingWorkflow

logger = logging.getLogger(__name__)


class USBMonitor:
    """Background worker that polls ADB device list and detects disconnections."""

    def __init__(self):
        self._running = False
        self._task = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("USB Monitor started (checking every 2 seconds)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("USB Monitor stopped")

    async def _monitor_loop(self):
        while self._running:
            try:
                await self._check_devices()
            except Exception as e:
                logger.error(f"USB monitor check failed: {e}")
            await asyncio.sleep(2.0)

    async def _check_devices(self):
        """Check all active workflows and verify their devices are still connected."""
        svc = get_pairing_workflow_service()
        db = get_db_session()
        try:
            # Find all non-terminal workflows with serial numbers
            active_workflows = db.query(PairingWorkflow).filter(
                PairingWorkflow.workflow_state.notin_([s.value for s in TERMINAL_STATES]),
                PairingWorkflow.serial != None,
                PairingWorkflow.serial != "",
                PairingWorkflow.connected == True,
            ).all()

            for workflow in active_workflows:
                serial = workflow.serial
                if not serial:
                    continue

                # Check ADB connectivity
                is_connected = svc.is_device_connected_via_adb(serial)

                if not is_connected and workflow.connected:
                    # Device disappeared - mark as disconnected
                    logger.info(f"Device {serial} disconnected (workflow {workflow.id})")
                    svc.mark_disconnected(workflow.user_id, serial)

        except Exception as e:
            logger.error(f"Error in USB monitor device check: {e}")
        finally:
            db.close()


_monitor = None


def get_usb_monitor() -> USBMonitor:
    global _monitor
    if _monitor is None:
        _monitor = USBMonitor()
    return _monitor
