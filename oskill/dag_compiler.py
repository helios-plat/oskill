"""oskill.dag_compiler — tasks.md → TaskNode list + cycle check. Pure."""

from __future__ import annotations

import re
from typing import Any

from obase.veya_workspace import TaskNode

_CHECK = re.compile(
    r"^(?P<indent>\s*)[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<body>.+)$"
)
_ID_TITLE = re.compile(r"^(?P<id>T\d+(?:\.\d+)*)\s+[:.\-]?\s*(?P<title>.+)$", re.I)
_DEPENDS = re.compile(r"depends(?:\s+on)?\s*:\s*(.+)$", re.I)
_ACCEPT = re.compile(r"accept(?:ance)?\s*:\s*(.+)$", re.I)
_PARALLEL = re.compile(r"\[P\]", re.I)


def compile_spec_to_dag(tasks_md_content: str) -> list[TaskNode]:
    """Parse Spec Kit checkboxes. Indent → parent dep. Explicit Depends: wins."""
    if not tasks_md_content or not tasks_md_content.strip():
        return []
    parsed: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in tasks_md_content.splitlines():
        match = _CHECK.match(raw.rstrip())
        if match:
            if current:
                parsed.append(current)
            indent = len(match.group("indent").replace("\t", "    "))
            body = match.group("body").strip()
            ident, title = _split_id_title(body, index=len(parsed) + 1)
            current = {
                "id": ident,
                "title": title,
                "indent": indent,
                "instruction_parts": [title],
                "acceptance": [],
                "depends_on": [],
                "explicit_deps": False,
                "parallel": False,
            }
            continue
        if current is None or not raw.strip():
            continue
        line = raw.strip()
        dep = _DEPENDS.match(line)
        if dep:
            current["depends_on"] = _split_ids(dep.group(1))
            current["explicit_deps"] = True
            continue
        acc = _ACCEPT.match(line)
        if acc:
            current["acceptance"].extend(_split_list(acc.group(1)))
            continue
        if line.startswith("- "):
            current["instruction_parts"].append(line[2:].strip())
        else:
            current["instruction_parts"].append(line)
    if current:
        parsed.append(current)

    nodes: list[TaskNode] = []
    stack: list[tuple[int, str]] = []
    prev_id = ""
    for item in parsed:
        if not item["explicit_deps"]:
            deps: list[str] = []
            # Check for [P] parallel marker in task body
            body_text = item.get("title", "") + " " + " ".join(item.get("instruction_parts", []))
            if _PARALLEL.search(body_text):
                item["parallel"] = True
            else:
                item["parallel"] = False
            while stack and stack[-1][0] >= item["indent"]:
                stack.pop()
            if stack:
                deps.append(stack[-1][1])
            elif prev_id:
                deps.append(prev_id)
            item["depends_on"] = deps
        stack.append((item["indent"], item["id"]))
        prev_id = item["id"]
        instruction = "\n".join(p for p in item["instruction_parts"] if p).strip()
        nodes.append(
            TaskNode(
                id=item["id"],
                title=item["title"],
                instruction=instruction or item["title"],
                acceptance=item["acceptance"] or [f"{item['title']} is done"],
                depends_on=item["depends_on"],
                parallel=item.get("parallel", False),
            )
        )
    return nodes


def validate_taskgraph_dag(
    nodes: list[TaskNode],
    *,
    max_leaf_tasks: int = 40,
) -> list[str]:
    errors: list[str] = []
    ids = [n.id for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate task id")
    if len(nodes) > max_leaf_tasks:
        errors.append(f"too many tasks: {len(nodes)} > {max_leaf_tasks}")
    known = set(ids)
    incoming = {n.id: 0 for n in nodes}
    edges: dict[str, list[str]] = {n.id: [] for n in nodes}
    for node in nodes:
        for dep in node.depends_on:
            if dep not in known:
                errors.append(f"{node.id} depends on missing {dep}")
                continue
            if dep == node.id:
                errors.append(f"{node.id} depends on itself")
                continue
            edges[dep].append(node.id)
            incoming[node.id] += 1
    ready = [nid for nid, deg in incoming.items() if deg == 0]
    seen = 0
    while ready:
        nid = ready.pop()
        seen += 1
        for child in edges[nid]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if nodes and seen != len(nodes):
        errors.append("cycle in task graph")
    return errors


def pick_ready_task_ids(
    nodes: list[TaskNode],
    *,
    completed_ids: set[str] | None = None,
) -> list[str]:
    done = completed_ids or set()
    ready: list[str] = []
    for node in nodes:
        if node.status not in {"pending", "ready"}:
            continue
        if all(dep in done for dep in node.depends_on):
            ready.append(node.id)
    return ready


def _split_id_title(body: str, *, index: int) -> tuple[str, str]:
    match = _ID_TITLE.match(body)
    if match:
        return match.group("id"), match.group("title").strip()
    return f"T{index}", body


def _split_ids(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[, ]+", text) if part.strip()]


def _split_list(text: str) -> list[str]:
    if ";" in text:
        return [p.strip() for p in text.split(";") if p.strip()]
    return [text.strip()] if text.strip() else []
