"""Tests for oskill.risk.position_size_tiers."""

import pytest

from oskill.risk.position_size_tiers import position_size_tiers


def _base_kwargs(**overrides):
    kwargs = dict(
        optimal_weight=0.5,
        capital_usd=10_000.0,
        slippage_scale=1.0,
        current_position_usd=0.0,
        atr_pct=0.02,
        atr_risk_budget=0.01,
        atr_min_position=0.005,
        atr_max_position=1.0,
        correlated_positions=[],
        max_net_exposure=1.0,
        min_trade_notional=10.0,
    )
    kwargs.update(overrides)
    return kwargs


def test_proposed_passes_through_when_all_tiers_have_headroom():
    result = position_size_tiers(100.0, **_base_kwargs())
    assert result["rejected"] is False
    assert result["binding_tier"] == "proposed"
    assert result["final_notional"] == pytest.approx(100.0)


def test_tier1_binds_when_near_optimal_max():
    # optimal_max = 0.5 * 10000 * 1.0 = 5000; current = 4950 -> headroom 50
    result = position_size_tiers(200.0, **_base_kwargs(current_position_usd=4950.0))
    assert result["binding_tier"] == "tier1_headroom"
    assert result["final_notional"] == pytest.approx(50.0)


def test_tier1_zero_headroom_rejects():
    result = position_size_tiers(100.0, **_base_kwargs(current_position_usd=5000.0))
    assert result["rejected"] is True
    assert result["final_notional"] == 0.0


def test_tier2_atr_cap_binds_under_high_volatility():
    # atr_pct high -> tiny atr cap fraction -> tiny notional cap
    result = position_size_tiers(
        1000.0,
        **_base_kwargs(
            optimal_weight=1.0,
            atr_pct=5.0,
            atr_risk_budget=0.01,
            atr_min_position=0.0001,
            atr_max_position=1.0,
        ),
    )
    assert result["binding_tier"] == "tier2_atr_cap"
    expected_cap_fraction = max(0.0001, min(1.0, 0.01 / 5.0))
    assert result["final_notional"] == pytest.approx(expected_cap_fraction * 10_000.0)


def test_tier3_correlation_clip_binds():
    result = position_size_tiers(
        1000.0,
        **_base_kwargs(
            optimal_weight=1.0,
            atr_pct=0.001,
            atr_max_position=1.0,
            correlated_positions=[(0.5, 0.85)],
            max_net_exposure=0.1,
        ),
    )
    assert result["binding_tier"] == "tier3_corr_clip"
    assert result["final_notional"] < 1000.0
    assert any("tier3" in r for r in result["reasons"])


def test_below_min_trade_notional_rejected():
    result = position_size_tiers(5.0, **_base_kwargs(min_trade_notional=10.0))
    assert result["rejected"] is True
    assert result["final_notional"] == 0.0
    assert any("min_trade_notional" in r for r in result["reasons"])


def test_tiers_dict_always_present():
    result = position_size_tiers(50.0, **_base_kwargs())
    assert set(result["tiers"].keys()) == {
        "tier1_headroom",
        "tier2_atr_cap",
        "tier3_corr_clip",
    }
