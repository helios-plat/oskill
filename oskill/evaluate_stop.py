"""3O 范式全栈 — 停止条件评估技能 (纯计算, 无 IO, stateless)."""

from __future__ import annotations


def evaluate_stop_condition(parsed_intent: dict, current_turn: int, max_turns: int = 15) -> bool:
    """技能 19: 停止条件评估。

    达到回合上限或意图为 final_answer 时停止。
    """
    if current_turn >= max_turns:
        return True
    return parsed_intent.get("tool_name") == "final_answer"
