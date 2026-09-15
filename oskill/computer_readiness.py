"""Stateless readiness checks for the Computer Supervisor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from obase.computer import ComputerHandle


def evaluate_computer_readiness(
    handle: ComputerHandle | Mapping[str, Any],
    *,
    status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a reported computer state without I/O or persistence."""
    if isinstance(handle, ComputerHandle):
        handle_data = handle.to_dict()
    else:
        handle_data = dict(handle)
    observed = dict(status or {})
    state = str(observed.get("status") or handle_data.get("state") or "failed")
    ready = state in {"running", "attached"}
    return {
        "ready": ready,
        "state": state,
        "computer_id": str(handle_data.get("computer_id") or ""),
        "reason": "computer is ready" if ready else f"computer is not ready: {state}",
    }


__all__ = ["evaluate_computer_readiness"]
