"""Pure usage aggregation skill."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _get(record: Any, key: str, default: Any = 0) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def aggregate_usage(
    records: Iterable[Any], *, pricing: Mapping[Any, Any] | None = None
) -> dict[str, Any]:
    """Aggregate normalized usage without persisting or mutating records."""
    items = list(records)
    input_tokens = sum(int(_get(item, "input_tokens", 0) or 0) for item in items)
    output_tokens = sum(int(_get(item, "output_tokens", 0) or 0) for item in items)
    latency_values = [
        float(_get(item, "latency_ms")) for item in items if _get(item, "latency_ms") is not None
    ]
    known_costs = [_get(item, "estimated_cost_usd") for item in items]
    if all(cost is not None for cost in known_costs):
        cost = sum(float(value) for value in known_costs)
    elif pricing:
        cost = 0.0
        for item in items:
            key = (str(_get(item, "provider", "")), str(_get(item, "model", "")))
            price = pricing.get(key, pricing.get(key[1], {}))
            if isinstance(price, Mapping):
                cost += int(_get(item, "input_tokens", 0) or 0) * float(
                    price.get("input_usd_per_token", 0.0)
                )
                cost += int(_get(item, "output_tokens", 0) or 0) * float(
                    price.get("output_usd_per_token", 0.0)
                )
    else:
        cost = None
    return {
        "calls": len(items),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "latency_ms_total": sum(latency_values),
        "estimated_cost_usd": cost,
        "successful_calls": sum(1 for item in items if bool(_get(item, "success", True))),
    }


__all__ = ["aggregate_usage"]
