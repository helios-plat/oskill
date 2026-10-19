"""Compact ML feature matrix for a price series (alpha-style factors).

Composites used:
    1. oprim.rsi_normalized — normalized RSI feature.
    2. oprim.macd           — MACD line / signal / histogram features.

Extraction source: helixa services/qlib-v2/src/features.py (Alpha158-style set),
trimmed to a compact, dependency-light factor set suitable for helivex's shorter
history. Additional return/volatility/momentum features are computed inline.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ml_feature_matrix(
    closes: pd.Series | np.ndarray | list,
    *,
    return_periods: tuple[int, ...] = (1, 3, 5, 10, 20),
    vol_windows: tuple[int, ...] = (5, 10, 20),
    momentum_windows: tuple[int, ...] = (5, 10, 20),
    rsi_period: int = 14,
) -> pd.DataFrame:
    """Build a per-bar feature matrix from a close-price series.

    Features: multi-horizon returns, rolling return volatility, momentum
    (close / close.shift - 1), normalized RSI, and MACD line/signal/histogram
    (each normalized by price). Rows with any NaN (leading warm-up) are dropped.

    Parameters
    ----------
    closes : array-like
        Close prices (chronological).
    return_periods, vol_windows, momentum_windows : tuple[int, ...]
        Feature horizons.
    rsi_period : int
        RSI window.

    Returns
    -------
    pd.DataFrame
        Feature matrix indexed 0..N-1 over the surviving bars; a ``_bar_index``
        column preserves each row's original position in `closes` so labels can
        be aligned.

    Raises
    ------
    ValueError
        If fewer than ``max(all windows) + 5`` bars are supplied.
    """
    from oprim import macd, rsi_normalized

    c = pd.Series(np.asarray(closes, dtype=float)).reset_index(drop=True)
    need = max((*return_periods, *vol_windows, *momentum_windows, rsi_period)) + 5
    if len(c) < need:
        raise ValueError(f"need >= {need} bars, got {len(c)}")

    rets = c.pct_change()
    feats: dict[str, pd.Series] = {}
    for p in return_periods:
        feats[f"ret_{p}"] = c.pct_change(p)
    for w in vol_windows:
        feats[f"vol_{w}"] = rets.rolling(w).std()
    for w in momentum_windows:
        feats[f"mom_{w}"] = c / c.shift(w) - 1.0

    feats["rsi"] = pd.Series(np.asarray(rsi_normalized(c.to_numpy(), period=rsi_period)))
    m = macd(c.to_numpy())
    feats["macd"] = pd.Series(np.asarray(m["macd"])) / c
    feats["macd_signal"] = pd.Series(np.asarray(m["signal"])) / c
    feats["macd_hist"] = pd.Series(np.asarray(m["histogram"])) / c

    df = pd.DataFrame(feats)
    df["_bar_index"] = np.arange(len(df))
    df = df.dropna().reset_index(drop=True)
    return df
