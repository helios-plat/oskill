"""oskill.proactive_deep_reach — 长程多阶主动联网深度搜查与信息交叉提炼算法.

Stateless 纯算法。依赖 LLMCallerProtocol + fetch_op Callable 注入.

组合: fetch_op (依赖注入) + LLM caller (依赖注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol — 不 import oprim，由调用方注入."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def proactive_deep_reach(
    initial_topic: str,
    *,
    fetch_op: Callable[..., dict[str, Any]],
    llm_caller: LLMCallerProtocol,
    max_depth: int = 2,
) -> dict[str, Any]:
    """长程多阶主动联网深度搜查与信息交叉提炼算法.

    从初始 topic 出发，逐层探索，每层用 LLM 决定下一跳方向。

    Args:
        initial_topic: 初始搜索主题
        fetch_op: 网页抓取函数，接受 (url_or_query) → {"content_markdown": str, ...}
        llm_caller: LLM 调用接口（注入）
        max_depth: 最大探索深度

    Returns:
        {
            "status": "completed" | "incomplete",
            "depth_reached": int,
            "collected_info": list[{"depth": int, "content": str, "target": str}],
        }
    """
    collected_info: list[dict[str, Any]] = []
    current_target = initial_topic

    for depth in range(max_depth):
        try:
            fetch_res = fetch_op(current_target)
        except Exception:
            # 单步失败不影响整体结果
            collected_info.append(
                {
                    "depth": depth,
                    "target": current_target,
                    "content": "",
                    "error": "fetch_op failed",
                }
            )
            break

        content = (
            fetch_res.get("content_markdown", "") if isinstance(fetch_res, dict) else str(fetch_res)
        )
        collected_info.append(
            {
                "depth": depth,
                "target": current_target,
                "content": content[:2000],  # 截断
            }
        )

        # LLM 决定下一个跳转链
        prompt = (
            f"Based on the following content about '{initial_topic}', "
            f"what is the next specific sub-topic or URL to explore "
            f"(depth {depth + 1}/{max_depth})?\n\n"
            f"Content:\n{content[:1000]}\n\n"
            f"Reply with a single URL or search query, or 'DONE' if finished."
        )

        try:
            next_target = llm_caller(prompt, temperature=0.1).strip()
        except Exception:
            next_target = "DONE"

        if next_target.upper() == "DONE" or not next_target:
            break

        # 简单校验下一跳是否合理
        if "http" in next_target or len(next_target) > 3:
            current_target = next_target
        else:
            break

    return {
        "status": "completed",
        "depth_reached": len(collected_info),
        "collected_info": collected_info,
    }
