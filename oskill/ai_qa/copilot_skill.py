"""Compatibility surface for the earlier financial Q&A scaffold.

This module intentionally routes requests instead of claiming to know market
prices, account state, or live regimes. Use the command's data source to obtain
any requested value after routing.
"""

from __future__ import annotations

from typing import Any

from oskill.gloom3o_router import LLMCaller, route_gloom3o_command


def route_financial_query(
    query: str,
    *,
    llm_caller: LLMCaller | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Convert a financial query into a command route without inventing data."""
    route = route_gloom3o_command(query, llm_caller=llm_caller, api_key=api_key)
    return {
        "status": "routed" if route.command else "unmatched",
        "command": route.command,
        "arguments": list(route.arguments),
        "options": route.options,
        "source": route.source,
        "reason": route.reason,
    }


def answer_financial_query(
    query: str,
    context_data: dict[str, Any] | None = None,
    *,
    llm_caller: LLMCaller | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible route-only entry point; context is not treated as verified data."""
    del context_data
    return route_financial_query(query, llm_caller=llm_caller, api_key=api_key)
