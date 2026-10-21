"""oskill.intent_categorization — NEW_KNOWLEDGE vs LOGIC_CORRECTION."""

from __future__ import annotations

from typing import Any, Protocol


class LLMCaller(Protocol):
    async def __call__(self, *, messages: list[dict[str, Any]], max_tokens: int = 4096) -> dict: ...


async def categorize_diff_intent(
    diff_struct: dict[str, Any],
    *,
    llm_caller: LLMCaller | None = None,
) -> dict[str, Any]:
    """Classify a diff. LLM optional; heuristic always available for tests."""
    heuristic = _heuristic(diff_struct)
    if llm_caller is None:
        return heuristic
    prompt = (
        "Classify this code diff as NEW_KNOWLEDGE or LOGIC_CORRECTION. "
        "Reply with JSON {\"category\": \"...\"}.\n"
        f"diff={diff_struct}"
    )
    rec = await llm_caller(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=128,
    )
    category = _extract_category(rec)
    if category not in {"NEW_KNOWLEDGE", "LOGIC_CORRECTION"}:
        return heuristic
    return {"category": category, "source": "llm", "ok": True}


def _heuristic(diff_struct: dict[str, Any]) -> dict[str, Any]:
    if diff_struct.get("logic_change"):
        category = "LOGIC_CORRECTION"
    elif diff_struct.get("knowledge_change") or diff_struct.get("has_meaningful_change"):
        category = "NEW_KNOWLEDGE"
    else:
        category = "NEW_KNOWLEDGE"
    return {"category": category, "source": "heuristic", "ok": True}


def _extract_category(rec: dict[str, Any]) -> str:
    if rec.get("category") in {"NEW_KNOWLEDGE", "LOGIC_CORRECTION"}:
        return str(rec["category"])
    text = str(rec.get("content") or rec.get("text") or "")
    if "LOGIC_CORRECTION" in text:
        return "LOGIC_CORRECTION"
    if "NEW_KNOWLEDGE" in text:
        return "NEW_KNOWLEDGE"
    return ""
