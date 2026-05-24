"""S1 — Candidate pool builder (screening + scoring + filtering)."""

from __future__ import annotations

from typing import Any, Callable


def candidate_pool_builder(
    *,
    universe: list[dict[str, Any]],
    scoring_fn: Callable[[dict[str, Any]], float],
    filter_rules: list[Callable[[dict[str, Any]], bool]] | None = None,
    top_n: int = 30,
    min_score: float = 0.0,
) -> dict[str, Any]:
    """Build a ranked candidate pool from universe.

    Parameters
    ----------
    universe : list of candidate dicts
    scoring_fn : function(candidate) -> float score
    filter_rules : list of functions that return True to keep, False to reject
    top_n : max candidates to return
    min_score : minimum score threshold

    Returns
    -------
    dict with: candidates (sorted by score desc), stats
    """
    if not universe:
        return {"candidates": [], "stats": {"total": 0, "filtered": 0, "scored": 0}}

    # Apply filters
    filtered = universe
    n_rejected = 0
    if filter_rules:
        kept = []
        for candidate in filtered:
            passed = True
            for rule in filter_rules:
                try:
                    if not rule(candidate):
                        passed = False
                        break
                except Exception:
                    passed = False
                    break
            if passed:
                kept.append(candidate)
            else:
                n_rejected += 1
        filtered = kept

    # Score
    scored: list[tuple[float, dict[str, Any]]] = []
    errors = 0
    for candidate in filtered:
        try:
            score = scoring_fn(candidate)
            if score >= min_score:
                scored.append((score, candidate))
        except Exception:
            errors += 1

    # Sort and truncate
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]

    candidates = [{**c, "_score": s} for s, c in top]

    return {
        "candidates": candidates,
        "stats": {
            "total": len(universe),
            "filtered": n_rejected,
            "scored": len(scored),
            "returned": len(candidates),
            "errors": errors,
        },
    }
