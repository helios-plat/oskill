"""Stateless browser control and takeover policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

BrowserTakeoverVerdict = Literal["ALLOW_AGENT", "REQUIRE_HUMAN_CONTROL", "DENY"]

_READ_ACTIONS = frozenset({"status", "snapshot", "screenshot"})
_WRITE_ACTIONS = frozenset({"click", "type", "upload"})
_NETWORK_ACTIONS = frozenset({"navigate", "download"})
_SENSITIVE_MARKERS = frozenset(
    {
        "2fa",
        "mfa",
        "otp",
        "one_time_password",
        "login",
        "log_in",
        "signin",
        "sign_in",
        "password",
        "credential",
        "sensitive",
        "sensitive_confirmation",
        "confirmation",
        "authorize",
        "authorization",
        "confirm_payment",
        "confirm_purchase",
    }
)


def _action_name(action: str) -> str:
    normalized = str(action).lower().strip()
    return normalized.removeprefix("browser_").replace("-", "_")


def browser_action_is_read(action: str) -> bool:
    """Return whether an action only reads browser state."""
    return _action_name(action) in _READ_ACTIONS


def browser_action_is_write(action: str) -> bool:
    """Return whether an action can mutate page or remote state."""
    return _action_name(action) in _WRITE_ACTIONS


def classify_browser_action_effect(action: str) -> str:
    """Classify browser effects without storage, task, or vendor knowledge."""
    normalized = _action_name(action)
    if normalized in _READ_ACTIONS:
        return "read"
    if normalized in _NETWORK_ACTIONS:
        return "network"
    if normalized in _WRITE_ACTIONS:
        return "network"
    return "destructive"


def _sensitive_context(context: Mapping[str, Any]) -> bool:
    for key in (
        "sensitive",
        "sensitive_confirmation",
        "requires_human_control",
        "authentication",
        "two_factor",
    ):
        value = context.get(key)
        if value is True or (isinstance(value, str) and value.lower() in {"true", "required"}):
            return True
    raw_markers = context.get("markers", ())
    if isinstance(raw_markers, str):
        raw_markers = (raw_markers,)
    markers = {str(value).lower().replace("-", "_") for value in raw_markers}
    if markers & _SENSITIVE_MARKERS:
        return True
    action_arguments = context.get("action_arguments", {})
    values = action_arguments.values() if isinstance(action_arguments, Mapping) else ()
    return any(
        marker in str(value).lower().replace("-", "_")
        for value in values
        for marker in _SENSITIVE_MARKERS
    )


def review_browser_takeover_need(
    action: str,
    *,
    control_state: str = "AGENT_CONTROL",
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide whether an agent browser action needs human control.

    The function is intentionally pure.  It does not switch control state or
    perform an action; the caller must obtain human approval and explicitly
    set ``HUMAN_CONTROL`` through the browser atomic.
    """
    normalized = _action_name(action)
    details = dict(context or {})
    if control_state not in {"AGENT_CONTROL", "HUMAN_CONTROL"}:
        return {
            "verdict": "DENY",
            "reason": "unknown browser control state",
            "action": normalized,
            "control_state": control_state,
        }
    if control_state == "HUMAN_CONTROL" and not browser_action_is_read(normalized):
        return {
            "verdict": "DENY",
            "reason": "agent browser writes are disabled during HUMAN_CONTROL",
            "action": normalized,
            "control_state": control_state,
        }
    if _sensitive_context(details):
        return {
            "verdict": "REQUIRE_HUMAN_CONTROL",
            "reason": "sensitive browser operation requires human control",
            "action": normalized,
            "control_state": control_state,
        }
    if any(marker in normalized for marker in _SENSITIVE_MARKERS):
        return {
            "verdict": "REQUIRE_HUMAN_CONTROL",
            "reason": "authentication or sensitive browser operation requires human control",
            "action": normalized,
            "control_state": control_state,
        }
    return {
        "verdict": "ALLOW_AGENT",
        "reason": "browser action is allowed for current control state",
        "action": normalized,
        "control_state": control_state,
    }


__all__ = [
    "BrowserTakeoverVerdict",
    "browser_action_is_read",
    "browser_action_is_write",
    "classify_browser_action_effect",
    "review_browser_takeover_need",
]
