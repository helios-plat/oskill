"""oskill.mcts_thought_planner — 基于蒙特卡洛树搜索 (MCTS) 的 System-2 深度推演.

在内部世界模型中模拟演练 N 条推演分支，评估并选择胜率最高的最优 Action
序列。stateless，LLM Protocol 注入。

Example:
    >>> r = mcts_thought_planner("发布新版本", llm_caller=llm, num_simulations=3)
    >>> r["evaluated_paths"] >= 0
    True
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class LLMCallerProtocol(Protocol):
    """LLM 调用协议。"""

    def __call__(self, prompt: str, *, temperature: float = 0.7) -> str: ...


def mcts_thought_planner(
    task_goal: str,
    *,
    llm_caller: LLMCallerProtocol,
    rollout_depth: int = 3,
    num_simulations: int = 5,
) -> dict[str, Any]:
    """MCTS 式推演规划。

    Args:
        task_goal: 任务目标。
        llm_caller: LLM 调用器（注入）。
        rollout_depth: 单分支推演步数。
        num_simulations: 模拟分支数。

    Returns:
        {"best_plan": [str], "confidence": float|None,
         "evaluated_paths": int}

    Raises:
        OskillError: task_goal 为空 / llm_caller 未注入 / 参数非法。
    """
    if not task_goal or not task_goal.strip():
        raise OskillError("mcts_thought_planner: task_goal must not be empty")
    if llm_caller is None:
        raise OskillError("mcts_thought_planner: llm_caller must be injected")
    if rollout_depth < 1 or num_simulations < 1:
        raise OskillError("mcts_thought_planner: rollout_depth/num_simulations must be >= 1")

    candidate_paths: list[dict[str, Any]] = []
    for i in range(num_simulations):
        prompt = (
            f"Simulation Run #{i + 1} for Task Goal: {task_goal}\n"
            f"Simulate a {rollout_depth}-step action plan and evaluate risk (0.0 to 1.0).\n"
            'Reply JSON: {"plan": ["step1", "step2"], "risk_score": 0.1, "confidence": 0.9}'
        )
        try:
            raw = llm_caller(prompt, temperature=0.7)
        except Exception:  # noqa: BLE001 - 单次模拟失败跳过
            continue
        try:
            parsed = json.loads(raw if isinstance(raw, str) else str(raw))
            if isinstance(parsed, dict) and parsed.get("plan"):
                candidate_paths.append(parsed)
        except Exception:  # noqa: BLE001 - 解析失败跳过
            continue

    if not candidate_paths:
        return {"best_plan": [task_goal], "confidence": None, "evaluated_paths": 0}

    # 排序挑选置信度最高且风险最低的最佳路径
    best_path = sorted(
        candidate_paths,
        key=lambda x: float(x.get("confidence", 0)) - float(x.get("risk_score", 1)),
        reverse=True,
    )[0]
    return {
        "best_plan": list(best_path.get("plan", [])),
        "confidence": best_path.get("confidence"),
        "evaluated_paths": len(candidate_paths),
    }
