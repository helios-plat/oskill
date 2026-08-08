"""oskill.code_graph_builder — 语义图构建管线 (Graft/Graphify 两遍管线 3O 内化)。

在 code_graph_semantic + code_parse 之上编排完整构建管线:
  * **build_graph** — 两遍: 文件摘要 (LLM 注入) → 分组节点 → 知识图谱导出
    (EXTRACTED/INFERRED 边);
  * **incremental_build** — 指纹复用: 未变文件跳过摘要, 只处理变更;
  * 组合: code_parse 符号 → code_graph_semantic 节点 → knowledge_graph 边。
零 veya 反向依赖: 摘要/分组函数注入; 纯编排。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FileSummarizer = Callable[[str, str], str]
"""文件摘要: (path, content) → 摘要。"""

NodeClusterer = Callable[[dict[str, str]], dict[str, Any]]
"""节点分组: {文件: 摘要} → {节点名: SemanticNode}。"""


@dataclass
class BuildStats:
    """构建统计。"""

    files_scanned: int = 0
    files_summarized: int = 0
    files_cached: int = 0
    nodes: int = 0
    edges: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_scanned": self.files_scanned,
            "files_summarized": self.files_summarized,
            "files_cached": self.files_cached,
            "nodes": self.nodes,
            "edges": self.edges,
        }


class CodeGraphBuilder:
    """语义图构建器 (两遍管线 + 增量)。"""

    def __init__(self) -> None:
        self.stats = BuildStats()
        self.build = None
        self._fingerprint: dict[str, str] = {}

    def build_graph(
        self,
        files: list[str | Path],
        *,
        summarize: FileSummarizer,
        cluster: NodeClusterer,
    ) -> Any:
        """全量两遍构建: 摘要 → 分组 → 语义图。

        Args:
            files: 源文件。
            summarize: 文件摘要函数。
            cluster: 节点分组函数 (返回 SemanticNode dict)。

        Returns:
            SemanticBuild。
        """
        from oskill.code_graph_semantic import semantic_build

        self.stats = BuildStats(files_scanned=len(files))
        build = semantic_build(
            files,
            summarize=summarize,
            cluster=cluster,
        )
        self.build = build
        self._fingerprint = dict(build.fingerprint)
        self.stats.files_summarized = len(files)
        self.stats.nodes = len(build.nodes)
        return build

    def incremental_build(
        self,
        files: list[str | Path],
        *,
        summarize: FileSummarizer,
        cluster: NodeClusterer,
    ) -> Any:
        """增量构建: 指纹复用未变文件摘要, 只处理变更。

        Args:
            files: 当前文件。
            summarize: 摘要函数 (仅变更文件调用)。
            cluster: 分组函数。

        Returns:
            SemanticBuild (stats 含 cached/summarized 分布)。
        """
        from oskill.code_graph_semantic import (
            build_fingerprint,
        )

        self.stats = BuildStats(files_scanned=len(files))
        current = build_fingerprint(files)
        if self.build is None or not self._fingerprint:
            return self.build_graph(files, summarize=summarize, cluster=cluster)

        changed = {path for path, h in current.items() if self._fingerprint.get(path) != h}
        # 复用旧节点 (来源未变的), 重建变更
        from oskill.code_graph_semantic import incremental_refresh

        refreshed = incremental_refresh(self.build, files, summarize)
        # 变更文件重新分组 (整体 re-cluster 保证一致性)
        summaries: dict[str, str] = {}
        for path in sorted(changed):
            try:
                content = Path(path).read_text(encoding="utf-8")
                summaries[path] = summarize(path, content)
            except OSError:
                continue
        if summaries:
            new_nodes = cluster(summaries)
            refreshed.nodes.update(new_nodes)
        refreshed.fingerprint = current
        self.build = refreshed
        self._fingerprint = dict(current)
        self.stats.files_summarized = len(changed)
        self.stats.files_cached = len(files) - len(changed)
        self.stats.nodes = len(refreshed.nodes)
        return refreshed

    def export_knowledge_graph(self) -> Any:
        """语义图 → 知识图谱 (EXTRACTED/INFERRED 边, Graphify 组合)。"""
        from oskill.knowledge_graph_query import semantic_to_graph

        if self.build is None:
            raise RuntimeError("no build yet; run build_graph first")
        return semantic_to_graph(self.build)


__all__ = ["BuildStats", "CodeGraphBuilder"]
