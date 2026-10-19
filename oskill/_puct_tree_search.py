"""oskill._puct_tree_search — PUCT (Predictor + UCT) 蒙特卡洛树搜索算法.

Stateless 纯算法。依赖 OracleProtocol (评估器) + LLMCallerProtocol (先验策略) 注入.

组合: oracle (注入) + LLM caller (注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.

算法: PUCT = UCT + prior probability P(s,a) from policy network/LLM.
"""

from __future__ import annotations

import math
from typing import Any, Protocol


class OracleProtocol(Protocol):
    """状态评估器 Protocol."""

    def __call__(self, state_id: str) -> dict[str, Any]: ...  # {"reward": float, "terminal": bool}


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol (提供先验策略)."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def _puct_tree_search(
    root_state_id: str,
    *,
    oracle_evaluator: OracleProtocol,
    llm_caller: LLMCallerProtocol,
    max_simulations: int = 100,
    exploration_constant: float = 1.414,
) -> dict[str, Any]:
    """PUCT 蒙特卡洛树搜索 —— 在状态空间中寻找最优路径.

    公式:
        PUCT(s, a) = Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))

    其中:
    - Q(s,a): 平均回报
    - P(s,a): 先验概率（来自 LLM 策略）
    - N(s), N(s,a): 访问计数
    - c_puct: 探索常数

    Args:
        root_state_id: 根状态标识
        oracle_evaluator: 状态评估器（注入）
        llm_caller: 先验策略提供者（注入）
        max_simulations: 最大模拟次数
        exploration_constant: PUCT 探索常数

    Returns:
        {
            "best_path": list[str],
            "best_reward": float,
            "simulations": int,
            "tree_size": int,
        }
    """
    # PUCT 树结构: state_id → {visits, children: {action → {state, visits, reward, prior}}}
    tree: dict[str, dict[str, Any]] = {}

    def _get_node(state_id: str) -> dict[str, Any]:
        if state_id not in tree:
            tree[state_id] = {
                "visits": 0,
                "total_reward": 0.0,
                "children": {},
            }
        return tree[state_id]

    def _select(state_id: str) -> list[str]:
        """从根选择到叶节点的路径."""
        path = [state_id]
        node = _get_node(state_id)
        while node["children"]:
            # 选最大 PUCT 值的动作
            best_action = None
            best_value = -float("inf")
            total_visits = node["visits"]

            for action, child in node["children"].items():
                q = child["reward"] / max(child["visits"], 1)
                u = (
                    exploration_constant
                    * child.get("prior", 1.0)
                    * math.sqrt(max(total_visits, 1))
                    / (1 + child["visits"])
                )
                puct = q + u
                if puct > best_value:
                    best_value = puct
                    best_action = action

            if best_action is None:
                break
            path.append(best_action)
            state_id = node["children"][best_action]["state"]
            node = _get_node(state_id)
        return path

    def _expand(state_id: str) -> list[str]:
        """扩展叶节点 —— 获取 LLM 先验策略生成候选动作."""
        try:
            prompt = (
                f"State: {state_id}\n"
                f"Generate 3-5 next possible actions as a JSON array of strings. "
                f"Reply with ONLY the JSON array."
            )
            import json

            raw = llm_caller(prompt, temperature=0.1).strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("json\n", "").strip()
            actions = json.loads(raw) if raw.startswith("[") else [f"action_{i}" for i in range(3)]
        except Exception:
            actions = [f"action_{i}" for i in range(3)]

        node = _get_node(state_id)
        for action in actions:
            child_state = f"{state_id}→{action}"
            if action not in node["children"]:
                node["children"][action] = {
                    "state": child_state,
                    "visits": 0,
                    "reward": 0.0,
                    "prior": 1.0 / max(len(actions), 1),
                }
        return actions

    def _simulate(state_id: str) -> float:
        """模拟：评估叶节点."""
        try:
            result = oracle_evaluator(state_id)
            return result.get("reward", 0.0)
        except Exception:
            return 0.0

    def _backpropagate(path: list[str], reward: float) -> None:
        """回传奖励."""
        for state_id in path:
            node = _get_node(state_id)
            node["visits"] += 1
            node["total_reward"] += reward

    # 主循环
    simulations = 0
    for _ in range(max_simulations):
        try:
            # 1. 选择
            path = _select(root_state_id)
            leaf = path[-1]

            # 2. 扩展
            _expand(leaf)

            # 3. 模拟
            reward = _simulate(leaf)

            # 4. 回传
            _backpropagate(path, reward)
            simulations += 1
        except Exception:
            break

    # 选择最优路径
    root = _get_node(root_state_id)
    best_action = None
    best_reward = -float("inf")
    for action, child in root.get("children", {}).items():
        avg_reward = child["reward"] / max(child["visits"], 1)
        if avg_reward > best_reward:
            best_reward = avg_reward
            best_action = action

    tree_size = len(tree)

    return {
        "best_path": [root_state_id, best_action] if best_action else [root_state_id],
        "best_reward": best_reward if best_reward > -float("inf") else 0.0,
        "simulations": simulations,
        "tree_size": tree_size,
    }
