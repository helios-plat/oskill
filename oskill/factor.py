"""Factor Information Coefficient analysis."""

from __future__ import annotations

import numpy as np


def factor_ic(
    factor: np.ndarray,
    forward_return: np.ndarray,
    window: int = 50,
    step: int = 20,
) -> dict:
    """Rolling Spearman rank IC and ICIR for a single factor.

    Parameters
    ----------
    factor : np.ndarray
        Factor values (same length as forward_return).
    forward_return : np.ndarray
        Forward returns aligned with factor.
    window : int
        Rolling window size for IC calculation.
    step : int
        Step size between windows.

    Returns
    -------
    dict
        "ic_mean": mean IC, "ic_std": std IC, "icir": IC/std,
        "positive_ratio": fraction of positive IC windows,
        "n_windows": number of windows computed.

    References
    ----------
    .. [1] Qian, E. et al. (2007). Quantitative Equity Portfolio Management.
    .. [2] Extraction source: Helixa services/factor-analyzer/src/main.py:compute_ic()
    """
    factor = np.asarray(factor, dtype=float)
    forward_return = np.asarray(forward_return, dtype=float)

    # Remove NaN pairs
    mask = ~(np.isnan(factor) | np.isnan(forward_return))
    f = factor[mask]
    r = forward_return[mask]

    if len(f) < window:
        return {"ic_mean": 0.0, "ic_std": 0.0, "icir": 0.0, "positive_ratio": 0.0, "n_windows": 0}

    ics = []
    for i in range(0, len(f) - window, step):
        f_chunk = f[i: i + window]
        r_chunk = r[i: i + window]
        # Spearman rank correlation
        f_rank = _rankdata(f_chunk)
        r_rank = _rankdata(r_chunk)
        ic = float(np.corrcoef(f_rank, r_rank)[0, 1])
        if not np.isnan(ic):
            ics.append(ic)

    if not ics:
        return {"ic_mean": 0.0, "ic_std": 0.0, "icir": 0.0, "positive_ratio": 0.0, "n_windows": 0}

    ic_arr = np.array(ics)
    mean_ic = float(ic_arr.mean())
    std_ic = float(ic_arr.std())
    icir = mean_ic / std_ic if std_ic > 1e-10 else 0.0

    return {
        "ic_mean": mean_ic,
        "ic_std": std_ic,
        "icir": icir,
        "positive_ratio": float((ic_arr > 0).mean()),
        "n_windows": len(ics),
    }


def _rankdata(x: np.ndarray) -> np.ndarray:
    """Simple rank (average ties)."""
    order = x.argsort()
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(x) + 1, dtype=float)
    return ranks
