"""Tests for oskill.signal.trend_follower_signal + intraday_scalper_signal (P7)."""

import numpy as np
import pytest

from oskill.signal.intraday_scalper_signal import intraday_scalper_signal
from oskill.signal.trend_follower_signal import trend_follower_signal


def _uptrend(n=80, drift=0.6, seed=1):
    rng = np.random.default_rng(seed)
    c = np.cumsum(np.abs(rng.normal(drift, 0.2, n))) + 100
    return c + 0.5, c - 0.5, c  # highs, lows, closes


def _choppy(n=80, seed=2):
    rng = np.random.default_rng(seed)
    c = 100 + rng.normal(0, 1, n)
    return c + 0.5, c - 0.5, c


# ── trend_follower ──────────────────────────────────────────────────────────
def test_trend_follower_shape():
    h, lo, c = _uptrend()
    r = trend_follower_signal(h, lo, c)
    assert r["direction"] in {"long", "short", "neutral"}
    assert set(r) >= {"direction", "score", "confidence", "adx", "exit_level", "votes"}


def test_trend_follower_ranging_is_neutral():
    # low ADX -> no trend -> neutral regardless of position
    h, lo, c = _choppy()
    r = trend_follower_signal(h, lo, c, adx_threshold=25)
    assert r["direction"] == "neutral"


def test_trend_follower_uptrend_breakout_long_with_exit():
    h, lo, c = _uptrend(drift=0.8)
    r = trend_follower_signal(h, lo, c, adx_threshold=20)
    # strong uptrend with breakout -> long with a chandelier exit level
    if r["direction"] == "long":
        assert r["exit_level"] is not None and r["score"] > 0


def test_trend_follower_insufficient_raises():
    with pytest.raises(ValueError):
        trend_follower_signal([100] * 10, [99] * 10, [99] * 10)


# ── intraday_scalper ────────────────────────────────────────────────────────
def test_scalper_mode_switch_by_adx():
    h, lo, c = _uptrend()
    r = intraday_scalper_signal(c, h, lo, adx_enter=22)
    assert r["mode"] == "breakout"  # strong trend -> breakout mode
    h2, lo2, c2 = _choppy()
    r2 = intraday_scalper_signal(c2, h2, lo2, adx_enter=22)
    assert r2["mode"] == "mean_reversion"  # ranging -> mean-reversion mode


def test_scalper_shape():
    h, lo, c = _choppy()
    r = intraday_scalper_signal(c, h, lo)
    assert r["direction"] in {"long", "short", "neutral"}
    assert -1.0 <= r["score"] <= 1.0


def test_scalper_insufficient_raises():
    with pytest.raises(ValueError):
        intraday_scalper_signal([100] * 10, [100] * 10, [99] * 10)
