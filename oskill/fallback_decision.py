"""Stateless provider fallback policy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def fallback_decision(
    attempts: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any] | str | None = None,
    max_attempts: int = 2,
) -> dict[str, Any]:
    """Decide whether another execution candidate may be tried.

    The decision is based on explicit call outcomes and limits, never on
    prompt content or inferred task type.
    """
    settings = dict(policy) if isinstance(policy, Mapping) else {}
    mode = str(settings.get("mode", policy if isinstance(policy, str) else "on_error"))
    limit = int(settings.get("max_attempts", max_attempts))
    if mode in {"never", "disabled", "none"}:
        return {"retry": False, "reason": "fallback_disabled"}
    if len(attempts) >= max(1, limit):
        return {"retry": False, "reason": "attempt_limit_reached"}
    if not attempts:
        return {"retry": False, "reason": "no_failed_attempt"}
    last = attempts[-1]
    if bool(last.get("success", False)) and not last.get("error"):
        return {"retry": False, "reason": "previous_attempt_succeeded"}
    retryable = settings.get("retryable_errors")
    error_type = str(last.get("error_type", last.get("error", "provider_error")))
    if retryable is not None and error_type not in {str(item) for item in retryable}:
        return {"retry": False, "reason": "error_not_retryable", "error_type": error_type}
    return {"retry": True, "reason": "explicit_provider_failure", "error_type": error_type}


__all__ = ["fallback_decision"]
