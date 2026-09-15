"""Stateless Action Gateway policy algorithms."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from obase.action import ActionDecision, ActionRequest, PolicyRule
from oprim._action import policy_match

_EFFECT_BY_ACTION: dict[str, str] = {
    "read": "read",
    "fetch": "read",
    "search": "read",
    "list": "read",
    "write": "local_write",
    "edit": "local_write",
    "delete": "destructive",
    "execute": "process",
    "invoke": "remote",
    "publish": "remote",
}


def classify_action_effect(
    action: str,
    *,
    declared_effect: str | None = None,
) -> str:
    """Classify an action without consulting storage or a vendor SDK."""
    if declared_effect:
        normalized = str(declared_effect).lower()
        aliases = {
            "pure_read": "read",
            "local_write": "local_write",
            "process_exec": "process",
            "network_write": "network",
            "external_mutation": "remote",
            "privileged": "destructive",
        }
        return aliases.get(normalized, normalized)
    normalized_action = str(action).lower()
    for prefix, effect in _EFFECT_BY_ACTION.items():
        if normalized_action == prefix or normalized_action.startswith(f"{prefix}_"):
            return effect
    return "remote"


def evaluate_action_policy(
    request: ActionRequest,
    *,
    rules: Iterable[PolicyRule] = (),
    default_non_read: str = "REQUIRE_APPROVAL",
    context: Mapping[str, Any] | None = None,
) -> ActionDecision:
    """Evaluate one request using explicit rules and a fail-closed default.

    A read with no matching rule is allowed because it cannot mutate state.
    Every other unruled action requires approval (or can be configured to deny).
    An evaluator failure is itself a denial.
    """
    del context  # reserved for injected, stateless policy context
    try:
        candidates = sorted(
            (rule for rule in rules if policy_match(rule, request)),
            key=lambda rule: rule.priority,
            reverse=True,
        )
        if candidates:
            rule = candidates[0]
            return ActionDecision(
                verdict=rule.decision,
                reason=f"matched policy rule '{rule.rule_id}'",
                policy_id=rule.rule_id,
                request_id=request.request_id,
            )
        if request.effect == "read":
            return ActionDecision(
                verdict="ALLOW",
                reason="read-only action has no matching deny rule",
                request_id=request.request_id,
            )
        verdict = default_non_read if default_non_read in {"DENY", "REQUIRE_APPROVAL"} else "DENY"
        return ActionDecision(
            verdict=verdict,  # type: ignore[arg-type]
            reason="non-read action has no matching allow rule",
            request_id=request.request_id,
        )
    except Exception as exc:
        return ActionDecision(
            verdict="DENY",
            reason=f"policy evaluation failed: {type(exc).__name__}",
            request_id=request.request_id,
        )


__all__ = ["classify_action_effect", "evaluate_action_policy"]
