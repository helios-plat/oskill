"""Tests for liquidation_cascade_risk (≥8 cases, ≥90% coverage)."""

import pytest

from oskill.liquidation_cascade_risk import (
    LiquidationCascadeInput,
    liquidation_cascade_risk,
)


def _base_input(**kwargs) -> LiquidationCascadeInput:
    defaults = dict(
        symbol="BTCUSDT",
        oi_history=[1.0e9, 1.05e9, 1.1e9, 1.15e9, 1.18e9],
        current_oi=1.2e9,
        funding_rate=0.0001,
        funding_history=[0.0001, 0.0001, 0.0002, 0.0001, 0.0002],
        crowding_score=0.5,
        perp_basis=0.001,
        cross_exchange_funding_diff=0.0,
    )
    defaults.update(kwargs)
    return LiquidationCascadeInput(**defaults)


# ── 1. 正常路径: 高 OI + 高正 funding + 高拥挤 → extreme/long_squeeze ──────────
def test_extreme_long_squeeze():
    data = _base_input(
        oi_history=[1.0e9] * 20,
        current_oi=2.0e9,
        funding_rate=0.002,
        funding_history=[0.0001] * 20,
        crowding_score=0.95,
        perp_basis=0.01,
    )
    result = liquidation_cascade_risk(data=data)
    assert result.risk_level == "extreme"
    assert result.direction_bias == "long_squeeze"
    assert result.risk_score >= 0.80


# ── 2. 正常路径: 高 OI + 高负 funding + 高拥挤 → short_squeeze ────────────────
def test_high_short_squeeze():
    data = _base_input(
        oi_history=[1.0e9] * 20,
        current_oi=2.0e9,
        funding_rate=-0.002,
        funding_history=[-0.0001] * 20,
        crowding_score=0.90,
        perp_basis=-0.01,
    )
    result = liquidation_cascade_risk(data=data)
    assert result.direction_bias == "short_squeeze"
    assert result.risk_level in ("high", "extreme")


# ── 3. 低风险: 中性 OI + 低 funding + 低拥挤 → low/neutral ───────────────────
def test_low_neutral():
    data = _base_input(
        oi_history=[1.0e9, 1.05e9, 1.1e9, 1.15e9, 1.2e9],
        current_oi=1.1e9,
        funding_rate=0.00005,
        funding_history=[0.0001, 0.0002, 0.0001, 0.0003, 0.0002],
        crowding_score=0.2,
        perp_basis=0.0002,
    )
    result = liquidation_cascade_risk(data=data)
    assert result.risk_level == "low"
    assert result.direction_bias == "neutral"


# ── 4. 边界: oi_history 单元素 ────────────────────────────────────────────────
def test_single_element_oi_history():
    data = _base_input(
        oi_history=[1.0e9],
        current_oi=1.5e9,
    )
    result = liquidation_cascade_risk(data=data)
    assert result.risk_score >= 0.0
    assert result.risk_score <= 1.0


# ── 5. 边界: risk_score 在分档阈值附近 ──────────────────────────────────────
def test_risk_level_thresholds():
    # 构造 risk_score ≈ 0.65 → high
    data = _base_input(
        oi_history=[1.0e9] * 10,
        current_oi=2.0e9,
        funding_rate=0.0007,
        funding_history=[0.0001] * 10,
        crowding_score=0.75,
        perp_basis=0.005,
    )
    result = liquidation_cascade_risk(data=data)
    assert result.risk_level in ("elevated", "high", "extreme")
    assert 0.0 <= result.risk_score <= 1.0


# ── 6. 错误: oi_history 空 → ValueError ─────────────────────────────────────
def test_empty_oi_history_raises():
    data = _base_input(oi_history=[])
    with pytest.raises(ValueError, match="oi_history"):
        liquidation_cascade_risk(data=data)


# ── 7. 错误: funding_history 空 → ValueError ─────────────────────────────────
def test_empty_funding_history_raises():
    data = _base_input(funding_history=[])
    with pytest.raises(ValueError, match="funding_history"):
        liquidation_cascade_risk(data=data)


# ── 8. 错误: current_oi <= 0 → ValueError ────────────────────────────────────
def test_non_positive_current_oi_raises():
    data = _base_input(current_oi=0.0)
    with pytest.raises(ValueError, match="current_oi"):
        liquidation_cascade_risk(data=data)

    data2 = _base_input(current_oi=-100.0)
    with pytest.raises(ValueError, match="current_oi"):
        liquidation_cascade_risk(data=data2)


# ── 9. 分量验证: components 四 key 齐全且 0-1 ─────────────────────────────────
def test_components_keys_and_range():
    data = _base_input()
    result = liquidation_cascade_risk(data=data)
    expected_keys = {"oi_percentile", "funding_extremity", "crowding", "basis_divergence"}
    assert set(result.components.keys()) == expected_keys
    for k, v in result.components.items():
        assert 0.0 <= v <= 1.0, f"{k}={v} 超出 [0,1]"


# ── 10. 阈值参数: 自定义 crowding_threshold 生效 ─────────────────────────────
def test_custom_crowding_threshold():
    data = _base_input(
        funding_rate=0.001,
        crowding_score=0.65,
    )
    # 默认 crowding_threshold=0.7: crowding_score=0.65 < 0.7 → neutral
    result_default = liquidation_cascade_risk(data=data)
    assert result_default.direction_bias == "neutral"

    # 自定义 crowding_threshold=0.6: crowding_score=0.65 > 0.6 → long_squeeze
    result_custom = liquidation_cascade_risk(data=data, crowding_threshold=0.6)
    assert result_custom.direction_bias == "long_squeeze"


# ── 11. cross_exchange_funding_diff 参与 basis_divergence 计算 ───────────────
def test_cross_exchange_funding_diff_contributes():
    data_no_diff = _base_input(perp_basis=0.0, cross_exchange_funding_diff=0.0)
    data_with_diff = _base_input(perp_basis=0.0, cross_exchange_funding_diff=0.02)
    r_no = liquidation_cascade_risk(data=data_no_diff)
    r_with = liquidation_cascade_risk(data=data_with_diff)
    assert r_with.components["basis_divergence"] > r_no.components["basis_divergence"]
    assert r_with.risk_score >= r_no.risk_score


# ── 12. symbol 透传 ──────────────────────────────────────────────────────────
def test_symbol_passthrough():
    data = _base_input(symbol="ETHUSDT")
    result = liquidation_cascade_risk(data=data)
    assert result.symbol == "ETHUSDT"
