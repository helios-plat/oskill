"""Trend-follower directional signal (Donchian breakout + ADX + Chandelier).

Composites used:
    1. oprim.donchian_channel — breakout bands.
    2. oprim.adx             — trend-strength gate.
    3. oprim.chandelier_exit — trailing-stop exit level.

Extraction source: helixa services/nautilus-trader/strategies/trend_follower
(Donchian(20) + custom ADX + ChandelierExit + ATR-health on daily bars),
re-expressed as a pure directional scorer. Stateful execution (position/trailing
management) is left to the consuming node; this returns the entry decision + the
Chandelier stop level for the caller to manage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def trend_follower_signal(
    highs: pd.Series | np.ndarray | list,
    lows: pd.Series | np.ndarray | list,
    closes: pd.Series | np.ndarray | list,
    *,
    donchian_window: int = 20,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    chandelier_period: int = 22,
    chandelier_mult: float = 3.0,
) -> dict:
    """Donchian breakout gated by ADX trend strength, with a Chandelier stop.

    Entry only when ADX >= `adx_threshold` (a real trend is present):
      - close breaks above the prior Donchian upper -> long.
      - close breaks below the prior Donchian lower -> short.
      - otherwise neutral.
    Score = direction × min(1, ADX/50) so confidence scales with trend strength.

    Returns
    -------
    dict
        ``{"direction","score","confidence","adx","exit_level","votes"}`` —
        `exit_level` is the Chandelier long/short trailing stop for the side taken.

    Raises
    ------
    ValueError
        If fewer than ``2*adx_period + 1`` bars are supplied.
    """
    from oprim import adx, chandelier_exit, donchian_channel

    h = np.asarray(highs, dtype=float)
    lo = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    need = max(2 * adx_period + 1, donchian_window + 2, chandelier_period + 1)
    if len(c) < need:
        raise ValueError(f"need >= {need} bars, got {len(c)}")

    dc = donchian_channel(h, lo, window=donchian_window)
    upper = np.asarray(dc["upper"])
    lower = np.asarray(dc["lower"])
    adx_val = adx(h, lo, c, period=adx_period)
    ce = chandelier_exit(h, lo, c, period=chandelier_period, multiplier=chandelier_mult)

    # prior-bar bands (breakout confirmed on close crossing the PRIOR channel)
    prior_upper = float(upper[-2])
    prior_lower = float(lower[-2])
    price = float(c[-1])

    votes = {"adx": adx_val, "prior_upper": prior_upper, "prior_lower": prior_lower}
    if adx_val < adx_threshold:
        direction, exit_level = "neutral", None
    elif price > prior_upper:
        direction, exit_level = "long", float(np.asarray(ce["long_exit"])[-1])
    elif price < prior_lower:
        direction, exit_level = "short", float(np.asarray(ce["short_exit"])[-1])
    else:
        direction, exit_level = "neutral", None

    strength = min(1.0, adx_val / 50.0)
    score = strength if direction == "long" else (-strength if direction == "short" else 0.0)
    return {
        "direction": direction,
        "score": score,
        "confidence": abs(score),
        "adx": adx_val,
        "exit_level": exit_level,
        "votes": votes,
    }
