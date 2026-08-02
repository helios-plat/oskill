"""Market-regime classification via Gaussian HMM with semantic state labels.

Composites used:
    1. oprim.zscore_normalize — standardize the engineered features.
    2. oskill.hmm_regime_detect — fit/decode the Gaussian HMM (itself composing
       oprim.hmm_baum_welch + oprim.hmm_viterbi).

Extraction source: helixa project, services/regime-detector/src/detector.py
(3-state Gaussian HMM on realized-vol / price-autocorr / momentum features),
re-expressed as a pure, semantically-labelled function.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def market_regime_hmm(
    closes: pd.Series | np.ndarray | list,
    *,
    vol_window: int = 60,
    autocorr_window: int = 30,
    momentum_window: int = 120,
    n_states: int = 3,
    random_state: int | None = 42,
) -> dict:
    """Classify the current market regime (crisis / trend / range) from a price
    series via a Gaussian HMM over engineered features.

    Features (per bar, then whole-series Z-scored):
        f0 realized_vol  — rolling std of simple returns over `vol_window`.
        f1 price_autocorr — rolling lag-1 autocorrelation of returns over
           `autocorr_window`.
        f2 momentum      — |cumulative return| over `momentum_window`.

    Raw HMM states are mapped to semantic labels by their mean feature profile:
    the highest-mean-volatility state -> "crisis"; of the remaining two, the
    higher-mean-autocorrelation state -> "trend", the other -> "range". This
    matches helixa's labelling rule.

    Parameters
    ----------
    closes : array-like
        Close-price series (chronological).
    vol_window, autocorr_window, momentum_window : int
        Rolling windows for the three features.
    n_states : int
        Number of HMM states (3 for crisis/trend/range labelling).
    random_state : int | None
        Seed for HMM fit reproducibility.

    Returns
    -------
    dict
        ``{"state": str, "confidence": float, "raw_state": int,
        "state_map": {int: str}, "rows_used": int,
        "feature_means_by_state": {int: {"vol","autocorr","momentum"}}}``.

    Raises
    ------
    ValueError
        If fewer than `momentum_window + n_states` usable bars remain after
        feature construction, or `n_states != 3` (semantic labelling assumes 3).
    """
    from oprim import zscore_normalize
    from oskill.hmm_regime_detect import hmm_regime_detect

    if n_states != 3:
        raise ValueError("market_regime_hmm semantic labelling requires n_states=3")

    s = pd.Series(np.asarray(closes, dtype=float)).reset_index(drop=True)
    rets = s.pct_change()

    vol = rets.rolling(vol_window).std()
    autocorr = rets.rolling(autocorr_window).apply(
        lambda w: pd.Series(w).autocorr(lag=1), raw=False
    )
    momentum = rets.rolling(momentum_window).sum().abs()

    feats = pd.DataFrame({"vol": vol, "autocorr": autocorr, "momentum": momentum})
    feats = feats.dropna().reset_index(drop=True)

    if len(feats) < n_states + 5:
        raise ValueError(
            f"insufficient bars after feature construction: {len(feats)} "
            f"(need > {n_states + 5}; increase input length)"
        )

    # whole-series Z-score (window=None) so features are comparably scaled
    z = zscore_normalize(feats, window=None).fillna(0.0)

    result = hmm_regime_detect(z.to_numpy(), n_regimes=n_states, random_state=random_state)
    regimes = np.asarray(result["regimes"])
    raw_state = int(result["current_regime"])
    tm = np.asarray(result["transition_matrix"], dtype=float)

    # per-state mean feature profile (on the standardized features)
    means: dict[int, dict[str, float]] = {}
    for st in range(n_states):
        mask = regimes == st
        if mask.any():
            means[st] = {
                "vol": float(z["vol"].to_numpy()[mask].mean()),
                "autocorr": float(z["autocorr"].to_numpy()[mask].mean()),
                "momentum": float(z["momentum"].to_numpy()[mask].mean()),
            }
        else:
            means[st] = {"vol": -np.inf, "autocorr": 0.0, "momentum": 0.0}

    # label: highest vol -> crisis; of the rest, higher autocorr -> trend
    crisis_st = max(means, key=lambda k: means[k]["vol"])
    rest = [k for k in means if k != crisis_st]
    rest.sort(key=lambda k: means[k]["autocorr"], reverse=True)
    state_map = {crisis_st: "crisis", rest[0]: "trend", rest[1]: "range"}

    # confidence = current state's self-persistence probability
    confidence = float(np.clip(tm[raw_state][raw_state], 0.0, 1.0)) if tm.size else 0.0

    return {
        "state": state_map[raw_state],
        "confidence": confidence,
        "raw_state": raw_state,
        "state_map": state_map,
        "rows_used": int(len(feats)),
        "feature_means_by_state": means,
    }
