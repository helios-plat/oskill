"""oskill.context_compression — 上下文长文本智能截断与摘要压缩算法.

组合 oprim.file_read_slice（按 token/行截断）+ oprim.llm_chat_call（摘要），
stateless：LLM 依赖经 caller Protocol 注入，不落库、不写文件。

流程：
1. 文本超预算 → file_read_slice 语义截断（保留头尾）
2. 中间段交给 LLM 生成结构化摘要
3. 拼回 {head + summary + tail} 并统计压缩比

Example:
    >>> r = await context_compression(long_text, caller=my_caller, budget_tokens=2000)
    >>> r["compressed"]
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class ContextCaller(Protocol):
    """LLM 调用协议（与 oskill._llm_caller.LLMCaller 对齐）。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


_CHARS_PER_TOKEN = 4.0
_HEAD_RATIO = 0.2
_TAIL_RATIO = 0.1


async def context_compression(
    text: str,
    *,
    caller: ContextCaller,
    budget_tokens: int = 4000,
    max_tokens: int = 512,
) -> dict[str, Any]:
    """长文本压缩：截断 + LLM 摘要 + 重组。

    Args:
        text: 待压缩文本。
        caller: LLM 调用器（注入）。
        budget_tokens: 输出 token 预算（含摘要后的全文估算）。
        max_tokens: 摘要生成的最大输出 token。

    Returns:
        {
            "compressed": bool,
            "text": str,
            "summary": str,
            "original_chars": int,
            "final_chars": int,
            "ratio": float,          # final/original
            "truncated_head": str,   # 保留头
            "truncated_tail": str,   # 保留尾
        }

    Raises:
        LLMOskillError: LLM 摘要失败。
        OskillError: text 为空。
    """
    if not text or not text.strip():
        raise OskillError("context_compression: text must not be empty")
    if budget_tokens <= 0:
        raise OskillError("context_compression: budget_tokens must be > 0")

    budget_chars = int(budget_tokens * _CHARS_PER_TOKEN)
    original_chars = len(text)
    if original_chars <= budget_chars:
        return {
            "compressed": False,
            "text": text,
            "summary": "",
            "original_chars": original_chars,
            "final_chars": original_chars,
            "ratio": 1.0,
            "truncated_head": "",
            "truncated_tail": "",
        }

    # 保留头尾，中间段摘录（模拟 file_read_slice 的截断语义）
    head_chars = int(original_chars * _HEAD_RATIO)
    tail_chars = int(original_chars * _TAIL_RATIO)
    head, middle, tail = (
        text[:head_chars],
        text[head_chars : -tail_chars or None],
        text[-tail_chars:],
    )

    summary = await _summarize(middle, caller=caller, max_tokens=max_tokens)

    final_text = f"{head}\n\n[摘要] {summary}\n\n{tail}"
    final_chars = len(final_text)
    return {
        "compressed": True,
        "text": final_text,
        "summary": summary,
        "original_chars": original_chars,
        "final_chars": final_chars,
        "ratio": round(final_chars / original_chars, 4),
        "truncated_head": head,
        "truncated_tail": tail,
    }


async def _summarize(middle: str, *, caller: ContextCaller, max_tokens: int) -> str:
    prompt = (
        "压缩以下文本为 3-5 句结构化摘要，保留关键决策、事实与结论，"
        "不要添加原文没有的信息：\n\n" + middle[:8000]
    )
    try:
        response = await caller(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        raise LLMOskillError("context_compression: LLM call failed", cause=exc) from exc
    content = response.get("content", "")
    if isinstance(content, str):
        return content.strip()
    return (
        "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
        or "(摘要为空)"
    )
