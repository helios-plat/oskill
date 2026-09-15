"""Pure preparation of a governance-bound tool execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from obase.tool_governance import Grant, ToolSpec

from .classify_tool_effect import classify_tool_effect
from .resolve_tool_grant import resolve_tool_grant


def _contains_raw_credential(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_name = str(key).lower().replace("-", "_")
            if any(
                token in key_name
                for token in (
                    "token",
                    "secret",
                    "password",
                    "api_key",
                    "access_key",
                    "private_key",
                    "authorization",
                    "client_secret",
                    "webhook",
                    "credential",
                )
            ):
                return True
            if _contains_raw_credential(item):
                return True
    elif isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_raw_credential(item) for item in value)
    return False


def prepare_tool_execution(
    spec: ToolSpec,
    grant: Grant | None,
    *,
    actor: str = "master",
    resource: str = "*",
    arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate grant/effect and return safe execution metadata.

    Raw credential-shaped arguments are rejected.  Callers must provide a
    ``CredentialRef``/``SecretRef`` and resolve it only after authorization.
    """
    try:
        effect = classify_tool_effect(spec)
    except ValueError as exc:
        return {"verdict": "DENY", "reason": str(exc), "tool": spec.identity}
    if _contains_raw_credential(arguments or {}):
        return {
            "verdict": "DENY",
            "reason": "raw credential argument is forbidden",
            "tool": spec.identity,
        }
    decision = resolve_tool_grant(spec, grant, actor=actor, resource=resource)
    if decision["verdict"] != "ALLOW":
        return decision
    return {
        **decision,
        "effect": effect,
        "resource": resource,
        "credential_ref": spec.credential_ref.to_dict() if spec.credential_ref else None,
    }


__all__ = ["prepare_tool_execution"]
