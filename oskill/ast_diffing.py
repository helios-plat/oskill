"""oskill.ast_diffing — compare two AST node lists. Pure. Ignores renames."""

from __future__ import annotations

from typing import Any


def compute_ast_diff(ast_v0: dict[str, Any], ast_v1: dict[str, Any]) -> dict[str, Any]:
    """Return added/removed logic keys and whether the change is meaningful."""
    left = _index(ast_v0.get("nodes") or [])
    right = _index(ast_v1.get("nodes") or [])
    added = [right[k] for k in right.keys() - left.keys()]
    removed = [left[k] for k in left.keys() - right.keys()]
    knowledge = any(n.get("kind") == "constant" for n in added + removed)
    logic = any(n.get("kind") in {"function", "class"} for n in added + removed)
    return {
        "has_meaningful_change": bool(added or removed),
        "added": added,
        "removed": removed,
        "knowledge_change": knowledge,
        "logic_change": logic,
    }


def _index(nodes: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for node in nodes:
        kind = node.get("kind")
        if kind == "constant":
            key = ("constant", node.get("name"), tuple(node.get("constants") or ()))
        else:
            # name dropped so a rename with the same shape is style noise
            key = (kind, node.get("arity"), node.get("shape"), tuple(node.get("constants") or ()))
        indexed[key] = node
    return indexed
