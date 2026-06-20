from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .access_control import AccessRole, Permission, get_access_control


@dataclass
class PolicyRule:
    field: str
    operator: str  # eq, neq, gt, lt, contains, in
    value: Any
    effect: str  # allow, deny

    def matches(self, context: dict) -> Optional[bool]:
        actual = context.get(self.field)
        if actual is None:
            return None

        if self.operator == "eq":
            result = actual == self.value
        elif self.operator == "neq":
            result = actual != self.value
        elif self.operator == "gt":
            try:
                result = float(actual) > float(self.value)
            except (TypeError, ValueError):
                result = False
        elif self.operator == "lt":
            try:
                result = float(actual) < float(self.value)
            except (TypeError, ValueError):
                result = False
        elif self.operator == "contains":
            result = self.value in str(actual)
        elif self.operator == "in":
            result = actual in self.value if isinstance(self.value, (list, tuple, set)) else str(actual) in str(self.value)
        else:
            return None

        return result if self.effect == "allow" else (not result if result is not None else None)


@dataclass
class Policy:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    rules: list[PolicyRule] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        defaults = [
            Policy(
                id="policy_msg_send",
                name="Message Sending Policy",
                description="Controls who can send messages",
                priority=100,
                rules=[
                    PolicyRule(field="action", operator="eq", value="send_message", effect="allow"),
                    PolicyRule(field="role", operator="neq", value="GUEST", effect="allow"),
                ],
            ),
            Policy(
                id="policy_app_launch",
                name="App Launching Policy",
                description="Controls which apps can be launched",
                priority=90,
                rules=[
                    PolicyRule(field="action", operator="eq", value="launch_app", effect="allow"),
                    PolicyRule(field="app_source", operator="in", value=["verified", "enterprise", "system"], effect="allow"),
                    PolicyRule(field="role", operator="eq", value="GUEST", effect="deny"),
                ],
            ),
            Policy(
                id="policy_file_ops",
                name="File Operations Policy",
                description="Controls file read/write/delete operations",
                priority=80,
                rules=[
                    PolicyRule(field="action", operator="in", value=["read_file", "write_file", "delete_file"], effect="allow"),
                    PolicyRule(field="role", operator="neq", value="VIEWER", effect="allow"),
                ],
            ),
            Policy(
                id="policy_device_control",
                name="Device Control Policy",
                description="Controls device management actions",
                priority=70,
                rules=[
                    PolicyRule(field="action", operator="in", value=["configure_device", "pair_device", "unpair_device", "device_action"], effect="allow"),
                    PolicyRule(field="role", operator="in", value=["ADMIN", "DEVICE_OPERATOR"], effect="allow"),
                ],
            ),
        ]
        for p in defaults:
            self._policies[p.id] = p

    def add_policy(self, policy: Policy) -> None:
        self._policies[policy.id] = policy

    def remove_policy(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self._policies.get(policy_id)

    def list_policies(self) -> list[Policy]:
        return sorted(self._policies.values(), key=lambda p: p.priority, reverse=True)

    def evaluate(self, action_type: str, resource: str, context: dict) -> dict:
        resolved = {"action": action_type, "resource": resource, **context}
        matched_policies: list[str] = []
        reasons: list[str] = []
        allowed = False

        for policy in sorted(self._policies.values(), key=lambda p: p.priority, reverse=True):
            if not policy.enabled:
                continue

            all_match = True
            for rule in policy.rules:
                result = rule.matches(resolved)
                if result is None:
                    all_match = False
                    break
                if not result:
                    all_match = False
                    break

            if all_match:
                matched_policies.append(policy.id)
                # Determine overall effect from the first matching rule's effect
                for rule in policy.rules:
                    r = rule.matches(resolved)
                    if r is not None:
                        if rule.effect == "allow" and r:
                            allowed = True
                        elif rule.effect == "deny" and r:
                            allowed = False
                            reasons.append(f"Denied by rule '{rule.field} {rule.operator} {rule.value}' in policy '{policy.name}'")
                        break

        if not matched_policies:
            allowed = False
            reasons.append("No matching policy found")

        return {
            "allowed": allowed,
            "matched_policies": matched_policies,
            "reason": "; ".join(reasons) if reasons else "Allowed by policy",
        }

    def evaluate_workflow(self, workflow_data: dict) -> dict:
        action_type = workflow_data.get("action_type", "unknown")
        resource = workflow_data.get("resource", "unknown")
        context = {k: v for k, v in workflow_data.items() if k not in ("action_type", "resource")}
        return self.evaluate(action_type, resource, context)

    def evaluate_device_action(self, device_id: str, action: str, context: dict) -> dict:
        resolved = {"device_id": device_id, "action": action, **context}
        return self.evaluate("device_action", f"device:{device_id}", resolved)


_engine_instance: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = PolicyEngine()
    return _engine_instance
