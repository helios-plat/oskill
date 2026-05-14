"""Tests for factor_neutralization."""

import numpy as np
import pandas as pd
import pytest

from oskill.factor.neutralization import factor_neutralization


def _make_signal_exposures(rng: np.random.Generator, N: int = 50, K: int = 2):
    """Generate signal and factor exposures."""
    fe = pd.DataFrame(
        rng.normal(0, 1, (N, K)),
        columns=[f"F{k}" for k in range(K)],
    )
    # Signal that has known factor exposure
    betas = rng.normal(0, 1, K)
    signal = pd.Series(fe.values @ betas + rng.normal(0, 0.1, N))
    return signal, fe


class TestFactorNeutralization:
    """Tests for factor_neutralization."""

    def test_output_length_matches_input(self):
        """Neutralized signal should have same length as input."""
        rng = np.random.default_rng(1)
        signal, fe = _make_signal_exposures(rng)
        result = factor_neutralization(signal, fe)
        assert len(result) == len(signal)

    def test_regression_method_reduces_correlation(self):
        """After regression neutralization, signal should have near-zero correlation with factors."""
        rng = np.random.default_rng(42)
        N = 100
        fe = pd.DataFrame({"F0": rng.normal(0, 1, N)})
        signal = pd.Series(2.0 * fe["F0"].values + rng.normal(0, 0.1, N))
        neutral = factor_neutralization(signal, fe, method="regression")
        # Correlation between neutralized signal and F0 should be near 0
        corr = float(np.corrcoef(neutral, fe["F0"].values)[0, 1])
        assert abs(corr) < 0.1

    def test_pandas_series_output_type(self):
        """With pd.Series input, should return pd.Series."""
        rng = np.random.default_rng(2)
        signal, fe = _make_signal_exposures(rng)
        result = factor_neutralization(signal, fe)
        assert isinstance(result, pd.Series)

    def test_ndarray_output_type(self):
        """With ndarray input, should return ndarray."""
        rng = np.random.default_rng(3)
        N, K = 40, 2
        fe = pd.DataFrame(rng.normal(0, 1, (N, K)), columns=["F0", "F1"])
        signal = rng.normal(0, 1, N)
        result = factor_neutralization(signal, fe)
        assert isinstance(result, np.ndarray)

    def test_shape_mismatch_raises(self):
        """Mismatched lengths should raise ValueError."""
        rng = np.random.default_rng(4)
        fe = pd.DataFrame(rng.normal(0, 1, (30, 2)), columns=["F0", "F1"])
        signal = np.ones(20)
        with pytest.raises(ValueError, match="length"):
            factor_neutralization(signal, fe)

    def test_ranking_method_runs(self):
        """Ranking method should run without errors."""
        rng = np.random.default_rng(5)
        signal, fe = _make_signal_exposures(rng, N=60)
        result = factor_neutralization(signal, fe, method="ranking")
        assert len(result) == 60

    def test_factors_to_neutralize_subset(self):
        """factors_to_neutralize should allow subset selection."""
        rng = np.random.default_rng(6)
        N = 50
        fe = pd.DataFrame(
            rng.normal(0, 1, (N, 3)),
            columns=["F0", "F1", "F2"],
        )
        signal = pd.Series(rng.normal(0, 1, N))
        result_all = factor_neutralization(signal, fe)
        result_sub = factor_neutralization(signal, fe, factors_to_neutralize=["F0"])
        # Both should return valid length arrays
        assert len(result_all) == N
        assert len(result_sub) == N
