"""Stateless execution-provider selection.

This skill deliberately accepts only execution constraints.  It never looks
at prompt text, task names, or user intent.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _models(provider: Any) -> list[Any]:
    raw = _value(provider, "models", ())
    return list(raw or ())


def _supports(model: Any, capability: str | None, streaming: bool, tools: bool) -> bool:
    caps = set(_value(model, "capabilities", ()) or ())
    if capability and capability not in caps:
        return False
    if streaming and not bool(_value(model, "supports_streaming", False)):
        return False
    if tools and not bool(_value(model, "supports_tools", False)):
        return False
    return True


def _model_cost(model: Any) -> float:
    pricing = _value(model, "pricing")
    if isinstance(pricing, Mapping):
        return float(pricing.get("input_usd_per_token", 0.0) or 0.0) + float(
            pricing.get("output_usd_per_token", 0.0) or 0.0
        )
    return float(_value(model, "cost_usd", 0.0) or 0.0)


def select_provider(
    candidates: Iterable[Any],
    *,
    capability: str | None = "chat",
    model: str | None = None,
    streaming: bool = False,
    tools: bool = False,
    preferred_provider: str | None = None,
    exclude: Iterable[str] = (),
) -> dict[str, Any]:
    """Select the best available provider using explicit constraints only."""
    excluded = {str(item) for item in exclude}
    viable: list[tuple[tuple[Any, ...], Any, Any]] = []
    for provider in candidates:
        name = str(_value(provider, "name", ""))
        if not name or name in excluded or not bool(_value(provider, "enabled", True)):
            continue
        health = _value(provider, "health")
        if health is not None and not bool(_value(health, "healthy", False)):
            continue
        provider_caps = set(_value(provider, "capabilities", ()) or ())
        for candidate_model in _models(provider):
            model_name = str(_value(candidate_model, "name", ""))
            if model and model_name != model:
                continue
            model_caps = set(_value(candidate_model, "capabilities", ()) or ())
            if capability and capability not in provider_caps and capability not in model_caps:
                continue
            if not _supports(candidate_model, None, streaming, tools):
                continue
            priority = int(_value(provider, "priority", 0) or 0)
            health_score = 1.0 if health is None else float(_value(health, "healthy", False))
            latency = float(_value(health, "latency_ms", 0.0) or 0.0) if health else 0.0
            preferred = 0 if preferred_provider and name == preferred_provider else 1
            # Explicit preference and health/priority come before cost/latency.
            sort_key = (
                preferred,
                -health_score,
                -priority,
                _model_cost(candidate_model),
                latency,
                name,
                model_name,
            )
            viable.append((sort_key, provider, candidate_model))
    if not viable:
        raise ValueError("no provider satisfies the requested execution constraints")
    _, provider, candidate_model = min(viable, key=lambda item: item[0])
    return {
        "provider": str(_value(provider, "name")),
        "model": str(_value(candidate_model, "name")),
        "credential_ref": _value(provider, "credential_ref"),
        "capabilities": sorted(set(_value(candidate_model, "capabilities", ()) or ())),
        "reason": "capability_health_priority_cost_latency",
    }


__all__ = ["select_provider"]
