"""oskill.bandit_router — Thompson sampling bandit 路由 (freellmapi 机制 3O 内化)。

路由从"规则"升"学习": 每个 provider 维护 Beta(alpha, beta) 分布, 按采样选
最佳 provider (freellmapi 的 Thompson-sampling bandit 机制层):
  * **record_observation** — 成功 (reward=1) / 失败 (reward=0) / 延迟归一化
    奖励 (0-1);
  * **sample_best** — 按 Beta 分布采样选 provider (探索与利用平衡);
  * **BanditRouter** — 选择 + 更新 + 探索率 (epsilon);
  * 与 model_routing 组合: bandit 作为路由策略替代静态优先级。

零 vey a 反向依赖: 纯随机采样 (random, 可种子)。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


def _sample_beta(alpha: float, beta: float) -> float:
    """Beta 分布采样 (Gamma 近似, 无第三方)。"""
    if alpha <= 0 or beta <= 0:
        return 0.5
    return random.gammavariate(alpha, 1) / (
        random.gammavariate(alpha, 1) + random.gammavariate(beta, 1)
    )


@dataclass
class BanditState:
    """单个 provider 的 bandit 状态。"""

    alpha: float = 1.0
    beta: float = 1.0
    observations: int = 0

    @property
    def success_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "observations": self.observations,
            "success_rate": round(self.success_rate, 3),
        }


class BanditRouter:
    """Thompson sampling 路由: 选 provider → 观测 → 更新分布。"""

    def __init__(self, *, epsilon: float = 0.1, seed: int | None = None) -> None:
        self.epsilon = epsilon
        self.states: dict[str, BanditState] = {}
        if seed is not None:
            random.seed(seed)

    def _state(self, provider: str) -> BanditState:
        if provider not in self.states:
            self.states[provider] = BanditState()
        return self.states[provider]

    def record(self, provider: str, reward: float) -> None:
        """记录一次观测: reward ∈ [0,1] (成功=1, 失败=0, 延迟归一化)。"""
        state = self._state(provider)
        reward = max(0.0, min(1.0, float(reward)))
        state.alpha += reward
        state.beta += 1.0 - reward
        state.observations += 1

    def sample_best(self, providers: list[str]) -> str:
        """按 Beta 分布采样选最佳 provider。

        Args:
            providers: 候选 provider 列表。

        Returns:
            选中的 provider (epsilon 概率随机探索)。
        """
        if not providers:
            raise ValueError("no providers to sample from")
        if random.random() < self.epsilon:
            return random.choice(providers)
        samples = {p: _sample_beta(self._state(p).alpha, self._state(p).beta) for p in providers}
        return max(samples, key=samples.get)

    def choose_and_observe(
        self,
        providers: list[str],
        executor: Any,
        *,
        reward_fn: Any = None,
    ) -> tuple[str, Any]:
        """选 provider → 执行 → 按结果奖励 (reward_fn 注入或默认 1/0)。

        Args:
            providers: 候选。
            executor: (provider) → 结果。
            reward_fn: (result) → reward; None 用 1 (成功) / 0 (异常)。

        Returns:
            (选中 provider, 结果)。
        """
        provider = self.sample_best(providers)
        try:
            result = executor(provider)
            reward = reward_fn(result) if reward_fn else 1.0
        except Exception:  # noqa: BLE001
            result = None
            reward = 0.0
        self.record(provider, reward)
        return provider, result

    def summary(self) -> dict[str, Any]:
        """各 provider 分布概览。"""
        return {p: s.to_dict() for p, s in self.states.items()}


__all__ = ["BanditRouter", "BanditState"]
