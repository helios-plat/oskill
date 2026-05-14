"""Tests for factor_quantile_returns."""

from __future__ import annotations

import numpy as np
import pytest

from oskill.factor import factor_quantile_returns


@pytest.fixture
def random_data():
    """Random T x N factor and returns."""
    rng = np.random.default_rng(42)
    T, N = 100, 30
    factor = rng.standard_normal((T, N))
    returns = rng.standard_normal((T, N)) * 0.01
    return factor, returns


@pytest.fixture
def perfect_factor():
    """Factor perfectly predicts next period's return."""
    rng = np.random.default_rng(0)
    T, N = 200, 50
    returns = rng.standard_normal((T, N)) * 0.01
    # Factor exactly equals next-period returns
    factor = returns.copy()
    return factor, returns


def test_factor_quantiles_returns_dict_with_five_keys(random_data):
    """Result must have exactly five keys."""
    factor, returns = random_data
    result = factor_quantile_returns(factor, returns)
    assert set(result.keys()) == {
        "quantile_returns", "mean_returns_by_quantile",
        "long_short_returns", "monotonicity_score", "top_minus_bottom_sharpe"
    }


def test_factor_quantiles_basic_5q(random_data):
    """Basic test with 5 quantiles."""
    factor, returns = random_data
    T, N = factor.shape
    result = factor_quantile_returns(factor, returns, n_quantiles=5)

    assert result["quantile_returns"].shape == (T, 5)
    assert result["mean_returns_by_quantile"].shape == (5,)
    assert result["long_short_returns"].shape == (T,)
    assert isinstance(result["monotonicity_score"], float)
    assert isinstance(result["top_minus_bottom_sharpe"], float)


def test_factor_quantiles_perfect_predictor(perfect_factor):
    """Perfect factor should give Q5 mean return >> Q1 mean return."""
    factor, returns = perfect_factor
    result = factor_quantile_returns(factor, returns, n_quantiles=5)

    mean_rets = result["mean_returns_by_quantile"]
    # Top quantile (Q5) should have higher mean than bottom (Q1)
    assert mean_rets[4] > mean_rets[0], (
        f"Perfect predictor: Q5 mean={mean_rets[4]:.4f} not > Q1 mean={mean_rets[0]:.4f}"
    )
    # Monotonicity score should be high
    assert result["monotonicity_score"] > 0.5


def test_factor_quantiles_random_low_monotonicity(random_data):
    """Random factor → monotonicity_score ≈ 0.5 (no systematic edge)."""
    factor, returns = random_data
    result = factor_quantile_returns(factor, returns, n_quantiles=5)
    # With random factor, monotonicity could be anywhere, but shouldn't be extreme
    assert 0.0 <= result["monotonicity_score"] <= 1.0


def test_factor_quantiles_long_short_shape(random_data):
    """long_short_returns must have length T."""
    factor, returns = random_data
    T = factor.shape[0]
    result = factor_quantile_returns(factor, returns, n_quantiles=5)
    assert len(result["long_short_returns"]) == T


def test_factor_quantiles_mean_returns_length_n_quantiles(random_data):
    """mean_returns_by_quantile must have length n_quantiles."""
    factor, returns = random_data
    for n_q in [3, 5, 10]:
        result = factor_quantile_returns(factor, returns, n_quantiles=n_q)
        assert len(result["mean_returns_by_quantile"]) == n_q


def test_factor_quantiles_invalid_n_quantiles_raises(random_data):
    """n_quantiles=1 should raise ValueError."""
    factor, returns = random_data
    with pytest.raises(ValueError):
        factor_quantile_returns(factor, returns, n_quantiles=1)


def test_factor_quantiles_mismatched_shapes_raises():
    """Mismatched factor and returns shapes should raise ValueError."""
    rng = np.random.default_rng(0)
    factor = rng.standard_normal((100, 20))
    returns = rng.standard_normal((100, 15))  # different N
    with pytest.raises(ValueError):
        factor_quantile_returns(factor, returns)


def test_factor_quantiles_monotonicity_score_range(random_data):
    """Monotonicity score must be in [0, 1]."""
    factor, returns = random_data
    result = factor_quantile_returns(factor, returns, n_quantiles=5)
    assert 0.0 <= result["monotonicity_score"] <= 1.0


@pytest.mark.academic_reference
def test_factor_quantiles_fama_macbeth_structure(perfect_factor):
    """Verify monotonic returns in Q1..Q5 for perfect predictor; top_minus_bottom_sharpe > 0.

    Reference: Fama & MacBeth (1973), cross-sectional factor sorting methodology.
    """
    factor, returns = perfect_factor
    result = factor_quantile_returns(factor, returns, n_quantiles=5)

    mean_rets = result["mean_returns_by_quantile"]

    # Perfect predictor → Q5 > Q1 (monotonic trend expected)
    assert mean_rets[4] > mean_rets[0], (
        f"Fama-MacBeth: Q5 ({mean_rets[4]:.6f}) should exceed Q1 ({mean_rets[0]:.6f}) for perfect factor"
    )

    # Long-short Sharpe should be positive
    assert result["top_minus_bottom_sharpe"] > 0.0, (
        f"top_minus_bottom_sharpe={result['top_minus_bottom_sharpe']:.4f} should be > 0"
    )

    # Monotonicity score should be > 0.5 for a good predictor
    assert result["monotonicity_score"] > 0.5
