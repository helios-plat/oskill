"""oskill.dag_visual_layout — DAG layout.

Algorithm: compute layered (topological) or radial layout for DAG,
output node positions and levels for visualization. stateless.
"""

from __future__ import annotations

from typing import Any, Literal

from oskill._exceptions import OskillError

LayoutKind = Literal["layered", "radial"]


def dag_visual_layout(
    nodes: list[str],
    *,
    edges: list[dict[str, str]],
    layout: LayoutKind = "layered",
    width: float = 100.0,
    height: float = 100.0,
) -> dict[str, Any]:
    """DAG 布局计算。

    Args:
        nodes: 节点 ID 列表。
        edges: 依赖边 [{from, to}]。
        layout: "layered"（拓扑分层纵向）或 "radial"（根为中心放射）。
        width / height: 画布尺寸。

    Returns:
        {"layout": str, "positions": {node: {"x", "y", "level"}},
         "levels": {level: [nodes]}, "width": float, "height": float,
         "cycle_detected": bool}

    Raises:
        OskillError: nodes 为空 / 边引用未知节点。
    """
    if not nodes:
        raise OskillError("dag_visual_layout: nodes must not be empty")
    node_set = set(nodes)
    for e in edges:
        if e.get("from") not in node_set or e.get("to") not in node_set:
            raise OskillError(f"dag_visual_layout: edge references unknown node: {e}")

    # 分层（Kahn；有环时退化为原始顺序单层标记）
    indeg = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = {n: [] for n in nodes}
    for e in edges:
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] += 1

    level_of: dict[str, int] = {}
    remaining = set(nodes)
    level = 0
    cycle = False
    while remaining:
        ready = sorted(n for n in remaining if indeg[n] == 0)
        if not ready:
            cycle = True
            break
        for n in ready:
            level_of[n] = level
            remaining.discard(n)
            for m in adj[n]:
                indeg[m] -= 1
        level += 1
    if cycle:
        for n in remaining:  # pragma: no cover - 仅剩环上节点
            level_of[n] = 0

    max_level = max(level_of.values()) if level_of else 0

    positions: dict[str, dict[str, float]] = {}
    levels: dict[int, list[str]] = {}
    for n in nodes:
        lvl = level_of[n]
        levels.setdefault(lvl, []).append(n)
    for lvl, members in levels.items():
        count = len(members)
        for i, n in enumerate(sorted(members)):
            if layout == "radial":
                import math

                angle = (2 * math.pi * i / count) if count > 1 else 0.0
                radius = height * (0.5 + 0.4 * lvl / max(1, max_level))
                positions[n] = {
                    "x": round(width / 2 + radius * math.cos(angle), 2),
                    "y": round(height / 2 + radius * math.sin(angle), 2),
                    "level": lvl,
                }
            else:
                positions[n] = {
                    "x": round(width * (0.5 + (i - (count - 1) / 2) * 0.8 / max(1, count)), 2),
                    "y": round(height * (lvl + 0.5) / max(1, max_level + 1), 2),
                    "level": lvl,
                }

    return {
        "layout": layout,
        "positions": positions,
        "levels": levels,
        "width": width,
        "height": height,
        "cycle_detected": cycle,
    }
