"""Tests for oskill.signal.ta_multi_indicator_signal + ml_feature_matrix."""

import numpy as np
import pytest

from oskill.signal.ml_feature_matrix import ml_feature_matrix
from oskill.signal.ta_multi_indicator_signal import ta_multi_indicator_signal


def _rising(n=200, drift=0.002, seed=0):
    rng = np.random.default_rng(seed)
    return list(100 * np.exp(np.cumsum(rng.normal(drift, 0.005, n))))


def test_ta_rising_series_is_long():
    r = ta_multi_indicator_signal(_rising())
    assert r["direction"] == "long"
    assert -1.0 <= r["score"] <= 1.0
    assert 0.0 <= r["confidence"] <= 1.0
    assert set(r["votes"]) == {"trend", "momentum", "slope", "rsi", "bollinger"}


def test_ta_falling_scores_below_rising():
    # blends trend-following + mean-reversion, so a falling series need not be
    # strictly "short", but it must score below a rising series
    up = ta_multi_indicator_signal(_rising(drift=0.003))["score"]
    down = ta_multi_indicator_signal(_rising(drift=-0.003))["score"]
    assert down < up
    assert down <= 0.0


def test_ta_insufficient_bars_raises():
    with pytest.raises(ValueError):
        ta_multi_indicator_signal([100.0] * 10)


def test_feature_matrix_shape_and_no_nan():
    df = ml_feature_matrix(_rising(n=300))
    assert "_bar_index" in df.columns
    assert not df.drop(columns=["_bar_index"]).isna().any().any()
    assert len(df) > 100


def test_feature_matrix_insufficient_raises():
    with pytest.raises(ValueError):
        ml_feature_matrix([100.0] * 10)
