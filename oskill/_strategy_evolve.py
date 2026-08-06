"""Long-horizon strategy evolution (Phase 4).

Maintains value estimates for a fixed set of high-level repair strategies and
evolves them from closed-loop outcomes:

    value_s ← (1 − α)·value_s + α·reward_s        (EMA)

Selection is ε-greedy with a hard threat override: above a threat ceiling the
system *must* quarantine regardless of learned preferences (security by
default). Each strategy maps to planner parameters (horizon / cost sensitivity
/ min-effective-Δ / exploration bonus / observe-first), so the strategy choice
dynamically reconfigures the counterfactual planner.

Strategies
----------
- aggressive_repair   : deep horizon, cheap repairs, low Δ bar — fix everything.
- conservative_isolate: shallow horizon, expensive repairs, high Δ bar — only
                        touch nodes with strong evidence.
- observe_first       : gather information before acting (explore bonus on
                        CPD uncertainty, optional observe action).
- quarantine          : highest-threat response — single decisive isolation
                        action, cost-insensitive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

__all__ = [
    "STRATEGY_NAMES",
    "STRATEGY_PARAMS",
    "StrategyRecord",
    "StrategyEvolver",
]

STRATEGY_NAMES: list[str] = [
    "aggressive_repair",
    "conservative_isolate",
    "observe_first",
    "quarantine",
]

# 策略 → 规划器参数（multi_step_plan 据此动态配置 horizon / 成本敏感度）
STRATEGY_PARAMS: dict[str, dict[str, Any]] = {
    "aggressive_repair": {
        "horizon": 3,
        "cost_lambda": 0.02,
        "min_effective_delta": 0.05,
        "explore_bonus": 0.0,
        "allow_observe": False,
    },
    "conservative_isolate": {
        "horizon": 2,
        "cost_lambda": 0.15,
        "min_effective_delta": 0.10,
        "explore_bonus": 0.0,
        "allow_observe": False,
    },
    "observe_first": {
        "horizon": 1,
        "cost_lambda": 0.10,
        "min_effective_delta": 0.03,
        "explore_bonus": 0.25,
        "allow_observe": True,
    },
    "quarantine": {
        "horizon": 1,
        "cost_lambda": 0.0,
        "min_effective_delta": 0.0,
        "explore_bonus": 0.0,
        "allow_observe": False,
    },
}

# 威胁水平硬覆盖阈值: ≥ 此值强制 quarantine（不探索、不学偏好）
THREAT_CAP_DEFAULT = 0.8


@dataclass
class StrategyRecord:
    value: float = 0.0
    count: int = 0
    total_reward: float = 0.0


class StrategyEvolver:
    """EMA value evolution + ε-greedy selection with threat hard cap."""

    def __init__(
        self,
        strategies: Optional[List[str]] = None,
        initial_value: float = 0.0,
        alpha: float = 0.3,
        epsilon: float = 0.1,
        threat_cap: float = THREAT_CAP_DEFAULT,
    ) -> None:
        names = list(strategies) if strategies is not None else list(STRATEGY_NAMES)
        self.records: Dict[str, StrategyRecord] = {
            s: StrategyRecord(value=float(initial_value)) for s in names
        }
        self.alpha = float(alpha)
        self.epsilon = float(epsilon)
        self.threat_cap = float(threat_cap)
        self.history: List[Dict[str, Any]] = []

    # ── 选择 ─────────────────────────────────────────────────────────
    def select(self, threat_level: float = 0.0, rng: Optional[np.random.Generator] = None) -> str:
        """ε-greedy strategy choice; threat override forces quarantine."""
        if threat_level >= self.threat_cap:
            return "quarantine"
        rng = rng or np.random.default_rng()
        if rng.random() < self.epsilon:
            return str(rng.choice(list(self.records)))
        return self.best()

    def best(self) -> str:
        return max(self.records, key=lambda s: self.records[s].value)

    # ── 学习 ─────────────────────────────────────────────────────────
    def update(self, strategy: str, reward: float) -> float:
        """EMA value update from a closed-loop reward; returns new value."""
        rec = self.records[strategy]
        rec.count += 1
        rec.total_reward += float(reward)
        rec.value = (1.0 - self.alpha) * rec.value + self.alpha * float(reward)
        self.history.append(
            {
                "strategy": strategy,
                "reward": float(reward),
                "value_after": rec.value,
            }
        )
        return rec.value

    # ── 参数映射 ─────────────────────────────────────────────────────
    def parameters_for(self, strategy: str) -> Dict[str, Any]:
        """Planner parameters for a strategy (horizon / cost sensitivity / ...)."""
        if strategy not in STRATEGY_PARAMS:
            raise KeyError(f"未知策略: {strategy!r}; 可选 {list(STRATEGY_PARAMS)}")
        return dict(STRATEGY_PARAMS[strategy])

    # ── 序列化 ───────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": self.alpha,
            "epsilon": self.epsilon,
            "threat_cap": self.threat_cap,
            "records": {
                s: {"value": r.value, "count": r.count, "total_reward": r.total_reward}
                for s, r in self.records.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyEvolver":
        ev = cls(
            strategies=list(data["records"]),
            alpha=data.get("alpha", 0.3),
            epsilon=data.get("epsilon", 0.1),
            threat_cap=data.get("threat_cap", THREAT_CAP_DEFAULT),
        )
        for s, r in data["records"].items():
            ev.records[s] = StrategyRecord(
                value=float(r["value"]),
                count=int(r.get("count", 0)),
                total_reward=float(r.get("total_reward", 0.0)),
            )
        return ev
