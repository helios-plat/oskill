"""Tests for okx_liquidation_notional (≥8 cases).

重点不是覆盖率,是把 HELIVEX-IMPL_SPEC-LER-001 §5.1.1 的两个静默错误钉死:
C1(合约张数 ≠ 币量,BTC 高估 100×)与 C2(side 是订单方向,不是仓位方向)。
"""

from datetime import datetime

import pytest

from oskill.okx_liquidation_notional import (
    OKX_CT_VAL,
    OkxLiquidationEvent,
    OkxLiquidationNotionalInput,
    okx_liquidation_notional,
)

T0 = datetime(2026, 7, 11, 0, 0)


def _ev(
    minute: int = 0,
    side: str = "sell",
    size: float = 100.0,
    price: float = 100_000.0,
    inst_id: str = "BTC-USDT-SWAP",
) -> OkxLiquidationEvent:
    return OkxLiquidationEvent(
        ts=T0.replace(minute=minute), inst_id=inst_id, side=side, size=size, price=price
    )


def _input(events, inst_id: str = "BTC-USDT-SWAP", window_minutes: int = 5):
    return OkxLiquidationNotionalInput(
        inst_id=inst_id, events=events, window_minutes=window_minutes
    )


# ── 1. C1 核心: BTC ctVal=0.01,天真的 size*price 会高估 100× ──────────────────
def test_ctval_btc_prevents_100x_overestimate():
    result = okx_liquidation_notional(data=_input([_ev(size=100, price=100_000)]))
    naive = 100 * 100_000  # size * price —— 这就是要防的写法

    assert result.total_long_notional == 100 * 0.01 * 100_000 == 100_000.0
    assert naive / result.total_long_notional == 100.0
    assert result.ct_val == 0.01


# ── 2. C1: ETH ctVal=0.1(高估 10×) ────────────────────────────────────────────
def test_ctval_eth():
    ev = _ev(size=50, price=4_000, inst_id="ETH-USDT-SWAP")
    result = okx_liquidation_notional(data=_input([ev], inst_id="ETH-USDT-SWAP"))

    assert result.ct_val == 0.1
    assert result.total_long_notional == 50 * 0.1 * 4_000 == 20_000.0


# ── 3. C1: SOL ctVal=1(唯一一个 size*price 恰好正确的标的 —— 正是误导来源)─────
def test_ctval_sol_is_one():
    ev = _ev(size=200, price=150, inst_id="SOL-USDT-SWAP")
    result = okx_liquidation_notional(data=_input([ev], inst_id="SOL-USDT-SWAP"))

    assert result.ct_val == 1.0
    assert result.total_long_notional == 200 * 150 == 30_000.0


# ── 4. C1: 未知 instId 必须抛错,不得按 ctVal=1 静默兜底 ───────────────────────
def test_unknown_inst_id_raises_not_silently_defaults():
    with pytest.raises(ValueError, match="未知 instId"):
        okx_liquidation_notional(
            data=_input([_ev(inst_id="DOGE-USDT-SWAP")], inst_id="DOGE-USDT-SWAP")
        )


# ── 5. C2: side='sell' = 多头被强制平仓(卖出平多)────────────────────────────
def test_side_sell_is_long_liquidation():
    result = okx_liquidation_notional(data=_input([_ev(side="sell")]))

    assert result.total_long_notional == 100_000.0
    assert result.total_short_notional == 0.0


# ── 6. C2: side='buy' = 空头被强制平仓 ────────────────────────────────────────
def test_side_buy_is_short_liquidation():
    result = okx_liquidation_notional(data=_input([_ev(side="buy")]))

    assert result.total_short_notional == 100_000.0
    assert result.total_long_notional == 0.0


# ── 7. 同一分钟内多笔累加,多空分开记 ──────────────────────────────────────────
def test_same_minute_events_sum_per_side():
    events = [
        _ev(minute=0, side="sell", size=100),
        _ev(minute=0, side="sell", size=50),
        _ev(minute=0, side="buy", size=30),
    ]
    result = okx_liquidation_notional(data=_input(events))

    assert result.long_liq_1m[0] == 150 * 0.01 * 100_000
    assert result.short_liq_1m[0] == 30 * 0.01 * 100_000
    assert result.n_events == 3


# ── 8. 无事件的分钟补 0,不前向填充(那一分钟确实没有强制流)──────────────────
def test_gap_minutes_are_zero_not_forward_filled():
    events = [_ev(minute=0, size=100), _ev(minute=3, size=100)]
    result = okx_liquidation_notional(data=_input(events))

    assert len(result.minutes) == 4  # 00,01,02,03 —— 连续网格
    assert result.long_liq_1m == [100_000.0, 0.0, 0.0, 100_000.0]


# ── 9. 滚动窗口和 = 过去 W 分钟(含当前)之和 ─────────────────────────────────
def test_rolling_window_sums_over_w_minutes():
    events = [_ev(minute=m, size=100) for m in range(6)]
    result = okx_liquidation_notional(data=_input(events, window_minutes=5))

    per_min = 100 * 0.01 * 100_000
    assert result.long_liq_rolling[0] == per_min  # min_periods=1
    assert result.long_liq_rolling[4] == 5 * per_min  # 窗口填满
    assert result.long_liq_rolling[5] == 5 * per_min  # 滚出去一根


# ── 10. 混入其它标的必须抛错(ctVal 不同,名义额不可相加)─────────────────────
def test_mixed_inst_id_events_raise():
    events = [_ev(inst_id="BTC-USDT-SWAP"), _ev(inst_id="SOL-USDT-SWAP")]
    with pytest.raises(ValueError, match="含其它标的"):
        okx_liquidation_notional(data=_input(events))


# ── 11. 空 events 抛错 ────────────────────────────────────────────────────────
def test_empty_events_raise():
    with pytest.raises(ValueError, match="不能为空"):
        okx_liquidation_notional(data=_input([]))


# ── 12. stateless: 同输入两次调用结果相同,且不修改入参 ───────────────────────
def test_stateless_and_does_not_mutate_input():
    data = _input([_ev(minute=0), _ev(minute=1, side="buy")])
    before = data.model_dump()

    first = okx_liquidation_notional(data=data)
    second = okx_liquidation_notional(data=data)

    assert first.model_dump() == second.model_dump()
    assert data.model_dump() == before


# ── 13. ctVal 表本身就是被判决工件(进 fingerprint),值锁死 ────────────────────
def test_ct_val_table_locked():
    assert OKX_CT_VAL == {
        "BTC-USDT-SWAP": 0.01,
        "ETH-USDT-SWAP": 0.1,
        "SOL-USDT-SWAP": 1.0,
    }
