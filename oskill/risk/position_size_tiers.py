"""Three-tier position-size clip: optimal-weight headroom, ATR cap, correlation clip.

Composites used:
    1. oprim.risk.atr_position_cap
    2. oprim.risk.net_exposure_clip
"""

from __future__ import annotations


def position_size_tiers(
    proposed_notional: float,
    *,
    optimal_weight: float,
    capital_usd: float,
    slippage_scale: float,
    current_position_usd: float,
    atr_pct: float,
    atr_risk_budget: float,
    atr_min_position: float,
    atr_max_position: float,
    correlated_positions: list[tuple[float, float]],
    max_net_exposure: float,
    min_trade_notional: float,
) -> dict:
    """Clip a proposed trade notional through three independent risk tiers.

    Tier 1 (optimal-weight headroom): ``optimal_max = optimal_weight * capital_usd
    * slippage_scale``; ``headroom = optimal_max - current_position_usd``.
    Tier 2 (ATR-adaptive cap): via `oprim.risk.atr_position_cap`, expressed in
    the same notional units as tier 1 (``cap_fraction * capital_usd``).
    Tier 3 (correlation net-exposure clip): via `oprim.risk.net_exposure_clip`,
    operating on notional-fraction-of-capital terms.

    Final size = min(tier1 headroom, tier2 cap, tier3 clip, proposed_notional),
    rejected outright if the result falls below `min_trade_notional`.

    Parameters
    ----------
    proposed_notional : float
        The trade size being requested, in USD notional.
    optimal_weight : float
        Target portfolio weight (0..1) for this instrument, e.g. from
        `oskill.portfolio.cvar_optimal_weights`.
    capital_usd : float
        Total capital base the weight is applied against.
    slippage_scale : float
        External scale factor in (0, 1], shrinking tier 1 headroom (e.g. from
        a slippage/liquidity monitor). Pass 1.0 if no such signal exists.
    current_position_usd : float
        Current notional already held in this instrument.
    atr_pct : float
        Average True Range normalized by price (ATR / close).
    atr_risk_budget, atr_min_position, atr_max_position : float
        Passed through to `oprim.risk.atr_position_cap` (position-fraction terms).
    correlated_positions : list[tuple[float, float]]
        ``[(other_position_fraction, correlation), ...]`` for tier 3.
    max_net_exposure : float
        Passed through to `oprim.risk.net_exposure_clip` (position-fraction terms).
    min_trade_notional : float
        Minimum notional below which the trade is rejected outright.

    Returns
    -------
    dict
        ``{"final_notional": float, "rejected": bool, "tiers": {...},
        "binding_tier": str, "reasons": list[str]}``
    """
    from oprim.risk.atr_position_cap import atr_position_cap
    from oprim.risk.net_exposure_clip import net_exposure_clip

    reasons: list[str] = []

    # Tier 1: optimal-weight headroom
    optimal_max = optimal_weight * capital_usd * slippage_scale
    tier1_headroom = optimal_max - current_position_usd
    if tier1_headroom <= 0:
        reasons.append(f"tier1: position already at/above optimal max ({optimal_max:.2f})")

    # Tier 2: ATR-adaptive cap (fraction -> notional)
    tier2_cap_fraction = atr_position_cap(
        atr_pct,
        risk_budget=atr_risk_budget,
        min_position=atr_min_position,
        max_position=atr_max_position,
    )
    tier2_atr_cap = tier2_cap_fraction * capital_usd

    # Tier 3: correlation net-exposure clip. net_exposure_clip() clips a specific
    # proposed value rather than reporting an independent cap, so probe it with a
    # sentinel far larger than any real trade to recover the true headroom cap
    # (comparable to tier1/tier2 as an independent bound in the min() below) —
    # this also avoids a spurious tie with `proposed` when tier 3 isn't binding.
    proposed_fraction = proposed_notional / capital_usd if capital_usd > 0 else 0.0
    cap_probe = net_exposure_clip(
        1e9,
        correlated_positions=correlated_positions,
        max_net_exposure=max_net_exposure,
    )
    tier3_cap_fraction = cap_probe["allowed_size"]
    tier3_corr_clip = tier3_cap_fraction * capital_usd

    clip_result = net_exposure_clip(
        proposed_fraction,
        correlated_positions=correlated_positions,
        max_net_exposure=max_net_exposure,
    )
    if clip_result["was_clipped"]:
        reasons.append(
            f"tier3: correlation net exposure clipped ({clip_result['net_exposure']:.4f} "
            f"vs max {max_net_exposure})"
        )

    candidates = {
        "tier1_headroom": max(0.0, tier1_headroom),
        "tier2_atr_cap": tier2_atr_cap,
        "tier3_corr_clip": max(0.0, tier3_corr_clip),
        "proposed": proposed_notional,
    }
    binding_tier = min(candidates, key=candidates.get)
    final_notional = candidates[binding_tier]

    rejected = final_notional < min_trade_notional
    if rejected:
        reasons.append(
            f"final notional {final_notional:.2f} below min_trade_notional {min_trade_notional}"
        )

    return {
        "final_notional": 0.0 if rejected else final_notional,
        "rejected": rejected,
        "tiers": {
            "tier1_headroom": candidates["tier1_headroom"],
            "tier2_atr_cap": candidates["tier2_atr_cap"],
            "tier3_corr_clip": candidates["tier3_corr_clip"],
        },
        "binding_tier": binding_tier,
        "reasons": reasons,
    }
