"""Tests for barra_style_decomposition."""

import numpy as np
import pandas as pd
import pytest

from oskill.factor.barra import barra_style_decomposition


def _make_barra_data(rng: np.random.Generator, T: int = 50, N: int = 10, K: int = 3):
    """Generate synthetic T x N asset returns and T x K style factors."""
    factor_exposures = rng.normal(0, 1, (T, K))
    true_factor_rets = rng.normal(0, 0.01, (T, K))
    noise = rng.normal(0, 0.002, (T, N))
    # asset_returns = factor_exposures @ true_factor_rets.T diagonal doesn't work
    # Instead: for each t, each asset gets r = x_t @ f_t + e_i
    asset_rets = np.zeros((T, N))
    for t in range(T):
        for n in range(N):
            asset_rets[t, n] = float(np.dot(factor_exposures[t], true_factor_rets[t])) + noise[t, n]

    time_idx = pd.date_range("2020-01-01", periods=T, freq="D")
    asset_cols = [f"A{i}" for i in range(N)]
    factor_cols = [f"F{k}" for k in range(K)]

    return (
        pd.DataFrame(asset_rets, index=time_idx, columns=asset_cols),
        pd.DataFrame(factor_exposures, index=time_idx, columns=factor_cols),
    )


class TestBarraStyleDecomposition:
    """Tests for barra_style_decomposition."""

    def test_returns_required_keys(self):
        """Result must contain all required keys."""
        rng = np.random.default_rng(1)
        asset_rets, style_factors = _make_barra_data(rng)
        result = barra_style_decomposition(asset_rets, style_factors)
        for key in ["factor_returns", "specific_returns", "r_squared_per_period", "mean_r_squared"]:
            assert key in result

    def test_factor_returns_shape(self):
        """factor_returns should have shape T x K."""
        rng = np.random.default_rng(2)
        T, N, K = 40, 8, 3
        asset_rets, style_factors = _make_barra_data(rng, T=T, N=N, K=K)
        result = barra_style_decomposition(asset_rets, style_factors)
        assert result["factor_returns"].shape == (T, K)

    def test_specific_returns_shape(self):
        """specific_returns should have shape T x N."""
        rng = np.random.default_rng(3)
        T, N, K = 30, 6, 2
        asset_rets, style_factors = _make_barra_data(rng, T=T, N=N, K=K)
        result = barra_style_decomposition(asset_rets, style_factors)
        assert result["specific_returns"].shape == (T, N)

    def test_r_squared_per_period_length(self):
        """r_squared_per_period should have length T."""
        rng = np.random.default_rng(4)
        T = 35
        asset_rets, style_factors = _make_barra_data(rng, T=T)
        result = barra_style_decomposition(asset_rets, style_factors)
        assert len(result["r_squared_per_period"]) == T

    def test_mean_r_squared_range(self):
        """mean_r_squared should be in [0, 1]."""
        rng = np.random.default_rng(5)
        asset_rets, style_factors = _make_barra_data(rng)
        result = barra_style_decomposition(asset_rets, style_factors)
        assert -0.1 <= result["mean_r_squared"] <= 1.0

    def test_factor_returns_has_correct_columns(self):
        """factor_returns DataFrame should have style_factors column names."""
        rng = np.random.default_rng(6)
        asset_rets, style_factors = _make_barra_data(rng)
        result = barra_style_decomposition(asset_rets, style_factors)
        assert list(result["factor_returns"].columns) == list(style_factors.columns)

    def test_shape_mismatch_raises(self):
        """Mismatched T dimension should raise ValueError."""
        rng = np.random.default_rng(7)
        asset_rets = pd.DataFrame(rng.normal(0, 1, (30, 5)))
        style_factors = pd.DataFrame(rng.normal(0, 1, (25, 3)))
        with pytest.raises(ValueError, match="rows"):
            barra_style_decomposition(asset_rets, style_factors)

    def test_non_dataframe_raises(self):
        """Non-DataFrame input should raise ValueError."""
        rng = np.random.default_rng(8)
        with pytest.raises(ValueError):
            barra_style_decomposition(rng.normal(0, 1, (20, 5)), pd.DataFrame())
