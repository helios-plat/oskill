"""3O 范式全栈 — 上下文压缩技能 (纯计算, 无 IO, stateless)."""

from __future__ import annotations


def truncate_history(history: list[dict], max_turns: int = 10) -> list[dict]:
    """技能 17: 上下文滑动窗口压缩。

    超出窗口时保留首条 (system prompt) 与最近 max_turns-1 条。
    """
    if len(history) <= max_turns:
        return history
    # 保留 system prompt 和最近的回合
    return [history[0]] + history[-(max_turns - 1) :]
