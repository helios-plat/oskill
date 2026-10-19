"""oskill.search_synthesize_loop — iterative search + synthesize (pure orchestration)."""

from __future__ import annotations

from typing import Any, Callable


def search_synthesize_loop(
    *,
    query: str,
    search_fn: Callable[[str], Any] | None = None,
    synthesize_fn: Callable[[str, list[Any]], str] | None = None,
    max_iterations: int = 3,
    llm_caller: Any = None,
) -> dict[str, Any]:
    """Run search/synthesize iterations.

    Returns {iterations: [{query, results, synthesis}], final: str}.
    """
    iterations = []
    current_query = query
    final = ""
    for i in range(max_iterations):
        results = []
        if search_fn is not None:
            try:
                results = search_fn(current_query) or []
            except Exception:
                results = []
        synthesis = ""
        if synthesize_fn is not None:
            try:
                synthesis = synthesize_fn(current_query, results) or ""
            except Exception:
                synthesis = ""
        elif llm_caller is not None:
            try:
                resp = llm_caller(messages=[{"role": "user", "content": f"Synthesize answer for: {current_query}\nResults: {results}"}], max_tokens=1024)
                synthesis = resp.get("content", "") if isinstance(resp, dict) else str(resp)
            except Exception:
                synthesis = ""
        iterations.append({"iteration": i, "query": current_query, "results": results, "synthesis": synthesis})
        final = synthesis or final
        # refine query naively: append "more details" not; just break if no results
        if not results:
            break
        current_query = f"{query} (refined {i+1})"
    return {"iterations": iterations, "final": final}
