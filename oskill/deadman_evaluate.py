"""deadman_evaluate — 预期心跳静默判定 (aegis DESIGN §3.1 cron dead-man / §6).

Composition note: pure algorithm, no I/O. cron 型负载(挂掉比容器隐蔽)与节点心跳共用,
机制与 §6 L1 外部死人开关同构:到期未心跳即 silent。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel


class DeadmanVerdict(BaseModel):
    subject: str
    ever_seen: bool
    silent: bool
    overdue_seconds: float  # 超过 deadline 的秒数(<=0 未超期);ever_seen=False 时为 0.0


def deadman_evaluate(
    *,
    subject: str,
    last_seen: datetime | None,
    expected_interval_seconds: float,
    now: datetime,
    grace_seconds: float = 0.0,
) -> DeadmanVerdict:
    """last_seen 距 now 超过 expected_interval+grace 即 silent(静默)。

    从未见(last_seen=None)→ silent=True、ever_seen=False。

    Args:
        subject: 被监控主体(cron 任务/采集器/节点)。
        last_seen: 最近一次心跳时刻;None=从未见。
        expected_interval_seconds: 预期心跳间隔秒。
        now: 当前时刻。
        grace_seconds: 宽限秒(避免临界抖动误报),默认 0。

    Returns:
        DeadmanVerdict(ever_seen / silent / overdue_seconds)。
    """
    if last_seen is None:
        return DeadmanVerdict(subject=subject, ever_seen=False, silent=True, overdue_seconds=0.0)

    deadline = last_seen + timedelta(seconds=expected_interval_seconds + grace_seconds)
    overdue = (now - deadline).total_seconds()
    return DeadmanVerdict(
        subject=subject,
        ever_seen=True,
        silent=overdue > 0,
        overdue_seconds=overdue,
    )
