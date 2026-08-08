"""oskill.context_engineering — 上下文工程 (hello-agents 第9章 3O 内化)。

持续交互的上下文管理 (veya context.py 的机制层):
  * **ContextMessage** — 消息 (role/content/priority/timestamp/summary);
  * **ContextBudget** — 预算 (token/字符上限, 超限策略);
  * **trim** — 裁剪: 按优先级保留 + 摘要化低优先级 + 截断;
  * **summarize_old** — 旧消息摘要压缩 (LLM 注入或规则);
  * 与 memory_layers/memory_hub 组合 (上下文窗口管理)。
零 veya 反向依赖: 摘要函数注入; token 计数注入 (默认 len/4)。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


@dataclass
class ContextMessage:
    """一条上下文消息 (带优先级/时间)。"""

    role: str
    content: str
    priority: int = 1  # 高优先级 = 保留 (0 最优先)
    ts: float = 0.0
    summary: str | None = None  # 摘要化后内容

    def effective_content(self) -> str:
        return self.summary if self.summary is not None else self.content


TokenCounter = Callable[[str], int]
"""token 计数: (text) → token 数。"""


def _default_token_counter(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class ContextBudget:
    """上下文预算。"""

    max_tokens: int = 8000
    keep_roles: tuple[str, ...] = (ROLE_SYSTEM,)
    summarize_below_priority: int = 2  # 低于该优先级 → 可摘要

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_tokens": self.max_tokens,
            "keep_roles": self.keep_roles,
            "summarize_below_priority": self.summarize_below_priority,
        }


@dataclass
class TrimResult:
    """裁剪结果。"""

    messages: list[ContextMessage]
    total_tokens: int
    summarized: int = 0
    dropped: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "summarized": self.summarized,
            "dropped": self.dropped,
            "count": len(self.messages),
        }


class ContextEngine:
    """上下文工程: 管理消息窗口 (优先级/摘要/裁剪)。"""

    def __init__(self, *, token_counter: TokenCounter | None = None) -> None:
        self.token_counter = token_counter or _default_token_counter

    def trim(
        self,
        messages: list[ContextMessage],
        budget: ContextBudget,
        *,
        summarize_fn: Callable[[str], str] | None = None,
    ) -> TrimResult:
        """裁剪消息窗口到预算内。

        策略 (确定性):
        1. 必须保留 role ∈ keep_roles (如 system);
        2. 低优先级 (priority >= summarize_below_priority) 且非必须 → 摘要化;
        3. 仍超限 → 从低优先级丢弃 (保留最新);
        4. 高优先级可截断内容到预算。

        Args:
            messages: 消息 (按时间序)。
            budget: 预算。
            summarize_fn: 摘要函数 (None 时低优先级直接丢弃)。

        Returns:
            TrimResult。
        """
        summarized = 0
        dropped = 0

        def token_count(m: ContextMessage) -> int:
            return self.token_counter(m.effective_content())

        # 1. 必须保留的 (system 等)
        must_keep = [m for m in messages if m.role in budget.keep_roles]
        others = [m for m in messages if m.role not in budget.keep_roles]
        must_tokens = sum(token_count(m) for m in must_keep)
        others.sort(key=lambda m: (m.priority, -m.ts))  # 低优先级在前, 旧在前

        # 2. 摘要化低优先级 (从最旧开始)
        if summarize_fn is not None:
            candidates = [
                m
                for m in others
                if m.priority >= budget.summarize_below_priority and m.summary is None
            ]
            for m in candidates:
                m.summary = summarize_fn(m.content)[:400]
                summarized += 1

        # 3-4. 逐步丢弃/截断
        kept: list[ContextMessage] = list(must_keep)
        total = must_tokens
        for m in sorted(others, key=lambda m: (m.priority, m.ts)):
            if m.summary is not None:
                kept.append(m)
                total += token_count(m)
            else:
                kept.append(m)
                total += token_count(m)
        # 超限: 从非必须中丢弃最旧的
        non_keep_indices = [i for i, m in enumerate(kept) if m.role not in budget.keep_roles]
        while total > budget.max_tokens and non_keep_indices:
            idx = non_keep_indices.pop(0)  # 最旧非必须
            removed = kept.pop(idx)
            total -= token_count(removed)
            dropped += 1
            non_keep_indices = [i for i, m in enumerate(kept) if m.role not in budget.keep_roles]
        # 仍超限: 截断最后一条
        if total > budget.max_tokens and kept:
            last = kept[-1]
            overflow = total - budget.max_tokens
            trimmed_content = last.effective_content()[: -overflow * 4]
            last.summary = trimmed_content + "…"
            total = must_tokens + sum(self.token_counter(m.effective_content()) for m in kept)
        return TrimResult(messages=kept, total_tokens=total, summarized=summarized, dropped=dropped)


def messages_from_dicts(data: list[dict[str, Any]]) -> list[ContextMessage]:
    """从 dict 列表构造消息。"""
    return [
        ContextMessage(
            role=m.get("role", ROLE_USER),
            content=m.get("content", ""),
            priority=m.get("priority", 1),
            ts=m.get("ts", 0.0),
        )
        for m in data
    ]


__all__ = [
    "ContextBudget",
    "ContextEngine",
    "ContextMessage",
    "ROLE_ASSISTANT",
    "ROLE_SYSTEM",
    "ROLE_TOOL",
    "ROLE_USER",
    "TrimResult",
    "messages_from_dicts",
]
