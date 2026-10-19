"""oskill.knowledge_graph_query — 可查询知识图谱 (Graphify 机制 3O 内化)。

真实图遍历 (非向量检索): 节点/边 + 信任分级标记 + 遍历查询。
  * **EXTRACTED / INFERRED 边标注** — EXTRACTED 是源码/文档显式连接 (可审计),
    INFERRED 是图推理所得 (需下游核实);
  * **图遍历查询** — neighbors (邻居) / shortest_path (最短路径) /
    communities (社区检测) / trace (两点间路径), 查询而非检索;
  * **导出** — graph.json (Graphify graph-out 形态), 可与 code_graph_semantic
    组合 (Graft 节点 → 图边标注)。

零 veya 反向依赖: 纯图数据结构 + BFS/社区算法。
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any

EDGE_EXTRACTED = "EXTRACTED"
EDGE_INFERRED = "INFERRED"


@dataclass(frozen=True)
class GraphNode:
    """图节点 (一个概念/文件/子系统)。"""

    id: str
    label: str = ""
    kind: str = ""  # file / concept / subsystem / doc ...
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label or self.id, "kind": self.kind, "meta": self.meta}


@dataclass(frozen=True)
class GraphEdge:
    """图边 (带信任分级)。"""

    source: str
    target: str
    kind: str = "related"  # 关系类型 (depends_on/uses/part_of/...)
    trust: str = EDGE_EXTRACTED  # EXTRACTED / INFERRED
    evidence: str = ""  # EXTRACTED 的出处 / INFERRED 的依据

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "trust": self.trust,
            "evidence": self.evidence,
        }


class KnowledgeGraph:
    """可查询知识图谱: 节点/边 → 遍历查询。"""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adj: dict[str, set[str]] = {}

    # ── 构建 ──────────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        """添加节点 (幂等覆盖)。"""
        self.nodes[node.id] = node
        self._adj.setdefault(node.id, set())

    def add_edge(
        self,
        source: str,
        target: str,
        *,
        kind: str = "related",
        trust: str = EDGE_EXTRACTED,
        evidence: str = "",
    ) -> None:
        """添加边 (双向邻接)。"""
        if source not in self.nodes:
            raise KeyError(f"unknown source node: {source}")
        if target not in self.nodes:
            raise KeyError(f"unknown target node: {target}")
        if trust not in (EDGE_EXTRACTED, EDGE_INFERRED):
            raise ValueError(f"invalid trust: {trust!r}")
        self.edges.append(GraphEdge(source, target, kind=kind, trust=trust, evidence=evidence))
        self._adj.setdefault(source, set()).add(target)
        self._adj.setdefault(target, set()).add(source)

    def add_node_many(self, nodes: list[GraphNode]) -> None:
        """批量加节点。"""
        for node in nodes:
            self.add_node(node)

    # ── 遍历查询 ──────────────────────────────────────────────────────

    def neighbors(self, node_id: str, *, trust: str | None = None) -> list[GraphNode]:
        """某节点的邻居 (可选按信任过滤)。

        Args:
            node_id: 节点 id。
            trust: EXTRACTED / INFERRED 过滤。

        Returns:
            邻居节点列表。
        """
        if node_id not in self._adj:
            return []
        targets = self._adj.get(node_id, set())
        if trust is not None:
            trusted = {
                e.target if e.source == node_id else e.source
                for e in self.edges
                if e.trust == trust and (e.source == node_id or e.target == node_id)
            }
            targets = targets & trusted
        return [self.nodes[t] for t in sorted(targets) if t in self.nodes]

    def shortest_path(self, start: str, goal: str) -> list[str]:
        """两点间最短路径 (BFS)。

        Args:
            start / goal: 节点 id。

        Returns:
            路径节点 id 列表; 无路径返回 []。
        """
        if start not in self._adj or goal not in self._adj:
            return []
        if start == goal:
            return [start]
        prev: dict[str, str] = {}
        queue: deque[str] = deque([start])
        visited = {start}
        while queue:
            node = queue.popleft()
            for neighbor in sorted(self._adj.get(node, set())):
                if neighbor in visited:
                    continue
                prev[neighbor] = node
                visited.add(neighbor)
                if neighbor == goal:
                    path = [goal]
                    while path[-1] != start:
                        path.append(prev[path[-1]])
                    return list(reversed(path))
                queue.append(neighbor)
        return []

    def trace(self, start: str, goal: str) -> dict[str, Any]:
        """两点间路径 + 边证据 (查询而非检索)。"""
        path = self.shortest_path(start, goal)
        if not path:
            return {"found": False, "path": [], "edges": []}
        edges = []
        for a, b in zip(path, path[1:]):
            edge = next(
                (e for e in self.edges if {e.source, e.target} == {a, b}),
                None,
            )
            edges.append(
                {
                    "from": a,
                    "to": b,
                    "trust": edge.trust if edge else None,
                    "evidence": edge.evidence if edge else "",
                }
            )
        return {"found": True, "path": path, "edges": edges}

    # ── 社区检测 (简单 label propagation) ─────────────────────────────

    def communities(self, *, iterations: int = 5) -> dict[str, list[str]]:
        """简单社区检测 (label propagation)。

        Args:
            iterations: 传播轮数。

        Returns:
            {社区代表节点: [成员节点]}。
        """
        labels = {nid: nid for nid in self.nodes}
        for _ in range(iterations):
            for nid in self.nodes:
                neighbor_labels = [labels[n] for n in self._adj.get(nid, set())]
                if not neighbor_labels:
                    continue
                # 选出现最多的邻居标签
                counts: dict[str, int] = {}
                for lab in neighbor_labels:
                    counts[lab] = counts.get(lab, 0) + 1
                best = max(counts.items(), key=lambda x: x[1])[0]
                labels[nid] = best
        communities: dict[str, list[str]] = {}
        for nid, lab in labels.items():
            communities.setdefault(lab, []).append(nid)
        return {rep: sorted(members) for rep, members in communities.items()}

    # ── 导出 ──────────────────────────────────────────────────────────

    def export_json(self) -> dict[str, Any]:
        """Graphify graph-out 形态 (graph.json)。"""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "nodes": len(self.nodes),
                "edges": len(self.edges),
                "extracted": sum(1 for e in self.edges if e.trust == EDGE_EXTRACTED),
                "inferred": sum(1 for e in self.edges if e.trust == EDGE_INFERRED),
            },
        }

    def to_json(self, path: str) -> None:
        """写 graph.json。"""
        import pathlib

        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.export_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# ── 与 code_graph_semantic 组合 ──────────────────────────────────────


def semantic_to_graph(build: Any) -> KnowledgeGraph:
    """把 SemanticBuild (Graft 节点图) 转成 KnowledgeGraph (Graphify 图)。

    节点 → GraphNode (kind=concept); 链接 → 边 (kind=链接类型, trust=EXTRACTED,
    evidence="semantic link"); 同时给共享来源文件的节点加 INFERRED 边
    (同文件共现推理)。

    Args:
        build: oskill.code_graph_semantic.SemanticBuild。

    Returns:
        KnowledgeGraph。
    """
    graph = KnowledgeGraph()
    for name, node in build.nodes.items():
        graph.add_node(GraphNode(id=name, label=name, kind="concept"))
    for name, node in build.nodes.items():
        for link_type, targets in node.links.items():
            for target in targets:
                if target in build.nodes:
                    graph.add_edge(
                        name,
                        target,
                        kind=link_type,
                        trust=EDGE_EXTRACTED,
                        evidence="semantic link",
                    )
    # INFERRED: 共享来源文件的节点 (共现推理)
    file_to_nodes: dict[str, list[str]] = {}
    for name, node in build.nodes.items():
        for source in node.sources:
            file_to_nodes.setdefault(source.path, []).append(name)
    for path, names in file_to_nodes.items():
        for i, a in enumerate(names):
            for b in names[i + 1 :]:
                if not _has_edge(graph, a, b):
                    graph.add_edge(
                        a,
                        b,
                        kind="co_occurrence",
                        trust=EDGE_INFERRED,
                        evidence=f"share source: {path}",
                    )
    return graph


def _has_edge(graph: KnowledgeGraph, a: str, b: str) -> bool:
    return any({e.source, e.target} == {a, b} for e in graph.edges)
