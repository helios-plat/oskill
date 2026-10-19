"""oskill.long_context_compress — 针对超长历史的上下文增量压缩算法.

Stateless 纯算法。依赖 LLMCallerProtocol 注入（不在顶层 import oprim）.

组合: LLM caller (依赖注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol — 不 import oprim，由调用方注入."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def long_context_compress(
    history_steps: list[dict[str, Any]],
    *,
    llm_caller: LLMCallerProtocol,
    max_keep_recent: int = 5,
) -> dict[str, Any]:
    """针对长程运行历史的上下文增量压缩算法 (Stateless).

    将旧的执行步骤压缩为摘要，保留最近步骤完整。

    Args:
        history_steps: 历史步骤列表
        llm_caller: LLM 调用接口（注入）
        max_keep_recent: 保留最近步骤数

    Returns:
        {
            "compressed": bool,
            "compacted_history": list[dict],
            "saved_tokens_est": int,
        }
    """
    if len(history_steps) <= max_keep_recent:
        return {
            "compressed": False,
            "compacted_history": list(history_steps),
            "saved_tokens_est": 0,
        }

    old_steps = history_steps[:-max_keep_recent]
    recent_steps = history_steps[-max_keep_recent:]

    prompt = (
        "Compress the following execution steps into a concise summary "
        "(3-5 sentences preserving key decisions, outcomes, and findings):\n\n"
        f"{json.dumps(old_steps, ensure_ascii=False, default=str)}\n\n"
        "Summary:"
    )

    try:
        summary_str = llm_caller(prompt, temperature=0.1)
        summary_str = summary_str.strip()
    except Exception:
        summary_str = f"(Compressed {len(old_steps)} steps — LLM unavailable)"

    compacted = [
        {"role": "system", "content": f"[LONG_HORIZON_SUMMARY]: {summary_str}"}
    ] + recent_steps

    # 估算节省的 token 数（粗略：每步约 150 tokens）
    saved_estimate = len(old_steps) * 150

    return {
        "compressed": True,
        "compacted_history": compacted,
        "saved_tokens_est": saved_estimate,
    }
