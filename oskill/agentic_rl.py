"""oskill.agentic_rl — Agentic-RL 训练管线机制 (hello-agents 第11章 3O 内化)。

LLM 训练层的确定性机制 (SFT → RM → RL → 评估):
  * **RewardRule** — 确定性奖励规则: exact_match / contains / format /
    length (答案正确 +1 错误 0 等);
  * **compute_reward** — 按规则计算回答奖励;
  * **grpo_advantages** — GRPO 组内相对优势: (reward - 组均值) / 组标准差
    (baseline 归一化, 确定性);
  * **TrainStage** — 阶段机: SFT → RM → RL → EVAL (评估门通过才推进)。
零 veya 反向依赖: 纯计算; 训练执行由调用方注入。
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

STAGE_SFT = "SFT"
STAGE_RM = "RM"
STAGE_RL = "RL"
STAGE_EVAL = "EVAL"
STAGES = (STAGE_SFT, STAGE_RM, STAGE_RL, STAGE_EVAL)

RULE_EXACT = "exact_match"
RULE_CONTAINS = "contains"
RULE_FORMAT = "format"
RULE_LENGTH = "length"


@dataclass(frozen=True)
class RewardRule:
    """一条确定性奖励规则。

    Attributes:
        kind: exact_match / contains / format / length。
        expected: exact/contains 的目标文本。
        pattern: format 的正则。
        min_len / max_len: length 边界。
        reward: 命中奖励 (默认 1.0)。
        penalty: 未命中惩罚 (默认 0.0)。
    """

    kind: str
    expected: str = ""
    pattern: str = ""
    min_len: int = 0
    max_len: int = 0
    reward: float = 1.0
    penalty: float = 0.0


def compute_reward(response: str, rules: list[RewardRule]) -> float:
    """按规则计算回答总奖励 (命中累加 reward, 未命中累加 penalty)。

    Args:
        response: 模型回答。
        rules: 奖励规则。

    Returns:
        总奖励。

    Example:
        >>> compute_reward("42", [RewardRule(RULE_EXACT, expected="42")])
        1.0
    """
    total = 0.0
    for rule in rules:
        if _rule_hit(rule, response):
            total += rule.reward
        else:
            total += rule.penalty
    return total


def _rule_hit(rule: RewardRule, response: str) -> bool:
    if rule.kind == RULE_EXACT:
        return response.strip() == rule.expected.strip()
    if rule.kind == RULE_CONTAINS:
        return rule.expected in response
    if rule.kind == RULE_FORMAT:
        return bool(re.search(rule.pattern, response))
    if rule.kind == RULE_LENGTH:
        if rule.max_len <= 0:  # max_len=0 表示无上限
            return len(response) >= rule.min_len
        return rule.min_len <= len(response) <= rule.max_len
    return False


def grpo_advantages(group_rewards: list[float]) -> list[float]:
    """GRPO 组内相对优势: (r - 组均值) / 组标准差。

    Args:
        group_rewards: 同一 prompt 的多个候选奖励。

    Returns:
        每个候选的优势值 (组内归一化)。

    Example:
        >>> a = grpo_advantages([1.0, 0.0, 1.0])
        >>> len(a) == 3
        True
    """
    if not group_rewards:
        return []
    mean = statistics.fmean(group_rewards)
    stdev = statistics.stdev(group_rewards) if len(group_rewards) > 1 else 0.0
    if stdev == 0:
        return [0.0] * len(group_rewards)
    return [(r - mean) / stdev for r in group_rewards]


@dataclass
class TrainState:
    """训练管线状态。"""

    stage: str = STAGE_SFT
    history: list[str] = field(default_factory=list)
    eval_scores: dict[str, float] = field(default_factory=dict)


class TrainPipeline:
    """SFT → RM → RL → EVAL 阶段机 (评估门推进)。"""

    def __init__(self, *, eval_threshold: float = 0.7) -> None:
        self.state = TrainState()
        self.eval_threshold = eval_threshold

    def current(self) -> str:
        return self.state.stage

    def next_stage(self) -> str | None:
        """下一阶段 (SFT→RM→RL→EVAL→None)。"""
        idx = STAGES.index(self.state.stage)
        return STAGES[idx + 1] if idx + 1 < len(STAGES) else None

    def advance(self, *, eval_score: float | None = None) -> dict[str, Any]:
        """推进阶段; EVAL→RL 需 eval_score >= 阈值 (评估门)。

        Args:
            eval_score: 评估分数 (EVAL 阶段推进时必填)。

        Returns:
            {stage, next, ok, reason}。

        Raises:
            ValueError: 非法推进 (EVAL 未达阈值/已到终态)。
        """
        next_stage = self.next_stage()
        if self.state.stage == STAGE_EVAL:
            if eval_score is None:
                raise ValueError("eval_score required to advance from EVAL")
            if eval_score < self.eval_threshold:
                return {
                    "stage": self.state.stage,
                    "next": next_stage,
                    "ok": False,
                    "reason": (f"eval_score {eval_score} < threshold {self.eval_threshold}"),
                }
            # 评估门通过: 终态完成
            self.state.history.append("EVAL_DONE")
            return {
                "stage": self.state.stage,
                "next": None,
                "ok": True,
                "reason": "eval passed, training complete",
            }
        if next_stage is None:
            raise ValueError("already at final stage")
        self.state.stage = next_stage
        self.state.history.append(next_stage)
        return {"stage": next_stage, "next": self.next_stage(), "ok": True, "reason": "advanced"}

    def record_eval(self, metric: str, score: float) -> None:
        """记录评估指标。"""
        self.state.eval_scores[metric] = score

    def summary(self) -> dict[str, Any]:
        return {
            "stage": self.state.stage,
            "history": self.state.history,
            "eval_scores": self.state.eval_scores,
        }


__all__ = [
    "RULE_CONTAINS",
    "RULE_EXACT",
    "RULE_FORMAT",
    "RULE_LENGTH",
    "RewardRule",
    "STAGE_EVAL",
    "STAGE_RL",
    "STAGE_RM",
    "STAGE_SFT",
    "STAGES",
    "TrainPipeline",
    "TrainState",
    "compute_reward",
    "grpo_advantages",
]
