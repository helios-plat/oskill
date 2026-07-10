"""Tests for oskill.risk.consensus_risk_size + oskill.consensus.engine_attribution."""

import pytest

from oskill.consensus.engine_attribution import engine_attribution
from oskill.risk.consensus_risk_size import consensus_risk_size


def _call(**kw):
    base = dict(
        direction="long",
        kelly_position=0.15,
        should_execute=True,
        capital_usd=5000,
        current_position_usd=0.0,
        atr_pct=0.02,
        regime_state="range",
        optimal_weight=0.4,
    )
    base.update(kw)
    return consensus_risk_size(**base)


def test_range_long_approved():
    r = _call()
    assert r["approved"] is True
    assert r["final_notional"] == pytest.approx(0.15 * 5000)
    assert r["blocking_stage"] is None


def test_not_executable_blocked_at_gate():
    r = _call(should_execute=False)
    assert r["approved"] is False and r["blocking_stage"] == "gate"


def test_neutral_blocked_at_gate():
    r = _call(direction="neutral")
    assert r["approved"] is False and r["blocking_stage"] == "gate"


def test_crisis_scales_notional():
    calm = _call(regime_state="range")["final_notional"]
    crisis = _call(regime_state="crisis")
    assert crisis["crisis_scaled"] is True
    assert crisis["final_notional"] == pytest.approx(calm * 0.1)


def test_fee_edge_blocks_tiny_atr():
    # very low ATR -> fee/edge fails (also tier2 cap huge). Force approval up to fee stage.
    r = _call(atr_pct=0.00003)
    assert r["approved"] is False
    assert r["blocking_stage"] in {"fee_edge", "position_tiers"}


# ── engine_attribution ──────────────────────────────────────────────────────
def test_attribution_credits_all_engines():
    rts = [
        {"realized_pnl": 10.0, "engines": ["ta", "ml"]},
        {"realized_pnl": -5.0, "engines": ["ta"]},
    ]
    a = engine_attribution(rts)
    assert a["ta"]["count"] == 2 and a["ta"]["wins"] == 1
    assert a["ta"]["total_pnl"] == pytest.approx(5.0)
    assert a["ml"]["win_rate"] == 1.0
    assert a["ta"]["results"] == [1.0, 0.0]


def test_attribution_empty():
    assert engine_attribution([]) == {}
