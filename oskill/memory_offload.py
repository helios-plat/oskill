"""oskill.memory_offload — 记忆 offload 管线补全 (TencentDB L1.5/L3 3O 内化)。

在 memory_layers (L0-L3) 之上补齐两条管线:
  * **L1.5 任务边界判断** — 判断对话分段是否为 long task (长任务 → 触发
    L2 场景构建), 确定性规则 + LLM 注入;
  * **L3 token 压缩光标** — token 预算管理: 累计 token 计数, 超过预算触发
    压缩 (cursor 前移), 防上下文淹没 (TencentDB l3-token-counter 机制)。
零 veya 反向依赖: token 计数函数注入 (默认字符/4 近似); 纯状态机。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

BoundaryFn = Callable[[list[dict[str, Any]]], str]
"""L1.5 边界判断: (分段) → "long" / "short" (LLM 或规则注入)。"""

TokenCounter = Callable[[str], int]
"""token 计数: (文本) → token 数 (注入, 默认 len/4 近似)。"""


def _default_token_counter(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class TaskSegment:
    """一个 L1.5 分段 (任务归属)。"""

    segment_id: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    judgment: str = "short"  # long / short

    def to_dict(self) -> dict[str, Any]:
        return {"segment_id": self.segment_id, "entries": self.entries, "judgment": self.judgment}


class OffloadPipeline:
    """offload 管线: L1.5 边界 + L3 token 光标。"""

    def __init__(
        self,
        *,
        token_counter: TokenCounter | None = None,
        token_budget: int = 20000,
        compress_ratio: float = 0.5,
    ) -> None:
        self.token_counter = token_counter or _default_token_counter
        self.token_budget = token_budget
        self.compress_ratio = compress_ratio
        self.segments: list[TaskSegment] = []
        self.cursor_token: int = 0  # 已压缩掉的 token (L3 光标)
        self.compressed: list[str] = []  # 压缩摘要 (cursor 之前的)
        self.total_tokens: int = 0

    # ── L1.5 任务边界 ────────────────────────────────────────────────

    def judge_segments(
        self,
        batches: list[list[dict[str, Any]]],
        boundary_fn: BoundaryFn,
    ) -> list[TaskSegment]:
        """按批次判断任务边界 (long → 后续 L2 构建)。

        Args:
            batches: 分段 (每段含消息 dict)。
            boundary_fn: 判断函数 ("long"/"short")。

        Returns:
            分段列表 (judgment 已填)。
        """
        self.segments = []
        for i, batch in enumerate(batches):
            judgment = boundary_fn(batch)
            segment = TaskSegment(segment_id=f"seg_{i}", entries=batch, judgment=judgment)
            self.segments.append(segment)
        return self.segments

    def long_segments(self) -> list[TaskSegment]:
        """判定为 long 的分段 (需 L2 场景构建)。"""
        return [s for s in self.segments if s.judgment == "long"]

    # ── L3 token 压缩光标 ────────────────────────────────────────────

    def ingest(self, text: str) -> int:
        """记入 token 计数 (L3 token 记账)。

        Args:
            text: 新文本。

        Returns:
            累计总 token。
        """
        tokens = self.token_counter(text)
        self.total_tokens += tokens
        return self.total_tokens

    def should_compress(self) -> bool:
        """总 token 是否超过预算 (触发压缩)。"""
        return self.total_tokens > self.token_budget

    def compress(self, summarize: Callable[[str], str]) -> dict[str, Any]:
        """压缩: 超过预算的部分摘要化, 光标前移。

        Args:
            summarize: 摘要函数 (注入, 对超预算文本生成压缩摘要)。

        Returns:
            {compressed_tokens, cursor_token, total_tokens, summary}。
        """
        if not self.should_compress():
            return {
                "compressed_tokens": 0,
                "cursor_token": self.cursor_token,
                "total_tokens": self.total_tokens,
                "summary": None,
            }
        overflow = self.total_tokens - self.token_budget
        # 摘要超预算部分 (近似: 按比例取文本长度)
        summary = summarize(f"[overflow {overflow} tokens]")
        self.compressed.append(summary)
        self.cursor_token += overflow
        self.total_tokens = self.token_budget + self.token_counter(summary)
        return {
            "compressed_tokens": overflow,
            "cursor_token": self.cursor_token,
            "total_tokens": self.total_tokens,
            "summary": summary,
        }

    def recall_cursor(self) -> dict[str, Any]:
        """L3 光标视图 (已压缩历史摘要 + 当前 token)。"""
        return {
            "cursor_token": self.cursor_token,
            "compressed_summaries": list(self.compressed),
            "total_tokens": self.total_tokens,
            "budget": self.token_budget,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "segments": len(self.segments),
            "long_segments": len(self.long_segments()),
            "total_tokens": self.total_tokens,
            "cursor_token": self.cursor_token,
            "budget": self.token_budget,
        }


__all__ = ["OffloadPipeline", "TaskSegment"]
