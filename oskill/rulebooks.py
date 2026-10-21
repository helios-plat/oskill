"""oskill.rulebooks — 经典软件工程书规则库 (agent-rules-books 3O 内化)。

数据资产: 14 本经典书的 full 规则集 (MIT), 每本仅保留**最完整版**
(oskill/_rulebooks/<book>/full.md)。机制:
  * 检索: 按任务关键词选书 (select_rulebooks), 解决"LLM 不知道该选谁";
  * 读取: get_rulebook 返回全文, rules_sections 按 ## 通用分段;
  * 注入: standards_rules 拼装审查/重构用的规则文本基线。

零 veya 反向依赖: 纯文件读取 + 词频检索, 无外部命令。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_RULEBOOKS_DIR = Path(__file__).parent / "_rulebooks"

# 书名 → 领域关键词 (用于 select_rulebooks 打分; 源自各书简介)
RULEBOOK_KEYWORDS: dict[str, list[str]] = {
    "a-philosophy-of-software-design": [
        "module",
        "api",
        "interface",
        "complexity",
        "cognitive",
        "deep module",
        "模块",
        "接口",
        "复杂度",
        "抽象",
        "设计",
    ],
    "clean-architecture": [
        "architecture",
        "boundary",
        "dependency rule",
        "layer",
        "framework",
        "架构",
        "边界",
        "依赖规则",
        "分层",
    ],
    "clean-code": [
        "naming",
        "readability",
        "function",
        "test",
        "comment",
        "simple",
        "命名",
        "可读性",
        "函数",
        "注释",
    ],
    "code-complete": [
        "construction",
        "variable",
        "control flow",
        "defensive",
        "standard",
        "构造",
        "变量",
        "控制流",
        "防御式",
        "编码标准",
    ],
    "designing-data-intensive-applications": [
        "data",
        "consistency",
        "replication",
        "partition",
        "transaction",
        "stream",
        "reliability",
        "scalability",
        "数据",
        "一致性",
        "复制",
        "分区",
        "事务",
        "流",
    ],
    "domain-driven-design": [
        "domain",
        "bounded context",
        "ubiquitous",
        "aggregate",
        "event",
        "modeling",
        "领域",
        "限界上下文",
        "统一语言",
        "聚合",
        "建模",
    ],
    "domain-driven-design-distilled": [
        "ddd",
        "subdomain",
        "context mapping",
        "domain",
        "精简",
        "子域",
        "上下文映射",
        "领域",
    ],
    "implementing-domain-driven-design": [
        "aggregate",
        "domain event",
        "application",
        "ddd",
        "落地",
        "聚合",
        "领域事件",
        "应用架构",
    ],
    "patterns-of-enterprise-application-architecture": [
        "enterprise",
        "layer",
        "repository",
        "unit of work",
        "service",
        "mapper",
        "企业",
        "服务层",
        "仓储",
        "工作单元",
    ],
    "refactoring": [
        "refactor",
        "smell",
        "behavior",
        "safe change",
        "重构",
        "坏味道",
        "行为",
    ],
    "refactoring-guru": [
        "refactor",
        "smell",
        "technique",
        "重构",
        "坏味道",
        "重构技术",
    ],
    "release-it": [
        "reliability",
        "timeout",
        "retry",
        "circuit",
        "bulkhead",
        "backpressure",
        "production",
        "observability",
        "可靠性",
        "超时",
        "重试",
        "熔断",
        "生产",
        "监控",
    ],
    "the-pragmatic-programmer": [
        "pragmatic",
        "dry",
        "orthogonal",
        "automation",
        "feedback",
        "prototype",
        "务实",
        "正交",
        "自动化",
        "快速反馈",
        "原型",
    ],
    "working-effectively-with-legacy-code": [
        "legacy",
        "characterization test",
        "seam",
        "dependency",
        "safe change",
        "遗留代码",
        "特征测试",
        "接缝",
        "依赖",
        "安全修改",
    ],
}

_TIER = "full"


def list_rulebooks() -> list[str]:
    """列出全部规则书 id (按目录序)。"""
    return sorted(RULEBOOK_KEYWORDS)


def get_rulebook(book: str, *, tier: str = _TIER) -> str:
    """读取某本书的规则全文 (仅打包 full 档, 最完整版)。

    Args:
        book: 书 id (list_rulebooks 返回值)。
        tier: 档位; 本模块仅打包 full, 传其他值抛 ValueError。

    Returns:
        规则全文 markdown。

    Raises:
        ValueError: 未知书 id 或档位。
    """
    if book not in RULEBOOK_KEYWORDS:
        raise ValueError(f"unknown rulebook: {book!r}; available: {list_rulebooks()}")
    if tier != _TIER:
        raise ValueError(f"only tier 'full' is packaged (got {tier!r})")
    path = _RULEBOOKS_DIR / book / f"{tier}.md"
    if not path.exists():
        raise ValueError(f"rulebook file missing: {path}")
    return path.read_text(encoding="utf-8")


def rules_sections(text: str) -> dict[str, str]:
    """按二级标题 (##) 通用分段解析规则文本。

    Args:
        text: get_rulebook 返回的全文。

    Returns:
        {段标题: 段内容} (不含标题行; 一级标题之前的前言归 "preamble")。
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is None:
            sections.setdefault("preamble", "")
            sections["preamble"] += line + "\n"
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return {k: v for k, v in sections.items() if v}


def select_rulebooks(
    task: str,
    *,
    top_k: int = 2,
    keywords: dict[str, list[str]] | None = None,
) -> list[str]:
    """按任务描述选择最相关的规则书 (词频打分)。

    Args:
        task: 任务描述 (如 "重构这个遗留模块并加特征测试")。
        top_k: 返回书数量。
        keywords: 覆盖内置关键词表。

    Returns:
        书 id 列表 (得分降序, top_k)。

    Example:
        >>> "refactoring" in select_rulebooks("refactor legacy module safely")
        True
    """
    table = keywords or RULEBOOK_KEYWORDS
    task_words = set(re.findall(r"[\w-]+", task.lower()))
    scored: list[tuple[int, str]] = []
    for book, words in table.items():
        score = sum(1 for w in words if w.lower() in task_words or w.lower() in task.lower())
        # 书名加权: 任务词命中书名主体 (含前缀匹配, 如 refactor→refactoring)
        book_tokens = [t for t in book.split("-") if len(t) >= 4]
        if any(tw in book_tokens for tw in task_words):
            score += 2
        elif any(
            t.startswith(tw) or tw.startswith(t)
            for t in book_tokens for tw in task_words
        ):
            score += 2
        if score > 0:
            scored.append((score, book))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [book for _, book in scored[:top_k]]


def standards_rules(
    *,
    books: list[str] | None = None,
    task: str | None = None,
    top_k: int = 2,
) -> dict[str, Any]:
    """拼装审查/重构用的规则基线: 选书 → 读全文 → 按分段注入。

    Args:
        books: 显式指定书列表; None 时按 task 自动选择。
        task: 任务描述 (books 为 None 时用于选书)。
        top_k: 自动选书数量。

    Returns:
        {books, sections: {书id: {段标题: 内容}}} —— LLM 可整体注入,
        或按需取某书的 Decision/Trigger 段。

    Example:
        >>> r = standards_rules(task="review refactoring of a legacy module")
        >>> r["books"] and r["sections"]
        True
    """
    selected = books or select_rulebooks(task or "", top_k=top_k)
    sections = {book: rules_sections(get_rulebook(book)) for book in selected}
    return {"books": selected, "sections": sections}
