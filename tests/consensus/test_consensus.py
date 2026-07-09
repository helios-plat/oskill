"""Tests for oskill.consensus.* + sentiment/on-chain synthesis."""

import pytest

from oskill.consensus.engine_consensus import engine_consensus
from oskill.consensus.ewma_weight_update import ewma_weight_update
from oskill.signal.sentiment_onchain_synthesis import fgi_sentiment_bias, onchain_signal


# ── fgi_sentiment_bias ──────────────────────────────────────────────────────
def test_fgi_extreme_fear_is_bullish_contrarian():
    r = fgi_sentiment_bias(10)
    assert r["bias"] > 0 and r["classification"] == "extreme_fear"


def test_fgi_extreme_greed_is_bearish():
    r = fgi_sentiment_bias(90)
    assert r["bias"] < 0 and r["classification"] == "extreme_greed"


def test_fgi_out_of_range_raises():
    with pytest.raises(ValueError):
        fgi_sentiment_bias(150)


# ── onchain_signal ──────────────────────────────────────────────────────────
def test_onchain_net_outflow_is_bullish():
    r = onchain_signal(flow_in=100, flow_out=300, mvrv=1.0)
    assert r["signal"] > 0  # coins leaving exchanges = accumulation


def test_onchain_high_mvrv_is_bearish():
    r = onchain_signal(flow_in=100, flow_out=100, mvrv=3.0)
    assert r["signal"] < 0


# ── ewma_weight_update ──────────────────────────────────────────────────────
def test_ewma_wins_raise_weight():
    r = ewma_weight_update(0.5, [1, 1, 1, 1, 1], base_weight=1.0)
    assert r["accuracy"] > 0.5 and r["dynamic_weight"] > 1.0


def test_ewma_losses_lower_weight_toward_floor():
    r = ewma_weight_update(0.5, [0] * 100, base_weight=1.0)
    assert r["dynamic_weight"] < 1.0
    assert r["dynamic_weight"] >= 0.5  # floor_mult clamp never breached
    assert r["accuracy"] < 0.1  # many losses drive accuracy toward 0


def test_ewma_bad_prior_raises():
    with pytest.raises(ValueError):
        ewma_weight_update(1.5, [1], base_weight=1.0)


# ── engine_consensus ────────────────────────────────────────────────────────
def _sig(engine, score, promoted, conf=1.0):
    d = "long" if score > 0 else ("short" if score < 0 else "neutral")
    return {
        "engine": engine,
        "direction": d,
        "score": score,
        "confidence": conf,
        "promoted": promoted,
        "age_seconds": 0,
    }


def test_only_promoted_engines_drive_live():
    sigs = [_sig("ta", 0.8, True), _sig("ml", -0.9, False)]  # ml would flip it but is not promoted
    c = engine_consensus(sigs, weights={"ta": 1.0, "ml": 1.8})
    assert c["final_direction"] == "long"  # ml (not promoted) contributes 0 to live
    assert c["n_promoted"] == 1
    assert c["live_score"] == pytest.approx(0.8)


def test_no_promoted_engine_cannot_execute():
    sigs = [_sig("ml", 0.9, False), _sig("llm", 0.0, False)]
    c = engine_consensus(sigs, weights={"ml": 1.8, "llm": 1.2})
    assert c["should_execute"] is False
    assert c["n_promoted"] == 0


def test_crisis_shrinks_kelly():
    sigs = [_sig("ta", 0.9, True)]
    calm = engine_consensus(sigs, weights={"ta": 1.0}, regime_state="range")
    crisis = engine_consensus(sigs, weights={"ta": 1.0}, regime_state="crisis")
    assert crisis["kelly_position"] < calm["kelly_position"]


def test_strong_agreement_executes():
    sigs = [_sig("ta", 0.9, True), _sig("ml", 0.8, True)]
    c = engine_consensus(sigs, weights={"ta": 1.0, "ml": 1.0}, base_threshold=0.4)
    assert c["should_execute"] is True
    assert c["is_divergent"] is False
