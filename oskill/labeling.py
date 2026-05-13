"""Triple Barrier labeling method."""

from __future__ import annotations

import numpy as np


def triple_barrier_label(
    prices: np.ndarray,
    take_profit: float = 0.015,
    stop_loss: float = 0.010,
    horizon: int = 30,
) -> np.ndarray:
    """Triple Barrier labeling (de Prado 2018).

    For each time step t, look forward up to `horizon` bars:
    - If price first hits +take_profit → label = 1 (long)
    - If price first hits -stop_loss → label = -1 (short)
    - If neither hit within horizon → label = 0 (neutral)

    Parameters
    ----------
    prices : np.ndarray
        Close price array.
    take_profit : float
        Upper barrier as fraction of entry price (e.g. 0.015 = 1.5%).
    stop_loss : float
        Lower barrier as fraction of entry price (e.g. 0.010 = 1.0%).
    horizon : int
        Maximum holding period in bars.

    Returns
    -------
    np.ndarray
        Integer labels array, same length as prices. Last `horizon` values are 0.

    References
    ----------
    .. [1] López de Prado, M. (2018). Advances in Financial Machine Learning, Ch. 3.
    .. [2] Extraction source: Helixa services/qlib-v2/src/label_engine.py:TripleBarrierLabeler.label()
    """
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    labels = np.zeros(n, dtype=int)

    for i in range(n - horizon):
        entry = prices[i]
        if entry <= 0:
            continue
        future_rets = (prices[i + 1: i + 1 + horizon] - entry) / entry
        hit_up = np.where(future_rets >= take_profit)[0]
        hit_down = np.where(future_rets <= -stop_loss)[0]
        first_up = hit_up[0] if len(hit_up) > 0 else horizon + 1
        first_down = hit_down[0] if len(hit_down) > 0 else horizon + 1

        if first_up < first_down:
            labels[i] = 1
        elif first_down < first_up:
            labels[i] = -1

    return labels
