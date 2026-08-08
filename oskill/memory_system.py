"""oskill.memory_system — 多类型记忆体系 (Auto-Deep-Research memory 3O 内化)。

AutoAgent 的四类记忆统一编排 (tool/rag/paper/codetree):
  * **MemoryKind** — tool (工具使用经验) / rag (检索增强) / paper (论文知识)
    / codetree (代码树);
  * **MemoryStore** — 分类型存储 + 分类检索 + 注入;
  * **ToolMemory** — 工具经验: 什么场景用什么工具 (复用规则);
  * 与 memory_hub/memory_offload 组合 (分层记忆之外的类型记忆)。
零 veya 反向依赖: 纯存储 + 关键词检索。
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

MEMORY_TOOL = "tool"
MEMORY_RAG = "rag"
MEMORY_PAPER = "paper"
MEMORY_CODETREE = "codetree"
MEMORY_KINDS = (MEMORY_TOOL, MEMORY_RAG, MEMORY_PAPER, MEMORY_CODETREE)


@dataclass
class MemoryEntry:
    """一条类型记忆。"""

    kind: str
    key: str
    content: str
    tags: list[str] = field(default_factory=list)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "content": self.content[:200],
            "tags": self.tags,
        }


class MemoryStore:
    """分类型记忆存储 + 检索。"""

    def __init__(self) -> None:
        self.entries: dict[str, MemoryEntry] = {}

    def remember(
        self, kind: str, key: str, content: str, *, tags: list[str] | None = None
    ) -> MemoryEntry:
        """存入一条记忆 (同 kind+key 覆盖)。"""
        if kind not in MEMORY_KINDS:
            raise ValueError(f"unknown memory kind: {kind!r}; expected {MEMORY_KINDS}")
        entry = MemoryEntry(kind=kind, key=key, content=content, tags=tags or [])
        self.entries[f"{kind}:{key}"] = entry
        return entry

    def recall(self, kind: str | None = None) -> list[MemoryEntry]:
        """取记忆 (按类型过滤)。"""
        if kind is None:
            return list(self.entries.values())
        return [e for e in self.entries.values() if e.kind == kind]

    def search(self, query: str, *, kind: str | None = None, top_k: int = 3) -> list[MemoryEntry]:
        """关键词检索 (tag/key/content 匹配)。"""
        query_lower = query.lower()
        scored = []
        for entry in self.recall(kind):
            score = 0
            if query_lower in entry.content.lower():
                score += 2
            if query_lower in entry.key.lower():
                score += 1
            score += sum(1 for t in entry.tags if query_lower in t.lower())
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:top_k]]

    def summary(self) -> dict[str, int]:
        return {kind: len(self.recall(kind)) for kind in MEMORY_KINDS}


class ToolMemory:
    """工具使用经验: 场景 → 工具映射 (AutoAgent tool_memory)。"""

    def __init__(self) -> None:
        self.scenarios: dict[str, str] = {}

    def learn(self, scenario: str, tool: str) -> None:
        """记录: 某场景适用某工具。"""
        self.scenarios[scenario.lower()] = tool

    def recommend(self, task: str) -> str | None:
        """按任务推荐工具 (token 全匹配: 场景所有词都出现在任务中)。"""
        task_lower = task.lower()
        for scenario, tool in self.scenarios.items():
            tokens = [t for t in re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", scenario.lower()) if t]
            if tokens and all(t in task_lower for t in tokens):
                return tool
        return None

    def suggestions(self) -> list[tuple[str, str]]:
        return sorted(self.scenarios.items())


__all__ = [
    "MEMORY_CODETREE",
    "MEMORY_KINDS",
    "MEMORY_PAPER",
    "MEMORY_RAG",
    "MEMORY_TOOL",
    "MemoryEntry",
    "MemoryStore",
    "ToolMemory",
]
