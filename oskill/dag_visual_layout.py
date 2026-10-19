"""oskill.dag_visual_layout — DAG node layout engine for visual workflow canvas.

Takes a workflow graph (nodes + edges) and computes 2D positions using a
deterministic layered topological layout (Sugiyama-style, lightweight).
Also tracks per-node execution status for the real-time canvas.

3O element: ``oskill.dag_visual_layout``.
"""

from __future__ import annotations

from typing import Any


def dag_visual_layout(
    graph: dict[str, Any],
    status_map: dict[str, str] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compute 2D node positions for a DAG workflow canvas.

    Args:
        graph: {"nodes": [{id, label, ...}], "edges": [{from, to}]}
        status_map: Optional {node_id: "pending"|"running"|"completed"|"failed"|"blocked"}
        context: Optional config (canvas_width, canvas_height, layer_gap).

    Returns:
        {nodes: [{id, label, x, y, status, ...}], edges: [{from, to, ...}], canvas: {w, h}}
    """
    ctx = context or {}
    nodes = list(graph.get("nodes", []))
    edges = list(graph.get("edges", []))
    statuses = dict(status_map or {})

    canvas_w = int(ctx.get("canvas_width", 1200))
    canvas_h = int(ctx.get("canvas_height", 800))
    layer_gap = int(ctx.get("layer_gap", 120))
    node_gap = int(ctx.get("node_gap", 80))

    # topological layering (longest-path heuristic)
    in_degree: dict[str, int] = {n.get("id", "?"): 0 for n in nodes}
    adj: dict[str, list[str]] = {n.get("id", "?"): [] for n in nodes}
    for e in edges:
        u, v = e.get("from", ""), e.get("to", "")
        if u in adj and v not in adj.get(u, []):
            adj[u].append(v)
        if v in in_degree:
            in_degree[v] = in_degree.get(v, 0) + 1

    layers: list[list[str]] = []
    assigned: set[str] = set()
    queue = [nid for nid, deg in in_degree.items() if deg == 0]

    while queue:
        layers.append(list(queue))
        assigned.update(queue)
        next_q = []
        for nid in queue:
            for v in adj.get(nid, []):
                in_degree[v] = in_degree.get(v, 1) - 1
                if in_degree[v] <= 0 and v not in assigned and v not in next_q:
                    next_q.append(v)
        queue = next_q

    # remaining nodes (cycles)
    remaining = [nid for nid in in_degree if nid not in assigned]
    if remaining:
        layers.append(remaining)

    # compute positions
    positioned: list[dict[str, Any]] = []
    for li, layer in enumerate(layers):
        layer_w = max(1, len(layer)) * node_gap
        x_start = max(50, (canvas_w - layer_w) // 2)
        y = 50 + li * layer_gap
        for ni, nid in enumerate(layer):
            positioned.append({
                "id": nid,
                "label": _node_label(nodes, nid),
                "x": x_start + ni * node_gap,
                "y": y,
                "status": statuses.get(nid, "pending"),
                "layer": li,
            })

    return {
        "status": "computed",
        "nodes": positioned,
        "edges": edges,
        "layer_count": len(layers),
        "canvas": {"width": canvas_w, "height": max(canvas_h, len(layers) * layer_gap + 100)},
    }


def _node_label(nodes: list[dict], nid: str) -> str:
    for n in nodes:
        if n.get("id") == nid:
            return n.get("label") or n.get("name") or nid
    return nid
