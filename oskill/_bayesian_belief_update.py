"""oskill._bayesian_belief_update — Bayesian Theory-of-Mind belief updater.

3O layer: oskill (stateless composite skill over oprim numerics).
Maintains a belief vector over the hidden intents of an interaction partner
(user or third-party agent). Every observed action E updates the posterior via
Bayes' theorem — pure NumPy matrix math, no LLM "empathy guessing":

    P(H | E) = P(E | H) · P(H) / Σ_i P(E | H_i) · P(H_i)

When P(malicious | evidence) crosses a safety threshold the caller (omodul
adversarial transaction / host) cuts the partner's privileged API access.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "BayesianBeliefUpdater",
    "_bayesian_belief_update",
    "sequential_update",
    "DEFAULT_HYPOTHESES",
]


# 默认隐藏意图假设空间: [合作, 中立, 受挫, 恶意]
DEFAULT_HYPOTHESES: list[str] = ["cooperative", "neutral", "frustrated", "malicious"]


def _bayesian_belief_update(
    prior: np.ndarray | list[float],
    likelihood: np.ndarray | list[float] | list[list[float]],
) -> np.ndarray:
    """纯函数式贝叶斯信念更新。

    Parameters
    ----------
    prior : shape (k,) 先验 P(H)
    likelihood : P(E|H) 向量 (k,) — 或矩阵 (n_obs, k)：此时按独立证据
                 乘积更新(等价于逐条顺序更新)。

    Returns
    -------
    归一化后验 P(H|E), shape (k,)。
    """
    prior = np.asarray(prior, dtype=np.float64)
    likelihood = np.asarray(likelihood, dtype=np.float64)
    if prior.ndim != 1:
        raise ValueError(f"prior 必须是一维向量, 收到 shape {prior.shape}")
    if likelihood.ndim == 1:
        if likelihood.shape != prior.shape:
            raise ValueError(
                f"likelihood 形状 {likelihood.shape} 与 prior {prior.shape} 不匹配"
            )
        unnorm = prior * likelihood
    elif likelihood.ndim == 2:
        if likelihood.shape[1] != prior.shape[0]:
            raise ValueError(
                f"likelihood 矩阵列数 {likelihood.shape[1]} 与 prior 长度 {prior.shape[0]} 不匹配"
            )
        # 独立证据联合似然 = 逐行乘积 (与 sequential_update 数学等价)
        unnorm = prior * likelihood.prod(axis=0)
    else:
        raise ValueError(f"likelihood 维度必须为 1 或 2, 收到 {likelihood.ndim}")
    if np.any(unnorm < 0):
        raise ValueError("likelihood/prior 含负值: 概率不允许为负")
    total = float(unnorm.sum())
    if total <= 0:
        raise ValueError("likelihood 全零: 观测在全部状态下概率为 0, 无法归一化")
    return unnorm / total


def sequential_update(
    prior: np.ndarray | list[float],
    likelihoods: list[np.ndarray | list[float]],
) -> np.ndarray:
    """按证据序列逐条更新, 返回最终后验 (等价于批量乘积)。"""
    post = np.asarray(prior, dtype=np.float64).copy()
    for lik in likelihoods:
        post = _bayesian_belief_update(post, lik)
    return post


class BayesianBeliefUpdater:
    """Hidden-intent belief vector with single/batch/sequence Bayesian updates."""

    def __init__(
        self,
        states: list[str],
        prior: list[float] | np.ndarray | None = None,
    ) -> None:
        """
        Args:
            states: hidden states, e.g. ["benign", "malicious"].
            prior: initial belief vector (default uniform).
        """
        self.states = list(states)
        k = len(self.states)
        if k == 0:
            raise ValueError("states 不能为空")
        if prior is None:
            prior = np.full(k, 1.0 / k)
        prior = np.asarray(prior, dtype=float)
        if prior.shape != (k,):
            raise ValueError(f"prior 形状必须为 ({k},), 收到 {prior.shape}")
        if prior.sum() <= 0 or np.any(prior < 0):
            raise ValueError("prior 必须是非负且总和为正的概率向量")
        self._prior: np.ndarray = prior / prior.sum()
        self._posterior: np.ndarray = self._prior.copy()
        self._history: list[np.ndarray] = [self._prior.copy()]

    # ── 属性 ─────────────────────────────────────────────────────────
    @property
    def posterior(self) -> np.ndarray:
        """当前后验信念向量 (与 self.states 对齐)。"""
        return self._posterior.copy()

    def belief(self, state: str) -> float:
        """查询某个隐藏状态的后验概率。"""
        return float(self._posterior[self.states.index(state)])

    def reset(self) -> None:
        """重置为先验。"""
        self._posterior = self._prior.copy()
        self._history = [self._prior.copy()]

    # ── 更新 ─────────────────────────────────────────────────────────
    def update(self, likelihood: list[float] | np.ndarray) -> np.ndarray:
        """单次观测更新: likelihood = P(E | H_i) 向量 (每个隐藏状态下观测到 E 的概率)。"""
        lik = np.asarray(likelihood, dtype=float)
        if lik.shape != (len(self.states),):
            raise ValueError(f"likelihood 形状必须为 ({len(self.states)},), 收到 {lik.shape}")
        if np.any(lik < 0):
            raise ValueError("likelihood 必须非负")
        unnorm = self._posterior * lik
        total = float(unnorm.sum())
        if total <= 0:
            raise ValueError("likelihood 全零: 观测在全部状态下概率为 0, 信念无法归一化")
        self._posterior = unnorm / total
        self._history.append(self._posterior.copy())
        return self._posterior.copy()

    def update_batch(self, likelihood_matrix: list[list[float]] | np.ndarray) -> np.ndarray:
        """批量观测更新: 行 = 观测, 列 = 隐藏状态 (逐行连续贝叶斯更新)。"""
        mat = np.asarray(likelihood_matrix, dtype=float)
        if mat.ndim != 2 or mat.shape[1] != len(self.states):
            raise ValueError(f"likelihood_matrix 形状必须为 (n_obs, {len(self.states)})")
        for row in mat:
            self.update(row)
        return self._posterior.copy()

    def sequence_update(self, likelihoods: list[list[float] | np.ndarray]) -> list[np.ndarray]:
        """连续多观测更新, 返回每一步的后验 (供阈值监控/测试断言)。"""
        trail: list[np.ndarray] = []
        for lik in likelihoods:
            trail.append(self.update(lik))
        return trail

    def dominates(self, state: str, threshold: float = 0.9) -> bool:
        """某个隐藏状态的后验是否突破阈值 (如 P(malicious) > 0.9)。"""
        return self.belief(state) >= threshold
