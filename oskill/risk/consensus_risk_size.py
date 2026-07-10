"""Full risk pipeline for a consensus signal — crisis override + tiers + fee/edge.

Composites used:
    1. oskill.risk.position_size_tiers — the 3-tier (optimal / ATR / correlation) clip.
    2. oprim.fee_edge_filter — reject trades that can't clear round-trip fees.

Extraction source: helixa services/risk-engine/src/checks.py (the full call-time
pipeline: crisis-regime hard cap + 3-tier position clip + fee/edge filter), which
sat on top of position_manager. This is the bridge from a consensus decision to a
risk-approved tradeable size.
"""

from __future__ import annotations


def consensus_risk_size(
    *,
    direction: str,
    kelly_position: float,
    should_execute: bool,
    capital_usd: float,
    current_position_usd: float,
    atr_pct: float,
    regime_state: str,
    optimal_weight: float,
    slippage_scale: float = 1.0,
    atr_risk_budget: float = 0.01,
    atr_min_position: float = 0.005,
    atr_max_position: float = 0.20,
    correlated_positions: list[tuple[float, float]] | None = None,
    max_net_exposure: float = 0.25,
    min_trade_notional: float = 10.0,
    crisis_position_scale: float = 0.1,
    taker_fee_rate: float = 0.0005,
    edge_multiple: float = 1.5,
) -> dict:
    """Turn a consensus decision into a risk-approved notional (or a rejection).

    Pipeline (first blocker wins):
      1. gate — reject if `should_execute` is False or direction is neutral.
      2. crisis override — in a crisis regime, shrink the Kelly notional by
         `crisis_position_scale` (0.1) before sizing.
      3. 3-tier clip — via `oskill.risk.position_size_tiers`.
      4. fee/edge — via `oprim.fee_edge_filter`; reject if expected gross can't
         clear round-trip fees × `edge_multiple`.

    Parameters largely pass through to the composed oskill/oprim; see those.

    Returns
    -------
    dict
        ``{"approved": bool, "final_notional": float, "blocking_stage": str|None,
        "crisis_scaled": bool, "tiers": dict|None, "fee_edge": dict|None,
        "reasons": list[str]}``.
    """
    from oprim.risk.fee_edge_filter import fee_edge_filter
    from oskill.risk.position_size_tiers import position_size_tiers

    reasons: list[str] = []

    if not should_execute or direction == "neutral":
        return {
            "approved": False,
            "final_notional": 0.0,
            "blocking_stage": "gate",
            "crisis_scaled": False,
            "tiers": None,
            "fee_edge": None,
            "reasons": ["consensus not executable (should_execute=False or neutral)"],
        }

    proposed = kelly_position * capital_usd
    crisis_scaled = False
    if regime_state == "crisis":
        proposed *= crisis_position_scale
        crisis_scaled = True
        reasons.append(f"crisis regime: notional ×{crisis_position_scale}")

    tiers = position_size_tiers(
        proposed_notional=proposed,
        optimal_weight=optimal_weight,
        capital_usd=capital_usd,
        slippage_scale=slippage_scale,
        current_position_usd=current_position_usd,
        atr_pct=atr_pct or 1e-9,
        atr_risk_budget=atr_risk_budget,
        atr_min_position=atr_min_position,
        atr_max_position=atr_max_position,
        correlated_positions=correlated_positions or [],
        max_net_exposure=max_net_exposure,
        min_trade_notional=min_trade_notional,
    )
    reasons.extend(tiers["reasons"])
    if tiers["rejected"]:
        return {
            "approved": False,
            "final_notional": 0.0,
            "blocking_stage": "position_tiers",
            "crisis_scaled": crisis_scaled,
            "tiers": tiers,
            "fee_edge": None,
            "reasons": reasons,
        }

    sized = tiers["final_notional"]
    fe = fee_edge_filter(
        sized, atr_pct=atr_pct or 1e-9, taker_fee_rate=taker_fee_rate, edge_multiple=edge_multiple
    )
    if not fe["passes"]:
        reasons.append(
            f"fee/edge: expected gross {fe['expected_gross']:.2f} < min {fe['min_gross']:.2f}"
        )
        return {
            "approved": False,
            "final_notional": 0.0,
            "blocking_stage": "fee_edge",
            "crisis_scaled": crisis_scaled,
            "tiers": tiers,
            "fee_edge": fe,
            "reasons": reasons,
        }

    return {
        "approved": True,
        "final_notional": sized,
        "blocking_stage": None,
        "crisis_scaled": crisis_scaled,
        "tiers": tiers,
        "fee_edge": fe,
        "reasons": reasons,
    }
