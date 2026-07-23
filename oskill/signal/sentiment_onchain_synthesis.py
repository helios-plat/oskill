"""Synthesize tradeable bias from raw sentiment (FGI) and on-chain metrics.

Composites used:
    1. oprim.zscore_normalize — standardize on-chain metric levels vs history
       (when a history series is supplied).

Extraction source: helixa fear-greed-collector (WeightFactorCalculator) and
glassnode-collector (tanh signal synthesis). Kept as pure functions in the
signal layer — the raw data lives in iris md.sentiment / md.onchain (data layer).
"""

from __future__ import annotations

import numpy as np


def fgi_sentiment_bias(fgi: float) -> dict:
    """Map the crypto Fear & Greed Index (0..100) to a contrarian bias in [-1, 1].

    FGI is used contrarian: extreme fear (low FGI) is a bullish bias, extreme
    greed (high FGI) a bearish bias. ``bias = clip((50 - fgi) / 50, -1, 1)``.

    Parameters
    ----------
    fgi : float
        Fear & Greed Index, 0 (extreme fear) .. 100 (extreme greed).

    Returns
    -------
    dict
        ``{"bias": float, "classification": str}`` — bias > 0 bullish
        (contrarian on fear), < 0 bearish.

    Raises
    ------
    ValueError
        If `fgi` is outside [0, 100].
    """
    if not 0 <= fgi <= 100:
        raise ValueError(f"fgi must be in [0, 100], got {fgi}")
    bias = float(np.clip((50.0 - fgi) / 50.0, -1.0, 1.0))
    if fgi < 25:
        cls = "extreme_fear"
    elif fgi < 45:
        cls = "fear"
    elif fgi <= 55:
        cls = "neutral"
    elif fgi <= 75:
        cls = "greed"
    else:
        cls = "extreme_greed"
    return {"bias": bias, "classification": cls}


def news_sentiment_nudge(score: float, *, threshold: float = 0.15, cap: float = 0.15) -> float:
    """Contrarian nudge in [-cap, cap] from a keyword-scored news sentiment [0,1].

    Extraction source: helixa fear-greed-collector WeightFactorCalculator — news
    is treated as a minor confirming/contrarian adjustment on top of FGI, not an
    independent bias channel (very negative news nudges bullish, very positive
    news nudges bearish; mid-range news is a no-op). `threshold`/`cap` mirror
    helixa's 0.35/0.65 bands and small (~5%) adjustment magnitude, expressed here
    as a direct additive bias term rather than a multiplier on downstream weights.

    Parameters
    ----------
    score : float
        News sentiment in [0, 1] (0=very negative, 1=very positive, 0.5=neutral).
    threshold : float
        Distance from 0.5 the score must exceed to produce a nonzero nudge.
    cap : float
        Nudge magnitude at the extremes (linear ramp from `threshold` to 0.5±0.5).

    Returns
    -------
    float
        Bias nudge in [-cap, cap]; positive = bullish, negative = bearish.
    """
    dist = score - 0.5
    if abs(dist) <= threshold:
        return 0.0
    # ramp from `threshold` (nudge=0) to the extreme (nudge=±cap)
    span = 0.5 - threshold
    magnitude = cap * min(1.0, (abs(dist) - threshold) / span) if span > 0 else cap
    return -magnitude if dist > 0 else magnitude


def onchain_signal(
    *,
    flow_in: float,
    flow_out: float,
    mvrv: float,
    mvrv_neutral: float = 1.0,
    mvrv_scale: float = 0.5,
) -> dict:
    """Combine exchange flows + MVRV into an on-chain bias in [-1, 1] via tanh.

    - **Exchange flows**: net outflow (flow_out > flow_in, coins leaving
      exchanges = accumulation) is bullish. Normalized by total flow.
    - **MVRV**: above `mvrv_neutral` = overvalued (bearish), below = undervalued
      (bullish), scaled by `mvrv_scale`.

    ``signal = tanh(flow_component - mvrv_component)``.

    Parameters
    ----------
    flow_in, flow_out : float
        Exchange inflow / outflow in native units (>= 0).
    mvrv : float
        Market-Value-to-Realized-Value ratio.
    mvrv_neutral : float
        MVRV level treated as fair value.
    mvrv_scale : float
        Sensitivity of the MVRV component.

    Returns
    -------
    dict
        ``{"signal": float, "flow_component": float, "mvrv_component": float}``.
    """
    total_flow = abs(flow_in) + abs(flow_out)
    flow_component = ((flow_out - flow_in) / total_flow) if total_flow > 0 else 0.0
    mvrv_component = (mvrv - mvrv_neutral) * mvrv_scale
    signal = float(np.tanh(flow_component - mvrv_component))
    return {
        "signal": signal,
        "flow_component": float(flow_component),
        "mvrv_component": float(mvrv_component),
    }


def risk_on_off_signal(
    *,
    equity_returns: list[float],
    dxy_returns: list[float],
    equity_weight: float = 0.7,
    dxy_weight: float = 0.3,
) -> dict:
    """Macro risk-on/off bias in [-1, 1] from traditional-asset trends.

    Crypto co-moves with risk appetite: equities (QQQ/SPY) rising = risk-on =
    a bullish macro tailwind; the US dollar index (DXY) rising = risk-off =
    bearish. ``bias = tanh(equity_weight*mean(equity_returns) * 50
    - dxy_weight*mean(dxy_returns) * 50)`` (returns are small daily fractions,
    scaled before the tanh squash).

    Parameters
    ----------
    equity_returns : list[float]
        Recent equity-index returns (e.g. QQQ/SPY blended daily pct-change).
    dxy_returns : list[float]
        Recent US dollar index returns.
    equity_weight, dxy_weight : float
        Blend weights.

    Returns
    -------
    dict
        ``{"bias": float, "regime": "risk_on"|"risk_off"|"neutral"}``.
    """
    import numpy as _np

    eq = float(_np.mean(equity_returns)) if equity_returns else 0.0
    dx = float(_np.mean(dxy_returns)) if dxy_returns else 0.0
    bias = float(_np.tanh((equity_weight * eq - dxy_weight * dx) * 50.0))
    regime = "risk_on" if bias > 0.1 else ("risk_off" if bias < -0.1 else "neutral")
    return {"bias": bias, "regime": regime}
