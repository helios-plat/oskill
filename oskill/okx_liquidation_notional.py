"""OKX 强制平仓事件 → 名义额流(合约乘数换算 + side→多空映射).

OKX `liquidation-orders` 的两个语义陷阱,不处理会**静默**产出错误信号:

1. `sz` 是**合约张数,不是币量**。名义额 = `sz × ctVal × price`。
   直接写 `sz × price` 会使 BTC 名义额**高估 100 倍**(ctVal = 0.01)。
2. `side` 是**强平订单本身的方向**,不是被强平仓位的方向。
   `side='sell'` = 一个**多头**被强制平仓(卖出平多);`side='buy'` = 空头被强平。
   搞反的概率是 50%,且不会报错。

本元素把这两条固定下来,并把逐笔事件聚合成 1m 名义额序列 + W 分钟滚动和。
未知 instId 一律抛错,不做 ctVal=1 的兜底——静默的 100× 比崩溃危险得多。

依赖: HELIVEX-IMPL_SPEC-LER-001 §5.1.1(C1/C2)。
组合 oprim: `rolling_window_aggregate`。
"""

from datetime import datetime
from typing import Literal

import pandas as pd
from oprim import rolling_window_aggregate
from pydantic import BaseModel, Field

OKX_CT_VAL: dict[str, float] = {
    "BTC-USDT-SWAP": 0.01,
    "ETH-USDT-SWAP": 0.1,
    "SOL-USDT-SWAP": 1.0,
}
"""合约乘数(张 → 币)。取自 OKX `/api/v5/public/instruments`,2026-07-11 实取,ctMult 均为 1。"""

LIQUIDATED_POSITION_SIDE: dict[str, str] = {"sell": "long", "buy": "short"}
"""强平订单方向 → 被强平仓位方向。`side='sell'` 是卖出平多 ⇒ 多头被强平。"""


class OkxLiquidationEvent(BaseModel):
    """一笔 OKX 强平事件(对应 `md.liquidations` 一行原值,未做任何换算)."""

    ts: datetime
    inst_id: str
    side: Literal["buy", "sell"] = Field(..., description="强平订单方向,非仓位方向")
    size: float = Field(..., ge=0.0, description="OKX `sz` 原值 = 合约张数,不是币量")
    price: float = Field(..., gt=0.0)


class OkxLiquidationNotionalInput(BaseModel):
    """强平名义额流输入."""

    inst_id: str = Field(..., description="标的;所有 event 必须同标的,防止跨标的名义额相加")
    events: list[OkxLiquidationEvent]
    window_minutes: int = Field(5, ge=1, description="滚动窗口分钟数(LER T1 用 5m)")


class OkxLiquidationNotionalResult(BaseModel):
    """强平名义额流结果(USD,已按 ctVal 换算)."""

    inst_id: str
    ct_val: float = Field(..., description="本次换算实际使用的合约乘数,供 fingerprint 记录")
    minutes: list[datetime] = Field(
        ..., description="连续 1m 时间网格(无事件的分钟补 0,不前向填充)"
    )
    long_liq_1m: list[float] = Field(..., description="每分钟多头被强平名义额(side='sell')")
    short_liq_1m: list[float] = Field(..., description="每分钟空头被强平名义额(side='buy')")
    long_liq_rolling: list[float] = Field(..., description="多头爆仓 W 分钟滚动名义额")
    short_liq_rolling: list[float] = Field(..., description="空头爆仓 W 分钟滚动名义额")
    total_long_notional: float
    total_short_notional: float
    n_events: int


def okx_liquidation_notional(*, data: OkxLiquidationNotionalInput) -> OkxLiquidationNotionalResult:
    """把 OKX 逐笔强平事件换算成 1m / 滚动 W 分钟的多空名义额流.

    名义额 = `size × ctVal × price`(§5.1.1 C1);多空按 `side` 反向映射(§5.1.1 C2)。
    无事件的分钟补 **0**——那一分钟确实没有强制流,不是"沿用上一分钟"。

    Args:
        data: 标的 + 逐笔强平事件 + 滚动窗口分钟数.

    Returns:
        OkxLiquidationNotionalResult: 多空 1m 名义额与 W 分钟滚动和(USD).

    Raises:
        ValueError: events 为空;inst_id 不在 `OKX_CT_VAL` 中(拒绝静默兜底);
            event 的 inst_id 与 `data.inst_id` 不一致.

    Example:
        >>> from datetime import datetime
        >>> data = OkxLiquidationNotionalInput(
        ...     inst_id="BTC-USDT-SWAP",
        ...     events=[OkxLiquidationEvent(
        ...         ts=datetime(2026, 7, 11, 0, 0), inst_id="BTC-USDT-SWAP",
        ...         side="sell", size=100, price=100_000,
        ...     )],
        ... )
        >>> result = okx_liquidation_notional(data=data)
        >>> result.total_long_notional  # 100 张 × 0.01 BTC/张 × $100k,不是 $10M
        100000.0
    """
    if not data.events:
        raise ValueError("events 不能为空")
    if data.inst_id not in OKX_CT_VAL:
        raise ValueError(
            f"未知 instId {data.inst_id!r},无合约乘数。已知: {sorted(OKX_CT_VAL)}。"
            "拒绝按 ctVal=1 兜底——那会使名义额静默失真(BTC 达 100×)"
        )
    ct_val = OKX_CT_VAL[data.inst_id]

    mismatched = {e.inst_id for e in data.events if e.inst_id != data.inst_id}
    if mismatched:
        raise ValueError(
            f"events 含其它标的 {sorted(mismatched)},与 inst_id={data.inst_id!r} 不符;"
            "跨标的名义额不可相加(ctVal 不同)"
        )

    rows = [
        {
            "minute": e.ts.replace(second=0, microsecond=0),
            "side": LIQUIDATED_POSITION_SIDE[e.side],
            "notional": e.size * ct_val * e.price,
        }
        for e in data.events
    ]
    df = pd.DataFrame(rows)

    # 连续 1m 网格:缺失的分钟是"零强制流",补 0 而非前向填充
    grid = pd.date_range(df["minute"].min(), df["minute"].max(), freq="1min")
    per_side = (
        df.pivot_table(index="minute", columns="side", values="notional", aggfunc="sum")
        .reindex(grid, fill_value=0.0)
        .fillna(0.0)
    )
    for side in ("long", "short"):
        if side not in per_side.columns:
            per_side[side] = 0.0

    w = data.window_minutes
    rolling = {
        side: rolling_window_aggregate(series=per_side[side], window=w, agg="sum", min_periods=1)
        for side in ("long", "short")
    }

    return OkxLiquidationNotionalResult(
        inst_id=data.inst_id,
        ct_val=ct_val,
        minutes=[ts.to_pydatetime() for ts in grid],
        long_liq_1m=[float(v) for v in per_side["long"]],
        short_liq_1m=[float(v) for v in per_side["short"]],
        long_liq_rolling=[float(v) for v in rolling["long"]],
        short_liq_rolling=[float(v) for v in rolling["short"]],
        total_long_notional=float(per_side["long"].sum()),
        total_short_notional=float(per_side["short"].sum()),
        n_events=len(data.events),
    )
