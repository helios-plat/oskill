"""oskill.code_graph_semantic — 语义节点图 (NanoNets/Graft 机制 3O 内化)。

把代码库变成"带语义的 markdown 节点图", 与 oprim 符号图 (CRG: 在哪) 互补:

  * **两遍构建** — Pass 1 逐文件摘要 → Pass 2 分组为节点 (子系统/关键文件/
    概念) + 类型化链接 (LLM 注入, 机制确定性);
  * **节点 = Summary + Crux + Sources(带哈希) + Links + Notes** — 答案内联,
    Crux 存原文而非行号 (行号会漂移, 关键行不会);
  * **指纹刷新** — 内容哈希指纹, 查询前 3ms 级比对, 只重建变更文件
    (incremental_refresh, $0 无 LLM);
  * **类型化 wikilinks** — depends_on / part_of / uses / implements / produces,
    markdown [[wikilinks]] 可跟随。

零 veya 反向依赖: 摘要/分组函数由调用方注入; 哈希纯 Python。
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── 类型化链接 ───────────────────────────────────────────────────────

LINK_DEPENDS_ON = "depends_on"
LINK_PART_OF = "part_of"
LINK_USES = "uses"
LINK_IMPLEMENTS = "implements"
LINK_PRODUCES = "produces"
LINK_TYPES = (LINK_DEPENDS_ON, LINK_PART_OF, LINK_USES, LINK_IMPLEMENTS, LINK_PRODUCES)


# ── 数据结构 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SourceRef:
    """节点来源文件 (带内容哈希, 用于过期判断)。"""

    path: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "hash": self.hash}


@dataclass
class SemanticNode:
    """一个语义节点 (对应 Graft 的 markdown 节点文件)。

    Attributes:
        name: 节点名。
        summary: 模型写的代码干什么的。
        crux: 关键逻辑行 (原文, 非行号)。
        sources: 来源文件 + 内容哈希。
        links: 类型 → 目标节点名列表。
        notes: 用户附加内容 (跨重建保留)。
    """

    name: str
    summary: str = ""
    crux: str = ""
    sources: list[SourceRef] = field(default_factory=list)
    links: dict[str, list[str]] = field(default_factory=dict)
    notes: str = ""

    def add_link(self, link_type: str, target: str) -> None:
        """加一条类型化链接 (去重)。"""
        if link_type not in LINK_TYPES:
            raise ValueError(f"invalid link type: {link_type!r}; expected {LINK_TYPES}")
        self.links.setdefault(link_type, [])
        if target not in self.links[link_type]:
            self.links[link_type].append(target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "crux": self.crux,
            "sources": [s.to_dict() for s in self.sources],
            "links": dict(self.links),
            "notes": self.notes,
        }


@dataclass
class SemanticBuild:
    """一次语义图构建结果。"""

    nodes: dict[str, SemanticNode] = field(default_factory=dict)
    fingerprint: dict[str, str] = field(default_factory=dict)  # path → 内容哈希
    built_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "fingerprint": dict(self.fingerprint),
        }


# ── 哈希与指纹 ───────────────────────────────────────────────────────


def content_hash(text: str) -> str:
    """内容 sha1 前缀 (12 位)。"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def build_fingerprint(files: list[str | Path]) -> dict[str, str]:
    """对一组文件生成指纹 (path → 内容哈希)。

    Args:
        files: 文件路径列表 (读失败跳过)。

    Returns:
        指纹 dict (相对路径 → 哈希)。
    """
    fingerprint: dict[str, str] = {}
    for file in files:
        path = Path(file)
        try:
            fingerprint[str(path)] = content_hash(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return fingerprint


def stale_nodes(build: SemanticBuild, files: list[str | Path]) -> list[str]:
    """按当前指纹找出过期节点 (来源文件哈希变化)。

    Args:
        build: 已有构建。
        files: 当前文件列表。

    Returns:
        过期节点名列表。
    """
    current = build_fingerprint(files)
    stale: list[str] = []
    for name, node in build.nodes.items():
        for source in node.sources:
            if source.hash != current.get(source.path):
                stale.append(name)
                break
    return stale


def incremental_refresh(
    build: SemanticBuild,
    files: list[str | Path],
    summarizer: Callable[[str, str], str],
) -> SemanticBuild:
    """指纹刷新: 只重建内容变化的文件 (3ms 级比对, $0 无 LLM 判断变更)。

    Args:
        build: 已有构建。
        files: 当前文件列表。
        summarizer: (path, content) → 摘要 (只在文件变更时调用)。

    Returns:
        新构建 (未变文件复用旧摘要)。
    """
    current = build_fingerprint(files)
    new_build = SemanticBuild(fingerprint=current, built_at=build.built_at)
    # 已存在节点: 其 sources 全部未变则复用
    for name, node in build.nodes.items():
        if all(source.hash == current.get(source.path) for source in node.sources):
            new_build.nodes[name] = node
    # 有变更文件的节点 → 重新摘要
    changed = {path for path, h in current.items() if build.fingerprint.get(path) != h}
    for path in sorted(changed):
        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        summary = summarizer(path, content)
        new_build.nodes.setdefault(
            f"node:{path}", SemanticNode(name=f"node:{path}", summary=summary)
        )
    return new_build


# ── 两遍构建 (LLM 注入) ──────────────────────────────────────────────

FileSummarizer = Callable[[str, str], str]
"""文件摘要: (path, content) → 一句话摘要。"""

NodeClusterer = Callable[[dict[str, str]], dict[str, SemanticNode]]
"""节点分组: {文件: 摘要} → 节点 dict (含 links)。"""


def semantic_build(
    files: list[str | Path],
    *,
    summarize: FileSummarizer,
    cluster: NodeClusterer,
) -> SemanticBuild:
    """两遍构建语义节点图。

    Args:
        files: 源文件列表。
        summarize: Pass 1 逐文件摘要。
        cluster: Pass 2 分组为节点 + 类型化链接。

    Returns:
        SemanticBuild (nodes + fingerprint)。
    """
    fingerprint = build_fingerprint(files)
    summaries: dict[str, str] = {}
    for file in files:
        path = Path(file)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        summaries[str(path)] = summarize(str(path), content)
    nodes = cluster(summaries)
    build = SemanticBuild(nodes=nodes, fingerprint=fingerprint)
    return build


# ── Markdown 渲染 ([[wikilinks]]) ────────────────────────────────────


def render_node_markdown(node: SemanticNode) -> str:
    """把节点渲染为 markdown (Graft 节点文件格式)。

    Args:
        node: 语义节点。

    Returns:
        markdown 文本 (Summary/Crux/Sources/Links/Notes 区块,
        Links 用 [[wikilinks]] 可跟随)。

    Example:
        >>> "<node>" in render_node_markdown(SemanticNode("a", summary="s"))
        True
    """
    parts = [f"<!-- node: {node.name} -->", "", f"# {node.name}", ""]
    if node.summary:
        parts += ["## Summary", "", node.summary, ""]
    if node.crux:
        parts += ["## Crux", "", "```", node.crux, "```", ""]
    if node.sources:
        parts += ["## Sources", ""]
        parts += [f"- `{s.path}` ({s.hash})" for s in node.sources]
        parts.append("")
    if node.links:
        parts += ["## Links", ""]
        for link_type in LINK_TYPES:
            targets = node.links.get(link_type, [])
            for target in targets:
                parts.append(f"- {link_type}: [[{target}]]")
        parts.append("")
    if node.notes:
        parts += ["## Notes", "", node.notes, ""]
    return "\n".join(parts)


def parse_wikilinks(markdown_text: str) -> list[str]:
    """从 markdown 提取 [[wikilinks]] 目标 (供跟随)。"""
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", markdown_text)
