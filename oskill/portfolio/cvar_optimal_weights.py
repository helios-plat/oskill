"""CVaR-optimal portfolio weights with equal-weight fallback.

Composites used:
    1. oprim.risk.cvar_portfolio_optimize
    2. oprim.risk.cvar
"""

from __future__ import annotations

import pandas as pd


def cvar_optimal_weights(
    returns: pd.DataFrame,
    *,
    alpha: float = 0.05,
    min_obs: int = 50,
    max_weight: float = 0.5,
    min_weight: float = 0.15,
) -> dict:
    """CVaR-Sharpe optimal portfolio weights, falling back to equal-weight.

    Falls back to equal (1/N) weighting when there are fewer than 2 assets,
    fewer than `min_obs` time-aligned observations, or the optimizer fails
    to converge for any reason — mirroring the production behavior this was
    extracted from (helixa's portfolio-optimizer), which never lets an
    optimization failure block a portfolio-weight cycle.

    Parameters
    ----------
    returns : pd.DataFrame
        Per-asset return series, columns = symbols. May contain NaNs; rows
        with any NaN are dropped before optimization (inner-join semantics
        across assets, matching how the source returns are normally built
        from time-aligned close-price pct_change series).
    alpha : float
        CVaR significance level passed through to the optimizer and to the
        diagnostic CVaR computed on the resulting weighted-return series.
    min_obs : int
        Minimum aligned observations required to attempt optimization.
    max_weight : float
        Per-asset weight cap in (0, 1], default 0.5 — forces the optimizer to
        hold at least two assets meaningfully instead of collapsing to
        near-100% in whichever had the best trailing Sharpe/CVaR over the
        sample (see oprim.risk.cvar_portfolio_optimize's max_weight docstring).
    min_weight : float
        Per-asset weight floor, default 0.15 — a cap alone still lets the
        optimizer starve one asset to ~0 while two others sit at the cap; a
        floor forces every asset to hold at least this much. If
        `len(symbols) * min_weight > 1` the constraint is infeasible and the
        optimizer failure is caught by the existing equal-weight fallback below
        (same as any other convergence failure).

    Returns
    -------
    dict
        ``{"weights": {symbol: float}, "method": "cvar_sharpe"|"equal_weight_fallback",
        "fallback_reason": str|None, "portfolio_cvar_95": float|None, "n_obs": int,
        "symbols": list[str]}``
    """
    from oprim.risk.cvar import cvar
    from oprim.risk.cvar_portfolio_optimize import cvar_portfolio_optimize

    symbols = list(returns.columns)
    clean = returns.dropna()
    n_obs = len(clean)

    def _equal_weight(reason: str) -> dict:
        n = len(symbols)
        weights = {s: (1.0 / n if n else 0.0) for s in symbols}
        return {
            "weights": weights,
            "method": "equal_weight_fallback",
            "fallback_reason": reason,
            "portfolio_cvar_95": None,
            "n_obs": n_obs,
            "symbols": symbols,
        }

    if len(symbols) < 2:
        return _equal_weight(f"need >= 2 symbols, got {len(symbols)}")
    if n_obs < min_obs:
        return _equal_weight(f"need >= {min_obs} obs, got {n_obs}")

    try:
        result = cvar_portfolio_optimize(
            clean, alpha=alpha, max_weight=max_weight, min_weight=min_weight
        )
        weights = result["weights"]
    except Exception as e:  # noqa: BLE001 — any optimizer failure must fall back
        return _equal_weight(f"optimizer failed: {e}")

    weighted_returns = clean[list(weights.keys())].dot(pd.Series(weights)[list(weights.keys())])
    portfolio_cvar_95 = cvar(weighted_returns.to_numpy(), alpha=alpha, method="historical")

    return {
        "weights": weights,
        "method": "cvar_sharpe",
        "fallback_reason": None,
        "portfolio_cvar_95": portfolio_cvar_95,
        "n_obs": n_obs,
        "symbols": symbols,
    }
