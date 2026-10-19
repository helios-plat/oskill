"""Worktree merge-conflict resolution.

Supports both the legacy three-way content API and the Veya conflict-block
API selected by passing a list of conflicts.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal

from oskill._exceptions import OskillError

Strategy = Literal["ours", "theirs", "merge"]


def worktree_conflict_resolve(
    base_content_or_conflicts: str | list[dict[str, Any]],
    ours_content: str | None = None,
    theirs_content: str | None = None,
    file_path: str = "",
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    *,
    strategy: Strategy = "merge",
    **kwargs: Any,
) -> dict[str, Any]:
    """Resolve conflict blocks or run the legacy three-way merge helper."""
    if isinstance(base_content_or_conflicts, list):
        return _resolve_conflict_blocks(base_content_or_conflicts, strategy)
    return _legacy_three_way(
        base_content_or_conflicts,
        ours_content or "",
        theirs_content or "",
        file_path,
        llm_caller,
        context,
    )


def _resolve_conflict_blocks(
    conflicts: list[dict[str, Any]],
    strategy: Strategy,
) -> dict[str, Any]:
    if not conflicts:
        raise OskillError("worktree_conflict_resolve: conflicts must not be empty")
    if strategy not in ("ours", "theirs", "merge"):
        raise OskillError(f"worktree_conflict_resolve: unknown strategy {strategy!r}")

    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for conflict in conflicts:
        file = str(conflict.get("file", "?"))
        ours = str(conflict.get("ours", ""))
        theirs = str(conflict.get("theirs", ""))
        if strategy == "ours":
            resolved.append({"file": file, "strategy": "ours", "content": ours})
        elif strategy == "theirs":
            resolved.append({"file": file, "strategy": "theirs", "content": theirs})
        else:
            merged, ok = _line_merge(ours, theirs)
            if ok:
                resolved.append({"file": file, "strategy": "merge", "content": merged})
            else:
                unresolved.append({"file": file, "reason": merged})

    return {"resolved": resolved, "unresolved": unresolved, "total": len(conflicts)}


def _line_merge(ours: str, theirs: str) -> tuple[str, bool]:
    ours_lines = ours.splitlines()
    theirs_lines = theirs.splitlines()
    if ours_lines == theirs_lines:
        return ours, True
    if not ours_lines:
        return theirs, True
    if not theirs_lines:
        return ours, True

    merged: list[str] = []
    for index in range(max(len(ours_lines), len(theirs_lines))):
        ours_line = ours_lines[index] if index < len(ours_lines) else None
        theirs_line = theirs_lines[index] if index < len(theirs_lines) else None
        if ours_line is None:
            merged.append(f"+ {theirs_line}")
        elif theirs_line is None:
            merged.append(f"- {ours_line}")
        elif ours_line == theirs_line:
            merged.append(ours_line)
        else:
            return _marked(ours_lines, theirs_lines), False
    return "\n".join(merged), True


def _marked(ours_lines: list[str], theirs_lines: list[str]) -> str:
    output = ["<<<<<<< ours", *ours_lines, "=======", *theirs_lines, ">>>>>>> theirs"]
    return "\n".join(output)


def _legacy_three_way(
    base_content: str,
    ours_content: str,
    theirs_content: str,
    file_path: str,
    llm_caller: Callable | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    ctx = context or {}
    ours_lines = ours_content.splitlines()
    conflicts = _detect_conflicts(ours_lines)
    if not conflicts:
        return {
            "status": "resolved",
            "resolved_content": ours_content,
            "conflict_blocks": 0,
            "strategy": "clean_ours",
        }
    if base_content == ours_content:
        return {
            "status": "resolved",
            "resolved_content": theirs_content,
            "conflict_blocks": 0,
            "strategy": "clean_theirs",
        }
    if base_content == theirs_content:
        return {
            "status": "resolved",
            "resolved_content": ours_content,
            "conflict_blocks": 0,
            "strategy": "clean_ours",
        }

    if llm_caller is not None:
        try:
            prompt = (
                f"Resolve the following git merge conflict in file {file_path}.\n\n"
                f"--- BASE ---\n{base_content[:3000]}\n\n"
                f"--- OURS ---\n{ours_content[:3000]}\n\n"
                f"--- THEIRS ---\n{theirs_content[:3000]}\n\n"
                "Output the fully resolved file content between ``` and ```."
            )
            out = llm_caller(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
                config=ctx,
            )
            raw = out.get("content", "") if isinstance(out, dict) else str(out)
            match = re.search(r"```(?:\w*)\n?(.*?)\n?```", raw, re.DOTALL)
            if match:
                return {
                    "status": "resolved",
                    "resolved_content": match.group(1),
                    "conflict_blocks": len(conflicts),
                    "strategy": "llm",
                }
        except Exception:
            pass

    resolved_lines = list(ours_lines)
    resolved_lines.append(f"\n# === Merged from {file_path} ===")
    resolved_lines.append(f"# {len(conflicts)} conflicts — used 'ours' version")
    for _start, _mid, _end in conflicts:
        resolved_lines.append("# --- theirs version ---")
    return {
        "status": "partial",
        "resolved_content": "\n".join(resolved_lines),
        "conflict_blocks": len(conflicts),
        "strategy": "ours_with_comments",
    }


def _detect_conflicts(ours: list[str]) -> list[tuple[int, int, int]]:
    ours_text = "\n".join(ours)
    return [
        (match.start(), 0, 0)
        for match in re.finditer(r"<<<<<<< .*?\n(.*?)=======\n(.*?)>>>>>>>", ours_text, re.DOTALL)
    ]
