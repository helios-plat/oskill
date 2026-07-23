"""Tests for oskill.portfolio.cvar_optimal_weights."""

import numpy as np
import pandas as pd
import pytest

from oskill.portfolio.cvar_optimal_weights import cvar_optimal_weights


def _synthetic_returns(n_assets=3, n_obs=300, seed=42):
    rng = np.random.default_rng(seed)
    cols = [f"SYM{i}" for i in range(n_assets)]
    data = rng.normal(0.0003, 0.01, size=(n_obs, n_assets))
    return pd.DataFrame(data, columns=cols)


def test_happy_path_uses_cvar_sharpe():
    returns = _synthetic_returns()
    result = cvar_optimal_weights(returns)
    assert result["method"] == "cvar_sharpe"
    assert result["fallback_reason"] is None
    assert sum(result["weights"].values()) == pytest.approx(1.0, abs=1e-6)
    assert result["portfolio_cvar_95"] is not None
    assert result["n_obs"] == 300


def test_fewer_than_two_symbols_falls_back_to_equal_weight():
    returns = _synthetic_returns(n_assets=1)
    result = cvar_optimal_weights(returns)
    assert result["method"] == "equal_weight_fallback"
    assert "symbols" in result["fallback_reason"]
    assert result["weights"] == {"SYM0": 1.0}
    assert result["portfolio_cvar_95"] is None


def test_insufficient_observations_falls_back_to_equal_weight():
    returns = _synthetic_returns(n_obs=10)
    result = cvar_optimal_weights(returns, min_obs=50)
    assert result["method"] == "equal_weight_fallback"
    assert "obs" in result["fallback_reason"]
    assert sum(result["weights"].values()) == pytest.approx(1.0)
    for w in result["weights"].values():
        assert w == pytest.approx(1.0 / 3)


def test_nan_rows_dropped_before_min_obs_check():
    returns = _synthetic_returns(n_obs=60)
    returns.iloc[:20, 0] = float("nan")  # 20 rows now unusable after dropna
    result = cvar_optimal_weights(returns, min_obs=50)
    # 60 - 20 = 40 clean rows < 50 -> fallback
    assert result["method"] == "equal_weight_fallback"
    assert result["n_obs"] == 40


def test_all_symbols_present_in_weights():
    returns = _synthetic_returns(n_assets=5, seed=3)
    result = cvar_optimal_weights(returns)
    assert set(result["weights"].keys()) == set(returns.columns)
    assert result["symbols"] == list(returns.columns)
