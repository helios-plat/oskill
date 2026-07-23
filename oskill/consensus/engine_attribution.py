"""Per-engine P&L attribution from closed round-trips → weight-learner inputs.

Extraction source: helixa services/factor-analyzer/src (attribution mode: split
each round-trip's net P&L across the engines that voted for it, then track
per-engine win-rate). Pure aggregation; the caller supplies matched round-trips
(each tagged with the engines that drove it) and persists the resulting weights.
"""

from __future__ import annotations


def engine_attribution(round_trips: list[dict]) -> dict:
    """Aggregate realized P&L and win/loss outcomes per contributing engine.

    Each round-trip's outcome (win if net P&L > 0) is credited to every engine
    that drove it, so an engine's accuracy reflects how often the trades it
    voted for were profitable — the signal `oskill.consensus.ewma_weight_update`
    consumes to re-weight engines.

    Parameters
    ----------
    round_trips : list[dict]
        Each: ``{"realized_pnl": float, "engines": list[str]}``.

    Returns
    -------
    dict
        ``{engine: {"total_pnl": float, "count": int, "wins": int,
        "win_rate": float, "results": list[float]}}`` — `results` is the ordered
        win(1.0)/loss(0.0) sequence, ready for `ewma_weight_update`.
    """
    out: dict[str, dict] = {}
    for rt in round_trips:
        pnl = float(rt.get("realized_pnl", 0.0))
        win = 1.0 if pnl > 0 else 0.0
        for eng in rt.get("engines", []):
            d = out.setdefault(eng, {"total_pnl": 0.0, "count": 0, "wins": 0, "results": []})
            d["total_pnl"] += pnl
            d["count"] += 1
            d["wins"] += int(win)
            d["results"].append(win)
    for d in out.values():
        d["win_rate"] = (d["wins"] / d["count"]) if d["count"] else 0.0
    return out
