"""Pure classification of a declared tool effect."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from obase.tool_governance import ToolEffect, ToolSpec

_ALIASES: dict[str, ToolEffect] = {
    "pure_read": "read",
    "local_write": "local_write",
    "process_exec": "process",
    "network_write": "network",
    "external_mutation": "remote",
    "privileged": "destructive",
}
_EFFECTS = frozenset({"read", "local_write", "process", "network", "remote", "destructive"})


def classify_tool_effect(
    tool: ToolSpec | Mapping[str, Any] | str,
    *,
    declared_effect: str | None = None,
) -> ToolEffect:
    """Return the explicit effect; unknown effects fail closed."""
    if declared_effect is not None:
        raw = str(declared_effect).lower()
    elif isinstance(tool, ToolSpec):
        raw = tool.effect
    elif isinstance(tool, Mapping):
        raw = str(tool.get("effect") or "")
    else:
        raise ValueError("tool effect must be declared by a ToolSpec")
    effect = _ALIASES.get(raw, raw)
    if effect not in _EFFECTS:
        raise ValueError(f"unsupported tool effect: {raw!r}")
    return effect  # type: ignore[return-value]


__all__ = ["classify_tool_effect"]
