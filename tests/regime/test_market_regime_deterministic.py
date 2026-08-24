"""Tests for oskill.regime.market_regime_deterministic."""

import numpy as np
import pytest

from oskill.regime.market_regime_deterministic import market_regime_deterministic


def _series(n=800, seed=0, vol=0.01, drift=0.0):
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, n)
    return 100.0 * np.exp(np.cumsum(rets))


def test_returns_valid_state():
    r = market_regime_deterministic(_series())
    assert r["state"] in {"crisis", "trend", "range"}
    assert 0.0 <= r["confidence"] <= 1.0
    assert r["rows_used"] > 0


def test_high_vol_tail_flags_crisis():
    # calm then a volatility explosion at the end -> crisis
    calm = _series(n=700, seed=1, vol=0.005)
    rng = np.random.default_rng(2)
    shock = calm[-1] * np.exp(np.cumsum(rng.normal(0, 0.06, 150)))
    series = np.concatenate([calm, shock])
    r = market_regime_deterministic(series)
    assert r["state"] == "crisis"


def test_features_present():
    r = market_regime_deterministic(_series())
    assert set(r["features"]) == {"vol_percentile", "momentum_z", "autocorr_z"}


def test_insufficient_bars_raises():
    with pytest.raises(ValueError):
        market_regime_deterministic(_series(n=50))


def test_deterministic_reproducible():
    s = _series(seed=5)
    a = market_regime_deterministic(s)
    b = market_regime_deterministic(s)
    assert a["state"] == b["state"]
    assert a["confidence"] == pytest.approx(b["confidence"])
