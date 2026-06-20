from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class ApprovalRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    trigger_conditions: list[dict] = field(default_factory=list)
    required_approvers: int = 1
    timeout_seconds: int = 300


@dataclass
class ApprovalRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rule_id: str = ""
    workflow_id: str = ""
    user_id: str = ""
    action_data: dict = field(default_factory=dict)
    status: str = "pending"  # pending, approved, rejected, expired
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    reason: Optional[str] = None


def _condition_matches(condition: dict, action_type: str, action_data: dict) -> bool:
    field = condition.get("field", "")
    operator = condition.get("operator", "eq")
    value = condition.get("value")

    if field == "action_type":
        actual = action_type
    else:
        actual = action_data.get(field)

    if actual is None:
        return False

    if operator == "eq":
        return actual == value
    elif operator == "neq":
        return actual != value
    elif operator == "in":
        return actual in value if isinstance(value, (list, tuple, set)) else str(actual) in str(value)
    elif operator == "contains":
        return value in str(actual)
    return False


class ApprovalRules:
    def __init__(self) -> None:
        self._rules: dict[str, ApprovalRule] = {}
        self._requests: dict[str, ApprovalRequest] = {}
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        defaults = [
            ApprovalRule(
                id="approval_send_message",
                name="Message Approval",
                description="Requires approval to send messages to external recipients",
                trigger_conditions=[
                    {"field": "action_type", "operator": "eq", "value": "send_message"},
                    {"field": "recipient_type", "operator": "eq", "value": "external"},
                ],
                required_approvers=1,
                timeout_seconds=300,
            ),
            ApprovalRule(
                id="approval_delete_file",
                name="File Deletion Approval",
                description="Requires approval for permanent file deletion",
                trigger_conditions=[
                    {"field": "action_type", "operator": "eq", "value": "delete_file"},
                    {"field": "permanent", "operator": "eq", "value": True},
                ],
                required_approvers=1,
                timeout_seconds=600,
            ),
            ApprovalRule(
                id="approval_access_credentials",
                name="Credential Access Approval",
                description="Requires approval to access stored credentials",
                trigger_conditions=[
                    {"field": "action_type", "operator": "eq", "value": "access_credentials"},
                ],
                required_approvers=2,
                timeout_seconds=120,
            ),
            ApprovalRule(
                id="approval_sideload_app",
                name="Sideload App Approval",
                description="Requires approval to install unverified applications",
                trigger_conditions=[
                    {"field": "action_type", "operator": "eq", "value": "install_app"},
                    {"field": "app_source", "operator": "neq", "value": "verified"},
                ],
                required_approvers=2,
                timeout_seconds=600,
            ),
        ]
        for r in defaults:
            self._rules[r.id] = r

    def add_rule(self, rule: ApprovalRule) -> None:
        self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[ApprovalRule]:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[ApprovalRule]:
        return list(self._rules.values())

    def check_required(self, action_type: str, action_data: dict) -> Optional[ApprovalRule]:
        for rule in self._rules.values():
            for condition in rule.trigger_conditions:
                if _condition_matches(condition, action_type, action_data):
                    return rule
        return None

    def create_approval_request(self, rule: ApprovalRule, workflow_id: str, user_id: str, action_data: dict) -> str:
        request = ApprovalRequest(
            rule_id=rule.id,
            workflow_id=workflow_id,
            user_id=user_id,
            action_data=action_data,
        )
        self._requests[request.id] = request
        return request.id

    def approve_request(self, request_id: str, approver_id: str, reason: Optional[str] = None) -> bool:
        req = self._requests.get(request_id)
        if req is None or req.status != "pending":
            return False
        req.status = "approved"
        req.decided_by = approver_id
        req.decision_at = datetime.now(timezone.utc)
        req.reason = reason
        return True

    def reject_request(self, request_id: str, approver_id: str, reason: Optional[str] = None) -> bool:
        req = self._requests.get(request_id)
        if req is None or req.status != "pending":
            return False
        req.status = "rejected"
        req.decided_by = approver_id
        req.decision_at = datetime.now(timezone.utc)
        req.reason = reason
        return True

    def get_pending_approvals(self, user_id: str) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.user_id == user_id and r.status == "pending"]


_instance: Optional[ApprovalRules] = None


def get_approval_rules() -> ApprovalRules:
    global _instance
    if _instance is None:
        _instance = ApprovalRules()
    return _instance
