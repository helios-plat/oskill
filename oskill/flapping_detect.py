"""flapping_detect — 自愈抖动检测 (aegis DESIGN §5.3).

Composition note: pure algorithm, no I/O. 阈值(window/threshold)为可注入参数,
业务知识不焊死(默认 30min/2 次,调用方可覆盖)。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel


class FlapVerdict(BaseModel):
    target: str
    heals_in_window: int
    is_flapping: bool
    window_seconds: int
    threshold: int


def flapping_detect(
    *,
    target: str,
    heal_history: list[datetime],
    now: datetime,
    window_seconds: int = 1800,
    threshold: int = 2,
) -> FlapVerdict:
    """同一目标在 window 内自愈次数 >= threshold(且仍异常)→ is_flapping。

    调用方 MUST 在 is_flapping 时停止对该目标的自愈并升级人工(DESIGN §5.3)。

    Args:
        target: 目标标识(容器/服务/节点)。
        heal_history: 该目标历史自愈时刻列表。
        now: 当前时刻(与 heal_history 同一时区语义)。
        window_seconds: 回看窗口秒(默认 1800=30min,可注入覆盖)。
        threshold: 判定抖动的次数阈值(默认 2,可注入覆盖)。

    Returns:
        FlapVerdict(heals_in_window / is_flapping / window_seconds / threshold)。
    """
    cutoff = now - timedelta(seconds=window_seconds)
    heals_in_window = sum(1 for h in heal_history if h >= cutoff)
    return FlapVerdict(
        target=target,
        heals_in_window=heals_in_window,
        is_flapping=heals_in_window >= threshold,
        window_seconds=window_seconds,
        threshold=threshold,
    )
