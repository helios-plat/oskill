"""oskill.dag_validator — graph dict → cycle + empty-acceptance check. Pure."""

from __future__ import annotations

from typing import Any

from obase.veya_workspace import TaskNode

from oskill.dag_compiler import validate_taskgraph_dag as validate_task_nodes


def validate_taskgraph_dag(graph_dict: dict[str, Any] | list[Any]) -> list[str]:
    """Topo-sort for cycles. Every leaf must have non-empty acceptance."""
    if isinstance(graph_dict, list):
        raw_tasks = graph_dict
    elif isinstance(graph_dict, dict):
        raw_tasks = graph_dict.get("tasks")
        if raw_tasks is None and isinstance(graph_dict.get("graph"), dict):
            raw_tasks = graph_dict["graph"].get("tasks")
    else:
        return ["task graph is not a dict or list"]
    if not isinstance(raw_tasks, list) or not raw_tasks:
        return ["empty task graph"]
    nodes: list[TaskNode] = []
    errors: list[str] = []
    for index, item in enumerate(raw_tasks, start=1):
        node, err = _as_node(item, index=index)
        if err:
            errors.append(err)
            continue
        assert node is not None
        if not any(str(rule).strip() for rule in node.acceptance):
            errors.append(f"{node.id} has empty acceptance")
        nodes.append(node)
    if nodes:
        errors.extend(validate_task_nodes(nodes))
    return errors


def _as_node(item: Any, *, index: int) -> tuple[TaskNode | None, str | None]:
    if isinstance(item, TaskNode):
        return item, None
    if not isinstance(item, dict):
        return None, f"task[{index}] is not an object"
    payload = dict(item)
    payload.setdefault("id", f"T{index}")
    payload.setdefault("title", payload.get("id", f"T{index}"))
    payload.setdefault("instruction", payload.get("title") or "")
    if isinstance(payload.get("acceptance"), str):
        text = payload["acceptance"].strip()
        payload["acceptance"] = [text] if text else []
    try:
        return TaskNode.model_validate(payload), None
    except Exception as exc:
        ident = payload.get("id") or f"task[{index}]"
        return None, f"{ident} invalid: {exc}"
