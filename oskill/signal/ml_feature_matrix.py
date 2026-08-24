"""ML feature matrix for a price series (alpha-style factors).

Composites used:
    1. oprim.rsi_normalized — normalized RSI feature.
    2. oprim.macd           — MACD line / signal / histogram features.

Extraction source: helixa services/qlib-v2/src/features.py (Alpha158-style set).
Close-only mode keeps the original compact factor set; passing the full OHLCV
arrays adds the remaining helixa factors (volume, VWAP deviation, price-volume
correlation, Bollinger, candle shape, high/low breaks, ATR, efficiency ratio,
multi-period RSI) so the two engines are feature-comparable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _sdiv(a, b, fill: float = 0.0) -> np.ndarray:
    """Element-wise a/b with 0-denominator → fill (helixa _safe_div)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b != 0, a / b, fill)


def ml_feature_matrix(
    closes: pd.Series | np.ndarray | list,
    *,
    opens: pd.Series | np.ndarray | list | None = None,
    highs: pd.Series | np.ndarray | list | None = None,
    lows: pd.Series | np.ndarray | list | None = None,
    volumes: pd.Series | np.ndarray | list | None = None,
    return_periods: tuple[int, ...] = (1, 3, 5, 10, 20),
    vol_windows: tuple[int, ...] = (5, 10, 20),
    momentum_windows: tuple[int, ...] = (5, 10, 20),
    rsi_period: int = 14,
) -> pd.DataFrame:
    """Build a per-bar feature matrix from a close-price series.

    Close-only features: multi-horizon returns, rolling return volatility,
    momentum (close / close.shift - 1), normalized RSI, and MACD
    line/signal/histogram (each normalized by price).

    If `opens`, `highs`, `lows`, `volumes` are ALL provided (same length as
    `closes`), the helixa Alpha158 OHLCV factors are appended: volume ratio/std,
    VWAP deviation, price-volume correlation, RSI(6/24), Bollinger
    upper/lower/width, candle body/shadows, high/low breaks + range position,
    ATR ratio, and Kaufman-style efficiency ratio. Passing only some of the
    four raises ValueError (a silently degraded feature set would make gate
    results incomparable).

    Rows with any NaN (leading warm-up) are dropped.

    Returns
    -------
    pd.DataFrame
        Feature matrix indexed 0..N-1 over the surviving bars; a ``_bar_index``
        column preserves each row's original position in `closes` so labels can
        be aligned.

    Raises
    ------
    ValueError
        If fewer than ``max(all windows) + 5`` bars are supplied, if only some
        of opens/highs/lows/volumes are given, or if their lengths differ from
        `closes`.
    """
    from oprim import macd, rsi_normalized

    c = pd.Series(np.asarray(closes, dtype=float)).reset_index(drop=True)
    need = max((*return_periods, *vol_windows, *momentum_windows, rsi_period)) + 5
    if len(c) < need:
        raise ValueError(f"need >= {need} bars, got {len(c)}")

    ohlcv_args = (opens, highs, lows, volumes)
    n_given = sum(a is not None for a in ohlcv_args)
    if n_given not in (0, 4):
        raise ValueError("opens/highs/lows/volumes must be given all together or not at all")
    full = n_given == 4

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

    if full:
        o = pd.Series(np.asarray(opens, dtype=float)).reset_index(drop=True)
        h = pd.Series(np.asarray(highs, dtype=float)).reset_index(drop=True)
        low = pd.Series(np.asarray(lows, dtype=float)).reset_index(drop=True)
        v = pd.Series(np.asarray(volumes, dtype=float)).reset_index(drop=True)
        for name, s in (("opens", o), ("highs", h), ("lows", low), ("volumes", v)):
            if len(s) != len(c):
                raise ValueError(f"{name} length {len(s)} != closes length {len(c)}")

        # 成交量因子
        for w in (5, 10, 20):
            vma = v.rolling(w).mean()
            feats[f"vol_ratio_{w}"] = pd.Series(_sdiv(v, vma))
            feats[f"vol_std_{w}"] = pd.Series(_sdiv(v.rolling(w).std(), vma))

        # VWAP 偏离度
        typical = (h + low + c) / 3
        for w in (5, 10, 20):
            vwap = (typical * v).rolling(w).sum() / v.rolling(w).sum()
            feats[f"vwap_dev_{w}"] = pd.Series(_sdiv(c - vwap, vwap))

        # 量价相关性
        for w in (10, 20):
            feats[f"pv_corr_{w}"] = rets.rolling(w).corr(v.pct_change())

        # 多周期 RSI(helixa 6/12/24;12≈现有 rsi_period 保留 6/24)
        for p in (6, 24):
            feats[f"rsi_{p}"] = pd.Series(np.asarray(rsi_normalized(c.to_numpy(), period=p)))

        # 布林带
        for w in (10, 20):
            ma = c.rolling(w).mean()
            std = c.rolling(w).std()
            feats[f"boll_upper_{w}"] = pd.Series(_sdiv(h - (ma + 2 * std), c))
            feats[f"boll_lower_{w}"] = pd.Series(_sdiv(low - (ma - 2 * std), c))
            feats[f"boll_width_{w}"] = pd.Series(_sdiv(4 * std, ma))

        # K线形态
        feats["body_size"] = pd.Series(_sdiv((c - o).abs(), c))
        feats["upper_shadow"] = pd.Series(_sdiv(h - c.clip(lower=o), c))
        feats["lower_shadow"] = pd.Series(_sdiv(c.clip(upper=o) - low, c))

        # 高低价突破 + 区间位置
        for w in (5, 10, 20):
            rh = h.rolling(w).max()
            rl = low.rolling(w).min()
            feats[f"high_break_{w}"] = (h >= rh).astype(float)
            feats[f"low_break_{w}"] = (low <= rl).astype(float)
            feats[f"position_{w}"] = pd.Series(_sdiv(c - rl, (rh - rl) + 1e-9))

        # ATR(占价格比例)
        tr = pd.concat([h - low, (h - c.shift(1)).abs(), (low - c.shift(1)).abs()], axis=1).max(
            axis=1
        )
        for w in (5, 10, 14):
            feats[f"atr_{w}"] = pd.Series(_sdiv(tr.rolling(w).mean(), c))

        # 价格效率比(趋势强度)
        for w in (10, 20):
            net_move = (c - c.shift(w)).abs()
            total_move = c.diff().abs().rolling(w).sum()
            feats[f"efficiency_{w}"] = pd.Series(_sdiv(net_move, total_move + 1e-9))

    df = pd.DataFrame(feats).replace([np.inf, -np.inf], np.nan)
    df["_bar_index"] = np.arange(len(df))
    df = df.dropna().reset_index(drop=True)
    return df
