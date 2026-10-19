"""Multi-indicator technical-analysis directional signal.

Composites used:
    1. oprim.ema             — trend (fast vs slow crossover).
    2. oprim.macd            — momentum (histogram sign).
    3. oprim.rsi_normalized  — overbought/oversold mean-reversion vote.
    4. oprim.bollinger_bands — band-position mean-reversion vote.
    5. oprim.linear_slope    — recent-trend direction/strength.

Extraction source: helixa services/tradingview-engine (homegrown multi-TF TA on
pandas indicators). Re-expressed as a pure, single-series directional scorer;
multi-timeframe alignment is done by the caller running this per timeframe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ta_multi_indicator_signal(
    closes: pd.Series | np.ndarray | list,
    *,
    ema_fast: int = 12,
    ema_slow: int = 26,
    rsi_period: int = 14,
    boll_window: int = 20,
    slope_window: int = 20,
    rsi_overbought: float = 0.70,
    rsi_oversold: float = 0.30,
) -> dict:
    """Blend 5 technical indicators into a directional score in [-1, 1].

    Votes (each in {-1, 0, +1}), then score = mean of non-null votes:
      - **trend**   ema_fast > ema_slow -> +1 else -1.
      - **momentum** macd histogram sign.
      - **slope**   sign of normalized linear regression slope over
        `slope_window`.
      - **rsi**     mean-reversion: rsi >= overbought -> -1 (fade), <= oversold
        -> +1, else 0.
      - **bollinger** close above upper band -> -1, below lower -> +1, else 0.

    Parameters
    ----------
    closes : array-like
        Close prices (chronological).
    ema_fast, ema_slow, rsi_period, boll_window, slope_window : int
        Indicator windows.
    rsi_overbought, rsi_oversold : float
        rsi_normalized thresholds (rsi_normalized is in [0, 1]).

    Returns
    -------
    dict
        ``{"direction": "long"|"short"|"neutral", "score": float,
        "confidence": float, "votes": {...}}`` — score in [-1,1], confidence in
        [0,1] = agreement magnitude.

    Raises
    ------
    ValueError
        If fewer than ``ema_slow + 5`` bars are supplied.
    """
    from oprim import bollinger_bands, ema, linear_slope, macd, rsi_normalized

    c = np.asarray(closes, dtype=float)
    if len(c) < ema_slow + 5:
        raise ValueError(f"need >= {ema_slow + 5} bars, got {len(c)}")

    votes: dict[str, float] = {}

    ef = np.asarray(ema(c, ema_fast))
    es = np.asarray(ema(c, ema_slow))
    votes["trend"] = 1.0 if ef[-1] > es[-1] else -1.0

    hist = np.asarray(macd(c)["histogram"])
    votes["momentum"] = 1.0 if hist[-1] > 0 else -1.0

    # NB: oprim.linear_slope returns the ABSOLUTE slope magnitude (direction-less),
    # so its size gates confidence, not direction; the sign comes from the net
    # price change over the window.
    slope_mag = linear_slope(c[-slope_window:], normalize=True)
    delta = c[-1] - c[-slope_window]
    votes["slope"] = (1.0 if delta > 0 else -1.0) if slope_mag > 0 and delta != 0 else 0.0

    rsi = float(np.asarray(rsi_normalized(c, period=rsi_period))[-1])
    votes["rsi"] = -1.0 if rsi >= rsi_overbought else (1.0 if rsi <= rsi_oversold else 0.0)

    bb = bollinger_bands(c, window=boll_window)
    upper = float(np.asarray(bb["upper"])[-1])
    lower = float(np.asarray(bb["lower"])[-1])
    votes["bollinger"] = -1.0 if c[-1] > upper else (1.0 if c[-1] < lower else 0.0)

    score = float(np.mean(list(votes.values())))
    direction = "long" if score > 0 else ("short" if score < 0 else "neutral")

    return {
        "direction": direction,
        "score": score,
        "confidence": abs(score),
        "votes": votes,
    }
