"""oskill.query_expansion — expand a query into sub-queries (pure algorithm)."""

from __future__ import annotations

from typing import Any


def query_expansion(
    *,
    query: str,
    llm_caller: Any = None,
    max_subqueries: int = 5,
) -> list[str]:
    """Expand a research query into sub-queries.

    If llm_caller provided, use it; otherwise heuristic split.
    """
    if not query or not query.strip():
        return []
    out = [query.strip()]
    # heuristic: split on conjunctions
    for sep in [" and ", " or ", ",", ";"]:
        if sep in query.lower():
            parts = [p.strip() for p in query.replace(",", " ").split() if p.strip()]
            # fallback simple
            break
    # If LLM caller provided, attempt
    if llm_caller is not None:
        try:
            resp = llm_caller(messages=[{"role": "user", "content": f"Expand into {max_subqueries} sub-queries: {query}"}], max_tokens=512)
            text = ""
            if isinstance(resp, dict):
                text = resp.get("content", "") or resp.get("text", "")
            elif isinstance(resp, str):
                text = resp
            for line in text.splitlines():
                line = line.strip().lstrip("-0123456789. ").strip()
                if line and line not in out:
                    out.append(line)
        except Exception:
            pass
    # dedup + cap
    seen = set()
    res = []
    for q in out:
        if q not in seen:
            seen.add(q)
            res.append(q)
        if len(res) >= max_subqueries:
            break
    if not res:
        res = [query.strip()]
    return res[:max_subqueries]
