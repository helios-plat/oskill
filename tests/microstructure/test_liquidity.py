"""Tests for kyle_lambda_estimator and amihud_illiquidity."""

import numpy as np
import pytest

from oskill.microstructure.liquidity import amihud_illiquidity, kyle_lambda_estimator


class TestKyleLambda:
    def test_basic_regression_returns_float(self):
        rng = np.random.default_rng(42)
        n = 50
        sv = rng.normal(0, 1, n)
        returns = 0.5 * sv + rng.normal(0, 0.1, n)
        lam = kyle_lambda_estimator(returns, sv)
        assert isinstance(lam, float)

    def test_regression_positive_impact(self):
        """Positive signed volume should positively impact prices."""
        rng = np.random.default_rng(7)
        n = 200
        sv = rng.normal(0, 1, n)
        returns = 0.3 * sv + rng.normal(0, 0.05, n)
        lam = kyle_lambda_estimator(returns, sv)
        assert lam > 0

    def test_rolling_returns_array(self):
        rng = np.random.default_rng(1)
        n = 100
        sv = rng.normal(0, 1, n)
        returns = 0.2 * sv + rng.normal(0, 0.1, n)
        lam = kyle_lambda_estimator(returns, sv, estimator="rolling", window=20)
        assert isinstance(lam, np.ndarray)
        assert lam.shape == (n,)

    def test_rolling_nan_at_start(self):
        """Rolling should have NaN for first window-1 elements."""
        rng = np.random.default_rng(2)
        n = 50
        sv = rng.normal(0, 1, n)
        returns = 0.2 * sv + rng.normal(0, 0.1, n)
        lam = kyle_lambda_estimator(returns, sv, estimator="rolling", window=10)
        assert np.all(np.isnan(lam[:9]))
        assert np.all(np.isfinite(lam[9:]))

    def test_zero_volume_returns_zero(self):
        """Zero variance signed volume yields lambda = 0."""
        returns = np.ones(10) * 0.01
        sv = np.zeros(10)
        lam = kyle_lambda_estimator(returns, sv)
        assert lam == 0.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            kyle_lambda_estimator(np.ones(5), np.ones(6))

    def test_invalid_estimator_raises(self):
        with pytest.raises(ValueError, match="Unknown estimator"):
            kyle_lambda_estimator(np.ones(10), np.ones(10), estimator="bad")

    def test_directionality(self):
        """Lambda should be negative when returns anti-correlate with signed volume."""
        rng = np.random.default_rng(99)
        n = 200
        sv = rng.normal(0, 1, n)
        returns = -0.5 * sv + rng.normal(0, 0.05, n)
        lam = kyle_lambda_estimator(returns, sv)
        assert lam < 0


class TestAmihudIlliquidity:
    def test_single_value_returns_float(self):
        returns = np.array([0.01, -0.02, 0.005])
        dvols = np.array([1e6, 2e6, 5e5])
        illiq = amihud_illiquidity(returns, dvols)
        assert isinstance(illiq, float)
        assert illiq >= 0

    def test_higher_volume_lower_illiquidity(self):
        """Higher trading volume should yield lower illiquidity."""
        returns = np.array([0.01, 0.01, 0.01])
        low_vol = np.array([1e4, 1e4, 1e4])
        high_vol = np.array([1e7, 1e7, 1e7])
        illiq_low = amihud_illiquidity(returns, low_vol)
        illiq_high = amihud_illiquidity(returns, high_vol)
        assert illiq_low > illiq_high

    def test_zero_dollar_volume_nan(self):
        """Zero dollar volume should yield NaN for that observation."""
        returns = np.array([0.01, 0.02])
        dvols = np.array([0.0, 1e6])
        # Should not raise; NaN is handled
        illiq = amihud_illiquidity(returns, dvols)
        assert np.isfinite(illiq)  # mean ignores NaN

    def test_rolling_returns_array(self):
        rng = np.random.default_rng(5)
        n = 50
        returns = rng.normal(0, 0.01, n)
        dvols = rng.uniform(1e5, 1e7, n)
        illiq = amihud_illiquidity(returns, dvols, window=10)
        assert isinstance(illiq, np.ndarray)
        assert illiq.shape == (n,)

    def test_annualize_scales_by_252(self):
        returns = np.array([0.01, 0.02, 0.015])
        dvols = np.array([1e6, 1e6, 1e6])
        illiq = amihud_illiquidity(returns, dvols)
        illiq_ann = amihud_illiquidity(returns, dvols, annualize=True)
        assert illiq_ann == pytest.approx(illiq * 252)

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            amihud_illiquidity(np.ones(5), np.ones(6))
