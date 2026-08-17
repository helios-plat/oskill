"""categorize_diff_intent heuristic + injected LLM."""

from __future__ import annotations

import pytest

from oskill.intent_categorization import categorize_diff_intent


@pytest.mark.asyncio
async def test_heuristic_logic() -> None:
    rec = await categorize_diff_intent({"logic_change": True, "has_meaningful_change": True})
    assert rec["category"] == "LOGIC_CORRECTION"
    assert rec["source"] == "heuristic"


@pytest.mark.asyncio
async def test_llm_overrides() -> None:
    async def caller(*, messages, max_tokens=4096):
        return {"content": '{"category": "NEW_KNOWLEDGE"}'}

    rec = await categorize_diff_intent(
        {"logic_change": True, "has_meaningful_change": True},
        llm_caller=caller,
    )
    assert rec["category"] == "NEW_KNOWLEDGE"
    assert rec["source"] == "llm"
