"""Tests for oskill.performance.monte_carlo_trade_permutation.

The element answers "is the observed equity path better than a random
permutation of the same trades?" — it is the path-significance leg of the
backtest-credibility report. These tests pin the contract that the Helios
consumer depends on: the returned keys, determinism under a fixed seed, and the
degenerate short-input path.
"""

from __future__ import annotations

import numpy as np
import pytest

from oskill.performance import monte_carlo_trade_permutation

EXPECTED_KEYS = {
    "actual_sharpe",
    "actual_max_dd",
    "p_value_sharpe",
    "p_value_max_dd",
    "simulated_sharpe_mean",
    "simulated_sharpe_std",
    "simulated_sharpe_p5",
    "simulated_sharpe_p95",
    "n_simulations",
    "n_trades",
}


def _trades() -> list[dict]:
    return [
        {"pnl": 120.0},
        {"pnl": -80.0},
        {"pnl": 200.0},
        {"pnl": -50.0},
        {"pnl": 15.0},
        {"pnl": -10.0},
        {"pnl": 90.0},
        {"pnl": -120.0},
    ]


def test_returns_the_documented_keys():
    out = monte_carlo_trade_permutation(_trades(), n_simulations=100)
    assert EXPECTED_KEYS <= set(out)


def test_trade_count_matches_input():
    out = monte_carlo_trade_permutation(_trades(), n_simulations=100)
    assert out["n_trades"] == 8
    assert out["n_simulations"] == 100


def test_p_values_are_probabilities():
    out = monte_carlo_trade_permutation(_trades(), n_simulations=200, seed=3)
    for key in ("p_value_sharpe", "p_value_max_dd"):
        assert 0.0 <= out[key] <= 1.0, key


def test_deterministic_for_a_fixed_seed():
    a = monte_carlo_trade_permutation(_trades(), n_simulations=100, seed=42)
    b = monte_carlo_trade_permutation(_trades(), n_simulations=100, seed=42)
    assert a == b


def test_different_seeds_differ():
    a = monte_carlo_trade_permutation(_trades(), n_simulations=100, seed=1)
    b = monte_carlo_trade_permutation(_trades(), n_simulations=100, seed=2)
    assert a["simulated_sharpe_mean"] != b["simulated_sharpe_mean"]


def test_accepts_a_plain_pnl_array():
    pnls = np.array([100.0, -50.0, 25.0, -10.0, 60.0])
    from_array = monte_carlo_trade_permutation(pnls, n_simulations=100, seed=7)
    from_list = monte_carlo_trade_permutation(list(pnls), n_simulations=100, seed=7)
    assert from_array["actual_sharpe"] == from_list["actual_sharpe"]


@pytest.mark.parametrize("alt_key", ["realized_pnl_usd", "profit"])
def test_alternative_pnl_key_names(alt_key):
    trades = [{alt_key: 100.0}, {alt_key: -50.0}, {alt_key: 25.0}]
    out = monte_carlo_trade_permutation(trades, n_simulations=50)
    assert out["n_trades"] == 3


def test_all_winning_path_is_significant():
    """A monotone-up path should beat nearly every permutation."""
    trades = [{"pnl": 100.0 + i} for i in range(10)]
    out = monte_carlo_trade_permutation(trades, n_simulations=200, seed=5)
    assert out["p_value_sharpe"] < 0.5


def test_short_input_returns_degenerate_result():
    out = monte_carlo_trade_permutation([{"pnl": 10.0}, {"pnl": -5.0}], n_simulations=10)
    assert out["n_trades"] == 2
    assert out["p_value_sharpe"] == 1.0
    assert out["p_value_max_dd"] == 1.0
    assert out["actual_sharpe"] == 0.0
    assert out["warning"] == "insufficient trades (<3)"


def test_zero_variance_returns_zero_sharpe_not_a_crash():
    """All-zero PnL gives zero mean and zero dispersion -> Sharpe 0, no crash."""
    trades = [{"pnl": 0.0}, {"pnl": 0.0}, {"pnl": 0.0}, {"pnl": 0.0}]
    out = monte_carlo_trade_permutation(trades, n_simulations=20, seed=11)
    assert out["actual_sharpe"] == 0.0
    assert out["actual_max_dd"] == 0.0
    assert np.isfinite(out["actual_max_dd"])


def test_constant_positive_pnl_has_no_drawdown():
    trades = [{"pnl": 10.0}, {"pnl": 10.0}, {"pnl": 10.0}, {"pnl": 10.0}]
    out = monte_carlo_trade_permutation(trades, n_simulations=20, seed=11)
    assert out["actual_max_dd"] == 0.0


def test_max_drawdown_is_non_positive():
    out = monte_carlo_trade_permutation(_trades(), n_simulations=100, seed=13)
    assert out["actual_max_dd"] <= 0.0
