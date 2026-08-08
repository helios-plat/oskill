"""oskill.health_probe — 服务健康探测 (freellmapi health 机制 3O 内化)。

周期性探测 key/服务状态 (freellmapi 健康服务机制层):
  * **ProbeResult** — healthy / rate_limited / invalid / error 状态;
  * **HealthProbe** — 单目标探测: 探测函数注入, 状态机 + 冷却;
  * **HealthMonitor** — 多目标监控: 周期轮询, 跳过死目标, 汇总。
零 veya 反向依赖: 探测函数注入; 纯状态机。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

STATUS_HEALTHY = "healthy"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_INVALID = "invalid"
STATUS_ERROR = "error"
STATUSES = (STATUS_HEALTHY, STATUS_RATE_LIMITED, STATUS_INVALID, STATUS_ERROR)

ProbeFn = Callable[[], str]
"""探测函数: () → 状态字符串 (healthy/rate_limited/invalid/error)。"""


@dataclass
class ProbeState:
    """单个目标的探测状态。"""

    name: str
    status: str = "unknown"
    observations: int = 0
    cooldown_until: float = 0.0
    last_ts: float = 0.0
    consecutive_errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "observations": self.observations,
            "cooldown_until": self.cooldown_until,
        }


class HealthProbe:
    """单目标健康探测 (探测 + 状态机 + 冷却)。"""

    def __init__(self, name: str, probe_fn: ProbeFn, *, cooldown_s: float = 60.0) -> None:
        self.name = name
        self.probe_fn = probe_fn
        self.cooldown_s = cooldown_s
        self.state = ProbeState(name=name)

    def probe(self, *, now: float | None = None) -> str:
        """执行一次探测 (冷却期内跳过)。"""
        now = now or time.time()
        if now < self.state.cooldown_until:
            return self.state.status  # 冷却中, 复用上次状态
        try:
            status = self.probe_fn()
        except Exception:  # noqa: BLE001
            status = STATUS_ERROR
        self.state.status = status
        self.state.observations += 1
        self.state.last_ts = now
        if status in (STATUS_RATE_LIMITED, STATUS_INVALID, STATUS_ERROR):
            self.state.consecutive_errors += 1
            # 冷却: 失败后暂缓再次探测
            self.state.cooldown_until = now + self.cooldown_s * min(
                self.state.consecutive_errors, 5
            )
        else:
            self.state.consecutive_errors = 0
        return status

    def should_skip(self) -> bool:
        """是否应跳过 (冷却中 / 状态无效)。"""
        return self.state.status in (STATUS_INVALID,) or time.time() < self.state.cooldown_until


class HealthMonitor:
    """多目标健康监控: 周期轮询 + 汇总。"""

    def __init__(self) -> None:
        self.probes: dict[str, HealthProbe] = {}

    def register(self, probe: HealthProbe) -> None:
        self.probes[probe.name] = probe

    def run_once(self) -> dict[str, Any]:
        """执行一轮探测 (跳过冷却中目标)。"""
        for probe in self.probes.values():
            if not probe.should_skip():
                probe.probe()
        return self.summary()

    def healthy(self) -> list[str]:
        return [n for n, p in self.probes.items() if p.state.status == STATUS_HEALTHY]

    def summary(self) -> dict[str, Any]:
        return {
            "probes": {n: p.state.to_dict() for n, p in self.probes.items()},
            "healthy": self.healthy(),
            "counts": {
                s: sum(1 for p in self.probes.values() if p.state.status == s) for s in STATUSES
            },
        }


__all__ = [
    "HealthMonitor",
    "HealthProbe",
    "ProbeState",
    "STATUS_ERROR",
    "STATUS_HEALTHY",
    "STATUS_INVALID",
    "STATUS_RATE_LIMITED",
    "STATUSES",
]
