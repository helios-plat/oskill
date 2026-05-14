"""Tests for multiplier_preferences_robust."""

from __future__ import annotations

import numpy as np
import pytest

from oskill.robust.multiplier_preferences import multiplier_preferences_robust


def make_returns(T: int = 100, N: int = 4, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.001, 0.02, (T, N))


class TestMultiplierPreferencesBasic:
    def test_returns_dict_keys(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0)
        assert "weights" in result
        assert "worst_case_distortion" in result
        assert "detection_error_prob" in result
        assert "theta_effective" in result

    def test_weights_sum_to_one(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_weights_non_negative(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0)
        assert np.all(result["weights"] >= -1e-8)

    def test_detection_error_prob_in_range(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0)
        dep = result["detection_error_prob"]
        assert 0.0 <= dep <= 0.5

    def test_theta_effective_matches(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=2.5)
        assert result["theta_effective"] == pytest.approx(2.5)

    def test_distortion_shape(self):
        T = 100
        returns = make_returns(T=T)
        result = multiplier_preferences_robust(returns, theta=1.0)
        assert result["worst_case_distortion"].shape == (T,)

    def test_distortion_near_zero_large_theta(self):
        """Large theta → distortion near 0 (near expected utility)."""
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1e6)
        assert np.abs(result["worst_case_distortion"]).max() < 0.1


class TestMultiplierPreferencesUtility:
    def test_log_utility(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0, utility="log")
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_power_utility(self):
        returns = make_returns()
        result = multiplier_preferences_robust(
            returns, theta=1.0, utility="power", risk_aversion=3.0
        )
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_exponential_utility(self):
        returns = make_returns()
        result = multiplier_preferences_robust(returns, theta=1.0, utility="exponential")
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_single_asset(self):
        rng = np.random.default_rng(1)
        returns = rng.normal(0.001, 0.02, (100, 1))
        result = multiplier_preferences_robust(returns, theta=1.0)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0


class TestMultiplierPreferencesValidation:
    def test_theta_zero_raises(self):
        returns = make_returns()
        with pytest.raises(ValueError, match="theta must be > 0"):
            multiplier_preferences_robust(returns, theta=0.0)

    def test_theta_negative_raises(self):
        returns = make_returns()
        with pytest.raises(ValueError, match="theta must be > 0"):
            multiplier_preferences_robust(returns, theta=-1.0)

    def test_1d_returns_handled(self):
        """1-D returns should be reshaped without error."""
        rng = np.random.default_rng(5)
        returns_1d = rng.normal(0.001, 0.02, 100)
        result = multiplier_preferences_robust(returns_1d, theta=1.0)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0
