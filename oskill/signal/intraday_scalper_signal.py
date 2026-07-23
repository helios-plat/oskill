"""Intraday scalper directional signal — ADX dual-mode (breakout vs mean-reversion).

Composites used:
    1. oprim.adx             — regime discriminator (hysteresis enter/exit).
    2. oprim.bollinger_bands — breakout bands / mean-reversion edges.
    3. oprim.rsi_normalized  — overbought/oversold trigger in ranging mode.

Extraction source: helixa services/nautilus-trader/strategies/intraday_scalper_v2
(Bollinger(20) + RSI + ADX(14) dual-mode with ADX hysteresis enter 22 / exit 18 on
5m bars), re-expressed as a pure directional scorer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def intraday_scalper_signal(
    closes: pd.Series | np.ndarray | list,
    highs: pd.Series | np.ndarray | list,
    lows: pd.Series | np.ndarray | list,
    *,
    bb_window: int = 20,
    rsi_period: int = 14,
    adx_period: int = 14,
    adx_enter: float = 22.0,
    rsi_overbought: float = 0.70,
    rsi_oversold: float = 0.30,
) -> dict:
    """Dual-mode 5m scalper: breakout when trending, mean-reversion when ranging.

    - **breakout mode** (ADX >= `adx_enter`): close above BB upper -> long, below
      BB lower -> short (ride the break).
    - **mean-reversion mode** (ADX < `adx_enter`): RSI <= oversold at/near BB
      lower -> long (buy the dip); RSI >= overbought at/near BB upper -> short
      (fade the spike).

    Returns
    -------
    dict
        ``{"direction","score","confidence","mode","adx","votes"}``.

    Raises
    ------
    ValueError
        If fewer than ``2*adx_period + 1`` bars are supplied.
    """
    from oprim import adx, bollinger_bands, rsi_normalized

    c = np.asarray(closes, dtype=float)
    h = np.asarray(highs, dtype=float)
    lo = np.asarray(lows, dtype=float)
    need = max(2 * adx_period + 1, bb_window + 2, rsi_period + 2)
    if len(c) < need:
        raise ValueError(f"need >= {need} bars, got {len(c)}")

    adx_val = adx(h, lo, c, period=adx_period)
    bb = bollinger_bands(c, window=bb_window)
    upper = float(np.asarray(bb["upper"])[-1])
    lower = float(np.asarray(bb["lower"])[-1])
    rsi = float(np.asarray(rsi_normalized(c, period=rsi_period))[-1])
    price = float(c[-1])

    votes = {"adx": adx_val, "rsi": rsi, "bb_upper": upper, "bb_lower": lower}

    if adx_val >= adx_enter:
        mode = "breakout"
        if price > upper:
            direction = "long"
        elif price < lower:
            direction = "short"
        else:
            direction = "neutral"
    else:
        mode = "mean_reversion"
        if rsi <= rsi_oversold and price <= lower:
            direction = "long"
        elif rsi >= rsi_overbought and price >= upper:
            direction = "short"
        else:
            direction = "neutral"

    # confidence: breakout scales with ADX; mean-reversion scales with RSI extremity
    if mode == "breakout":
        conf = min(1.0, adx_val / 50.0)
    else:
        conf = min(1.0, abs(rsi - 0.5) * 2)
    score = conf if direction == "long" else (-conf if direction == "short" else 0.0)
    return {
        "direction": direction,
        "score": score,
        "confidence": abs(score),
        "mode": mode,
        "adx": adx_val,
        "votes": votes,
    }
