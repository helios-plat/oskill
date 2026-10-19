"""Deterministic market-regime classification (crisis / trend / range).

Composites used:
    1. oprim.percentile_rank — robust rank of current realized vol vs history.
    2. oprim.zscore_normalize — standardize momentum / autocorrelation features.

A threshold-rule alternative to a Gaussian HMM, using the SAME feature basis
(realized vol / momentum / lag-1 autocorrelation) as helixa's regime-detector.
Preferred over the HMM path in helivex because (a) helivex's own research found
HMM market regimes have no out-of-sample persistence (11/11 FAIL, commit
646dc71), and (b) it needs no hmmlearn dependency. The HMM variant remains
available as `oskill.regime.market_regime_hmm` for environments that install it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_regime_deterministic(
    closes: pd.Series | np.ndarray | list,
    *,
    vol_window: int = 60,
    autocorr_window: int = 30,
    momentum_window: int = 120,
    vol_pctl_window: int = 500,
    crisis_vol_pctl: float = 0.85,
    trend_momentum_z: float = 0.5,
    trend_autocorr_z: float = 0.0,
) -> dict:
    """Classify the current market regime from a price series via threshold rules.

    Rule order (first match wins):
      - **crisis** — current realized vol at/above `crisis_vol_pctl` percentile
        of its trailing `vol_pctl_window` history.
      - **trend**  — not crisis, and standardized momentum >= `trend_momentum_z`
        AND standardized lag-1 autocorrelation >= `trend_autocorr_z`.
      - **range**  — otherwise (low vol, mean-reverting).

    Parameters
    ----------
    closes : array-like
        Close-price series (chronological).
    vol_window, autocorr_window, momentum_window : int
        Rolling windows for the three features.
    vol_pctl_window : int
        Trailing window for the crisis volatility percentile.
    crisis_vol_pctl : float
        Volatility percentile (0..1) at/above which the regime is crisis.
    trend_momentum_z, trend_autocorr_z : float
        Standardized-feature thresholds distinguishing trend from range.

    Returns
    -------
    dict
        ``{"state": str, "confidence": float, "features": {...},
        "rows_used": int}`` — confidence in [0,1] reflects how decisively the
        binding threshold is crossed.

    Raises
    ------
    ValueError
        If fewer usable bars remain than `momentum_window + 5` after feature
        construction.
    """
    from oprim import percentile_rank, zscore_normalize

    s = pd.Series(np.asarray(closes, dtype=float)).reset_index(drop=True)
    rets = s.pct_change()

    vol = rets.rolling(vol_window).std()
    autocorr = rets.rolling(autocorr_window).apply(
        lambda w: pd.Series(w).autocorr(lag=1), raw=False
    )
    momentum = rets.rolling(momentum_window).sum().abs()

    feats = pd.DataFrame({"vol": vol, "autocorr": autocorr, "momentum": momentum})
    feats = feats.dropna().reset_index(drop=True)
    if len(feats) < momentum_window + 5:
        raise ValueError(
            f"insufficient bars after feature construction: {len(feats)} "
            f"(need >= {momentum_window + 5})"
        )

    # crisis test: current vol's expanding/rolling percentile
    vol_pctl_series = percentile_rank(
        feats["vol"], window=min(vol_pctl_window, len(feats)), method="rolling"
    )
    cur_vol_pctl = float(vol_pctl_series.iloc[-1])

    # trend/range test: standardized momentum + autocorrelation, current value
    z = zscore_normalize(feats[["momentum", "autocorr"]], window=None).fillna(0.0)
    cur_mom_z = float(z["momentum"].iloc[-1])
    cur_ac_z = float(z["autocorr"].iloc[-1])

    if cur_vol_pctl >= crisis_vol_pctl:
        state = "crisis"
        # confidence: how far past the crisis threshold, scaled to [0,1]
        confidence = float(
            np.clip((cur_vol_pctl - crisis_vol_pctl) / (1.0 - crisis_vol_pctl), 0, 1)
        )
    elif cur_mom_z >= trend_momentum_z and cur_ac_z >= trend_autocorr_z:
        state = "trend"
        confidence = float(np.clip(min(cur_mom_z, cur_ac_z + 1.0) / 2.0, 0, 1))
    else:
        state = "range"
        # decisive range = low vol percentile + weak momentum
        confidence = float(
            np.clip((crisis_vol_pctl - cur_vol_pctl) + (0.5 - abs(cur_mom_z)) / 2, 0, 1)
        )

    return {
        "state": state,
        "confidence": confidence,
        "features": {
            "vol_percentile": cur_vol_pctl,
            "momentum_z": cur_mom_z,
            "autocorr_z": cur_ac_z,
        },
        "rows_used": int(len(feats)),
    }
