"""
APA-OS Automation Engine
Workflow triggers, conditions, actions, and scheduling
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AutomationAction:
    """Single automation action"""
    type: str  # open_app, send_message, create_task, notify, adb_command
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationCondition:
    """Automation condition"""
    type: str  # message_contains, app_is, time_between, battery_above, etc.
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationTrigger:
    """Automation trigger"""
    type: str  # message_received, app_opened, time_based, notification, manual
    params: Dict[str, Any] = field(default_factory=dict)


class AutomationEngine:
    """Complete automation engine with triggers, conditions, and actions"""

    def __init__(self, adb_service=None):
        self._adb = adb_service
        self._active_rules: Dict[str, Dict] = {}

    def _get_db(self):
        from database.connection import get_db_session
        return get_db_session()

    # ==================== Rule Management ====================

    def create_rule(
        self,
        user_id: str,
        name: str,
        trigger_type: str,
        trigger_config: Dict[str, Any],
        actions: List[Dict[str, Any]],
        conditions: List[Dict[str, Any]] = None,
        device_id: str = None,
        description: str = "",
    ) -> Dict[str, Any]:
        """Create a new automation rule"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule
            import uuid

            rule_id = f"auto_{uuid.uuid4().hex[:12]}"
            rule = AutomationRule(
                id=rule_id,
                user_id=user_id,
                device_id=device_id,
                name=name,
                description=description,
                is_active=True,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
                conditions=conditions or [],
                actions=actions,
            )
            db.add(rule)
            db.commit()

            # Cache active rule
            self._active_rules[rule_id] = {
                "user_id": user_id,
                "device_id": device_id,
                "trigger_type": trigger_type,
                "trigger_config": trigger_config,
                "conditions": conditions or [],
                "actions": actions,
            }

            logger.info(f"Automation rule created: {rule_id} ({name})")
            return {"success": True, "rule_id": rule_id, "name": name}
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create automation rule: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all automation rules for a user"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rules = db.query(AutomationRule).filter(
                AutomationRule.user_id == user_id,
            ).order_by(AutomationRule.created_at.desc()).all()

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "is_active": r.is_active,
                    "trigger_type": r.trigger_type.value if hasattr(r.trigger_type, 'value') else r.trigger_type,
                    "trigger_config": r.trigger_config,
                    "conditions": r.conditions,
                    "actions": r.actions,
                    "run_count": r.run_count,
                    "last_run_at": r.last_run_at.isoformat() if r.last_run_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rules
            ]
        finally:
            db.close()

    def update_rule(self, rule_id: str, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an automation rule"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rule = db.query(AutomationRule).filter(
                AutomationRule.id == rule_id,
                AutomationRule.user_id == user_id,
            ).first()

            if not rule:
                return {"success": False, "error": "Rule not found"}

            for key, value in updates.items():
                if hasattr(rule, key) and key not in ("id", "user_id", "created_at"):
                    setattr(rule, key, value)

            rule.updated_at = datetime.utcnow()
            db.commit()
            return {"success": True, "rule_id": rule_id}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def delete_rule(self, rule_id: str, user_id: str) -> Dict[str, Any]:
        """Delete an automation rule"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rule = db.query(AutomationRule).filter(
                AutomationRule.id == rule_id,
                AutomationRule.user_id == user_id,
            ).first()

            if not rule:
                return {"success": False, "error": "Rule not found"}

            db.delete(rule)
            db.commit()
            self._active_rules.pop(rule_id, None)
            return {"success": True, "rule_id": rule_id}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    # ==================== Rule Execution ====================

    async def execute_rule(
        self,
        rule_id: str,
        user_id: str,
        device_id: str = None,
        trigger_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Execute an automation rule"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule, AutomationRun
            import uuid

            rule = db.query(AutomationRule).filter(
                AutomationRule.id == rule_id,
                AutomationRule.user_id == user_id,
            ).first()

            if not rule:
                return {"success": False, "error": "Rule not found"}

            if not rule.is_active:
                return {"success": False, "error": "Rule is inactive"}

            # Create run record
            run_id = str(uuid.uuid4())
            run = AutomationRun(
                id=run_id,
                rule_id=rule_id,
                user_id=user_id,
                device_id=device_id or rule.device_id,
                trigger_data=trigger_data or {},
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(run)
            db.commit()

            # Check conditions
            conditions = rule.conditions or []
            if conditions:
                conditions_met = await self._check_conditions(conditions, device_id, trigger_data or {})
                if not conditions_met:
                    run.status = "completed"
                    run.result = {"skipped": True, "reason": "conditions not met"}
                    run.completed_at = datetime.utcnow()
                    db.commit()
                    return {"success": True, "skipped": True, "reason": "conditions not met"}

            # Execute actions
            results = []
            actions = rule.actions or []
            for action_def in actions:
                action_result = await self._execute_action(action_def, device_id or rule.device_id, user_id)
                results.append(action_result)

            # Update rule stats
            rule.run_count = (rule.run_count or 0) + 1
            rule.last_run_at = datetime.utcnow()
            rule.last_result = {"results": results}

            # Update run record
            run.status = "completed"
            run.result = {"results": results}
            run.completed_at = datetime.utcnow()
            run.duration_ms = int((datetime.utcnow() - run.started_at).total_seconds() * 1000)
            db.commit()

            logger.info(f"Automation rule executed: {rule_id} ({len(results)} actions)")
            return {"success": True, "results": results, "run_id": run_id}
        except Exception as e:
            logger.error(f"Automation execution failed: {e}")
            try:
                run.status = "failed"
                run.error = str(e)
                run.completed_at = datetime.utcnow()
                db.commit()
            except Exception:
                pass
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    async def _check_conditions(
        self,
        conditions: List[Dict[str, Any]],
        device_id: str,
        trigger_data: Dict[str, Any],
    ) -> bool:
        """Check if all conditions are met"""
        for cond in conditions:
            cond_type = cond.get("type", "")
            params = cond.get("params", {})

            if cond_type == "message_contains":
                text = trigger_data.get("message", "")
                keyword = params.get("keyword", "")
                if keyword.lower() not in text.lower():
                    return False

            elif cond_type == "app_is":
                expected_app = params.get("app", "")
                current_app = trigger_data.get("foreground_app", "")
                if expected_app.lower() not in current_app.lower():
                    return False

            elif cond_type == "time_between":
                start_time = params.get("start", "00:00")
                end_time = params.get("end", "23:59")
                now = datetime.now().strftime("%H:%M")
                if not (start_time <= now <= end_time):
                    return False

            elif cond_type == "battery_above":
                threshold = params.get("threshold", 50)
                battery = trigger_data.get("battery_level", 100)
                if battery < threshold:
                    return False

            elif cond_type == "battery_below":
                threshold = params.get("threshold", 20)
                battery = trigger_data.get("battery_level", 0)
                if battery > threshold:
                    return False

        return True

    async def _execute_action(
        self,
        action_def: Dict[str, Any],
        device_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Execute a single automation action"""
        action_type = action_def.get("type", "")
        params = action_def.get("params", {})

        try:
            if action_type == "open_app":
                app = params.get("app", "")
                if self._adb:
                    await self._adb.shell(device_id, f"monkey -p {app} 1")
                return {"type": "open_app", "app": app, "success": True}

            elif action_type == "send_message":
                # Would send via notification agent
                return {"type": "send_message", "success": True, "params": params}

            elif action_type == "notify":
                from services.notification_service import get_notification_service
                service = get_notification_service()
                notif_id = service.create_notification(
                    user_id=user_id,
                    device_id=device_id,
                    title=params.get("title", "Automation"),
                    body=params.get("body", "Rule executed"),
                    notification_type=params.get("type", "info"),
                )
                return {"type": "notify", "success": True, "notification_id": notif_id}

            elif action_type == "create_task":
                # Would create a task
                return {"type": "create_task", "success": True, "params": params}

            elif action_type == "adb_command":
                command = params.get("command", "")
                if self._adb:
                    result = await self._adb.shell(device_id, command)
                    return {"type": "adb_command", "success": True, "output": str(result)[:200]}
                return {"type": "adb_command", "success": False, "error": "ADB not available"}

            elif action_type == "delay":
                seconds = params.get("seconds", 1)
                await asyncio.sleep(seconds)
                return {"type": "delay", "success": True, "seconds": seconds}

            return {"type": action_type, "success": False, "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            return {"type": action_type, "success": False, "error": str(e)}

    # ==================== Trigger Events ====================

    async def on_message_received(self, user_id: str, device_id: str, message_data: Dict[str, Any]):
        """Handle incoming message trigger"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rules = db.query(AutomationRule).filter(
                AutomationRule.user_id == user_id,
                AutomationRule.is_active == True,
                AutomationRule.trigger_type == "message_received",
            ).all()

            for rule in rules:
                await self.execute_rule(rule.id, user_id, device_id, trigger_data=message_data)
        finally:
            db.close()

    async def on_app_opened(self, user_id: str, device_id: str, app_name: str):
        """Handle app opened trigger"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rules = db.query(AutomationRule).filter(
                AutomationRule.user_id == user_id,
                AutomationRule.is_active == True,
                AutomationRule.trigger_type == "app_opened",
            ).all()

            for rule in rules:
                trigger_config = rule.trigger_config or {}
                if trigger_config.get("app", "").lower() in app_name.lower():
                    await self.execute_rule(rule.id, user_id, device_id, {"app_name": app_name})
        finally:
            db.close()

    async def check_time_triggers(self):
        """Check and execute time-based triggers (called periodically)"""
        db = self._get_db()
        try:
            from database.auth_models import AutomationRule

            rules = db.query(AutomationRule).filter(
                AutomationRule.is_active == True,
                AutomationRule.trigger_type == "time_based",
            ).all()

            for rule in rules:
                trigger_config = rule.trigger_config or {}
                scheduled_time = trigger_config.get("time", "")
                now = datetime.now().strftime("%H:%M")

                if scheduled_time == now:
                    await self.execute_rule(rule.id, rule.user_id, rule.device_id)
        finally:
            db.close()


# ==================== Singleton ====================

_automation_engine: Optional[AutomationEngine] = None


def get_automation_engine(adb_service=None) -> AutomationEngine:
    global _automation_engine
    if _automation_engine is None:
        _automation_engine = AutomationEngine(adb_service)
    return _automation_engine
