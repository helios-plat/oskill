"""Multi-engine consensus fusion — weighted, decayed, regime/sentiment-adjusted.

Composites used:
    1. oprim.clip_with_warning — bound the blended consensus score to [-1, 1].
    2. oskill.signal.sentiment_onchain_synthesis.fgi_sentiment_bias — (called by
       the adapter; its output is passed in as `sentiment_bias`).

Extraction source: helixa services/prob-engine/src/aggregator.py + regime.py.
The decisive helivex difference: only engines whose own gate PASSED
(`promoted=True`) drive the live consensus. helixa let every engine vote
(a 0.2315-accuracy model included); here un-promoted engines are recorded for
observability but contribute 0 to the executable score.
"""

from __future__ import annotations

# regime → (threshold add, all-engine weight scale)
_REGIME_ADJ = {
    "trend": (-0.05, 1.0),
    "range": (0.05, 1.0),
    "crisis": (0.15, 0.3),
}


def engine_consensus(
    signals: list[dict],
    *,
    weights: dict[str, float],
    regime_state: str = "range",
    sentiment_bias: float = 0.0,
    onchain_bias: float = 0.0,
    macro_bias: float = 0.0,
    ttl_seconds: float = 3600.0,
    base_threshold: float = 0.45,
    max_kelly: float = 0.20,
    divergence_threshold: float = 0.55,
    nudge_weight: float = 0.10,
) -> dict:
    """Fuse per-engine directional signals into an executable consensus.

    Parameters
    ----------
    signals : list[dict]
        Each: ``{engine, direction, score(-1..1), confidence(0..1), promoted(bool),
        age_seconds(float)}``.
    weights : dict[str, float]
        Per-engine base/dynamic weight.
    regime_state : str
        "trend" | "range" | "crisis" (advisory — adjusts threshold + scales
        weights, does not hard-block except crisis position shrink).
    sentiment_bias, onchain_bias : float
        Biases in [-1, 1] blended in at `nudge_weight` each.
    ttl_seconds : float
        Linear time-decay horizon: decay = max(0, 1 - age/ttl).
    base_threshold : float
        Base |score| needed to execute (regime-adjusted).
    max_kelly : float
        Half-Kelly position cap.
    divergence_threshold : float
        Min agreement ratio among live engines to allow execution.
    nudge_weight : float
        Blend weight for sentiment/on-chain nudges.

    Returns
    -------
    dict
        ``{final_direction, consensus_score, live_score, observe_score,
        agreement_ratio, is_divergent, kelly_position, should_execute,
        effective_threshold, n_promoted, n_total, contributions}``.
    """
    from oprim import clip_with_warning

    thr_adj, weight_scale = _REGIME_ADJ.get(regime_state, (0.0, 1.0))

    contributions = []
    live_num = live_den = 0.0
    obs_num = obs_den = 0.0
    for s in signals:
        w = weights.get(s["engine"], 1.0) * weight_scale
        decay = max(0.0, 1.0 - float(s.get("age_seconds", 0.0)) / ttl_seconds)
        eff = w * float(s.get("confidence", 1.0)) * decay
        sc = float(s["score"])
        obs_num += sc * eff
        obs_den += eff
        promoted = bool(s.get("promoted", False))
        if promoted:
            live_num += sc * eff
            live_den += eff
        contributions.append(
            {"engine": s["engine"], "score": sc, "eff_weight": eff, "promoted": promoted}
        )

    live_score = (live_num / live_den) if live_den > 0 else 0.0
    observe_score = (obs_num / obs_den) if obs_den > 0 else 0.0

    # sentiment / on-chain nudge on the live score, then bound to [-1,1]
    nudged = (
        live_score
        + nudge_weight * sentiment_bias
        + nudge_weight * onchain_bias
        + nudge_weight * macro_bias
    )
    consensus_score = float(clip_with_warning(nudged, -1.0, 1.0))

    # divergence among live (promoted) engines
    live = [c for c in contributions if c["promoted"] and c["eff_weight"] > 0]
    non_neutral = [c for c in live if c["score"] != 0]
    dom = 1.0 if consensus_score >= 0 else -1.0
    agreeing = sum(1 for c in non_neutral if (c["score"] > 0) == (dom > 0))
    agreement_ratio = (agreeing / len(non_neutral)) if non_neutral else 1.0
    is_divergent = agreement_ratio < divergence_threshold

    effective_threshold = base_threshold + thr_adj
    kelly = min(abs(consensus_score) * 0.5, max_kelly)
    if regime_state == "crisis":
        kelly *= 0.1

    final_direction = (
        "long" if consensus_score > 0 else ("short" if consensus_score < 0 else "neutral")
    )
    should_execute = (
        final_direction != "neutral"
        and not is_divergent
        and abs(consensus_score) >= effective_threshold
        and len(live) > 0
    )

    return {
        "final_direction": final_direction,
        "consensus_score": consensus_score,
        "live_score": live_score,
        "observe_score": observe_score,
        "agreement_ratio": agreement_ratio,
        "is_divergent": is_divergent,
        "kelly_position": kelly,
        "should_execute": should_execute,
        "effective_threshold": effective_threshold,
        "n_promoted": len(live),
        "n_total": len(signals),
        "contributions": contributions,
    }
