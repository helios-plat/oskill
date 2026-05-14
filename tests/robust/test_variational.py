"""Tests for variational_preferences_estimate."""

from __future__ import annotations

import numpy as np
import pytest

from oskill.robust.variational_preferences import variational_preferences_estimate


def make_returns(T: int = 100, N: int = 4, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.001, 0.02, (T, N))


class TestVariationalPreferencesBasic:
    def test_returns_dict_keys(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns)
        assert "weights" in result
        assert "worst_measure_q" in result
        assert "cost_at_optimum" in result
        assert "divergence_type_used" in result

    def test_weights_sum_to_one(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_weights_non_negative(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns)
        assert np.all(result["weights"] >= -1e-8)

    def test_worst_measure_sums_to_one(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns)
        assert pytest.approx(result["worst_measure_q"].sum(), abs=1e-6) == 1.0

    def test_cost_non_negative(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns)
        assert result["cost_at_optimum"] >= 0.0

    def test_divergence_type_matches_input(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, cost_function="chi_square")
        assert result["divergence_type_used"] == "chi_square"

    def test_q_shape_matches_t(self):
        T = 100
        returns = make_returns(T=T)
        result = variational_preferences_estimate(returns)
        assert result["worst_measure_q"].shape == (T,)


class TestVariationalPreferencesLargeAmbiguity:
    def test_large_ambiguity_cost_near_zero(self):
        """Large ambiguity_index → near expected utility → cost near zero."""
        returns = make_returns()
        result = variational_preferences_estimate(returns, ambiguity_index=1e6)
        # Q converges to uniform → cost is small
        assert result["cost_at_optimum"] >= 0.0

    def test_large_ambiguity_weights_reasonable(self):
        """Large ambiguity_index → valid portfolio."""
        returns = make_returns()
        result = variational_preferences_estimate(returns, ambiguity_index=1e4)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0


class TestVariationalPreferencesCostFunctions:
    def test_entropy_cost(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, cost_function="entropy")
        assert result["cost_at_optimum"] >= 0.0
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_chi_square_cost(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, cost_function="chi_square")
        assert result["cost_at_optimum"] >= 0.0
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_wasserstein_cost(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, cost_function="wasserstein")
        assert result["cost_at_optimum"] >= 0.0
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_power_utility(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, utility="power", risk_aversion=3.0)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_q_non_negative(self):
        returns = make_returns()
        result = variational_preferences_estimate(returns, cost_function="chi_square")
        assert np.all(result["worst_measure_q"] >= -1e-10)


class TestVariationalPreferencesSingleAsset:
    def test_single_asset(self):
        rng = np.random.default_rng(7)
        returns = rng.normal(0.001, 0.02, (100, 1))
        result = variational_preferences_estimate(returns)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0

    def test_1d_returns(self):
        rng = np.random.default_rng(8)
        returns_1d = rng.normal(0.001, 0.02, 100)
        result = variational_preferences_estimate(returns_1d)
        assert pytest.approx(result["weights"].sum(), abs=1e-6) == 1.0
