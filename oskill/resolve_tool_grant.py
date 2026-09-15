"""Pure grant resolution for a versioned tool contract."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from obase.tool_governance import Grant, ToolSpec
from oprim.grant_check import grant_check


def resolve_tool_grant(
    spec: ToolSpec,
    grant: Grant | None,
    *,
    actor: str = "master",
    resource: str = "*",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve one grant against the exact tool identity and version."""
    if not spec.enabled:
        return {"verdict": "DENY", "reason": "tool contract is disabled", "tool": spec.identity}
    allowed = grant_check(
        grant,
        tool_identity=spec.identity,
        actor=actor,
        effect=spec.effect,
        version=spec.version,
        resource=resource,
        now=now,
    )
    if not allowed:
        reason = "missing, stale, revoked, or mismatched grant"
        return {"verdict": "DENY", "reason": reason, "tool": spec.identity}
    return {
        "verdict": "ALLOW",
        "reason": "grant matches tool identity, version, actor, and effect",
        "tool": spec.identity,
        "grant_id": grant.grant_id if grant else None,
    }


__all__ = ["resolve_tool_grant"]
