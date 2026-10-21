"""DAG layout for workflow canvases.

The original graph-shaped API is retained. A node list selects the newer
positions/levels API used by the Veya layout element.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from oskill._exceptions import OskillError

LayoutKind = Literal["layered", "radial"]


def dag_visual_layout(
    nodes: list[str] | dict[str, Any] | None = None,
    status_map: dict[str, str] | None = None,
    context: dict[str, Any] | None = None,
    *,
    edges: list[dict[str, str]] | None = None,
    layout: LayoutKind = "layered",
    width: float = 100.0,
    height: float = 100.0,
    graph: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute positions for a DAG."""
    if graph is not None or isinstance(nodes, dict):
        return _legacy_layout(graph if graph is not None else nodes, status_map, context)
    return _layered_layout(
        list(nodes or []),
        edges=edges,
        layout=layout,
        width=width,
        height=height,
    )


def _legacy_layout(
    graph: dict[str, Any] | None,
    status_map: dict[str, str] | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    graph = graph or {}
    ctx = context or {}
    graph_nodes = list(graph.get("nodes", []))
    graph_edges = list(graph.get("edges", []))
    statuses = dict(status_map or {})

    canvas_w = int(ctx.get("canvas_width", 1200))
    canvas_h = int(ctx.get("canvas_height", 800))
    layer_gap = int(ctx.get("layer_gap", 120))
    node_gap = int(ctx.get("node_gap", 80))

    in_degree: dict[str, int] = {node.get("id", "?"): 0 for node in graph_nodes}
    adj: dict[str, list[str]] = {node.get("id", "?"): [] for node in graph_nodes}
    for edge in graph_edges:
        src, dst = edge.get("from", ""), edge.get("to", "")
        if src in adj and dst not in adj.get(src, []):
            adj[src].append(dst)
        if dst in in_degree:
            in_degree[dst] = in_degree.get(dst, 0) + 1

    layers: list[list[str]] = []
    assigned: set[str] = set()
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    while queue:
        layers.append(list(queue))
        assigned.update(queue)
        next_queue = []
        for node_id in queue:
            for dst in adj.get(node_id, []):
                in_degree[dst] = in_degree.get(dst, 1) - 1
                if in_degree[dst] <= 0 and dst not in assigned and dst not in next_queue:
                    next_queue.append(dst)
        queue = next_queue

    remaining = [node_id for node_id in in_degree if node_id not in assigned]
    if remaining:
        layers.append(remaining)

    positioned: list[dict[str, Any]] = []
    for layer_index, layer in enumerate(layers):
        layer_width = max(1, len(layer)) * node_gap
        x_start = max(50, (canvas_w - layer_width) // 2)
        y = 50 + layer_index * layer_gap
        for node_index, node_id in enumerate(layer):
            positioned.append(
                {
                    "id": node_id,
                    "label": _node_label(graph_nodes, node_id),
                    "x": x_start + node_index * node_gap,
                    "y": y,
                    "status": statuses.get(node_id, "pending"),
                    "layer": layer_index,
                }
            )

    return {
        "status": "computed",
        "nodes": positioned,
        "edges": graph_edges,
        "layer_count": len(layers),
        "canvas": {
            "width": canvas_w,
            "height": max(canvas_h, len(layers) * layer_gap + 100),
        },
    }


def _node_label(nodes: list[dict[str, Any]], node_id: str) -> str:
    for node in nodes:
        if node.get("id") == node_id:
            return node.get("label") or node.get("name") or node_id
    return node_id


def _layered_layout(
    nodes: list[str],
    *,
    edges: list[dict[str, str]] | None,
    layout: LayoutKind,
    width: float,
    height: float,
) -> dict[str, Any]:
    edges = list(edges or [])
    if not nodes:
        raise OskillError("dag_visual_layout: nodes must not be empty")

    node_set = set(nodes)
    for edge in edges:
        if edge.get("from") not in node_set or edge.get("to") not in node_set:
            raise OskillError(f"dag_visual_layout: edge references unknown node: {edge}")

    indegree = {node: 0 for node in nodes}
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in edges:
        adjacency[edge["from"]].append(edge["to"])
        indegree[edge["to"]] += 1

    level_of: dict[str, int] = {}
    remaining = set(nodes)
    level = 0
    cycle = False
    while remaining:
        ready = sorted(node for node in remaining if indegree[node] == 0)
        if not ready:
            cycle = True
            break
        for node in ready:
            level_of[node] = level
            remaining.discard(node)
            for dst in adjacency[node]:
                indegree[dst] -= 1
        level += 1
    if cycle:
        for node in remaining:
            level_of[node] = 0

    max_level = max(level_of.values()) if level_of else 0
    positions: dict[str, dict[str, float]] = {}
    levels: dict[int, list[str]] = {}
    for node in nodes:
        levels.setdefault(level_of[node], []).append(node)

    for node_level, members in levels.items():
        count = len(members)
        for index, node in enumerate(sorted(members)):
            if layout == "radial":
                angle = (2 * math.pi * index / count) if count > 1 else 0.0
                radius = height * (0.5 + 0.4 * node_level / max(1, max_level))
                positions[node] = {
                    "x": round(width / 2 + radius * math.cos(angle), 2),
                    "y": round(height / 2 + radius * math.sin(angle), 2),
                    "level": node_level,
                }
            else:
                positions[node] = {
                    "x": round(
                        width * (0.5 + (index - (count - 1) / 2) * 0.8 / max(1, count)),
                        2,
                    ),
                    "y": round(height * (node_level + 0.5) / max(1, max_level + 1), 2),
                    "level": node_level,
                }

    return {
        "layout": layout,
        "positions": positions,
        "levels": levels,
        "width": width,
        "height": height,
        "cycle_detected": cycle,
    }
