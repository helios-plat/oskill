"""oskill.context_assembler — densify snapshot + goal. Pure, no I/O."""

from __future__ import annotations

from typing import Any

from obase.workspace_snapshot import WorkspaceSnapshot

_MAX_DIFF = 12_000
_MAX_AST_KEYS = 40


def assemble_intent_context(snapshot: WorkspaceSnapshot | dict[str, Any], goal: str) -> str:
    """Sync, pure: pack snapshot for G0 triage. Does not plan tasks."""
    return (
        "Decide plan | ask | refuse. Do not write code or split tasks.\n"
        f"{_pack_snapshot(snapshot, goal)}"
    )


def assemble_boss_context(
    snapshot: WorkspaceSnapshot | dict[str, Any],
    goal: str,
    brief: dict[str, Any] | None = None,
) -> str:
    """Sync, pure: drop noise and pack git/AST into a planning prompt."""
    packed = _pack_snapshot(snapshot, goal)
    if not brief:
        return packed
    interpretation = str(brief.get("interpretation") or "").strip()
    in_scope = ", ".join(brief.get("in_scope_files") or []) or "(unspecified)"
    out_scope = ", ".join(brief.get("out_of_scope_files") or []) or "(none)"
    draft = "; ".join(brief.get("acceptance_draft") or []) or "(none)"
    assumptions = "; ".join(brief.get("assumptions") or []) or "(none)"
    return (
        "Intent (authoritative — do not re-interpret the raw request):\n"
        f"- interpretation: {interpretation or '(missing)'}\n"
        f"- in scope: {in_scope}\n"
        f"- out of scope: {out_scope}\n"
        f"- acceptance draft: {draft}\n"
        f"- assumptions: {assumptions}\n"
        f"{packed}"
    )


def _pack_snapshot(snapshot: WorkspaceSnapshot | dict[str, Any], goal: str) -> str:
    git_diff, ast_summary, active = _unpack(snapshot)
    diff = git_diff.strip() or "(clean working tree)"
    if len(diff) > _MAX_DIFF:
        diff = diff[:_MAX_DIFF] + "\n...[diff truncated]..."
    files = ", ".join(active[:40]) if active else "(none)"
    return (
        f"Goal: {str(goal).strip()}\n"
        f"Active files: {files}\n"
        f"Git Diff:\n{diff}\n"
        f"AST Summary:\n{_fmt_ast(ast_summary)}"
    )


def _unpack(
    snapshot: WorkspaceSnapshot | dict[str, Any],
) -> tuple[str, dict[str, Any], list[str]]:
    if isinstance(snapshot, WorkspaceSnapshot):
        return snapshot.git_diff, snapshot.ast_summary, list(snapshot.active_files)
    return (
        str(snapshot.get("git_diff") or ""),
        dict(snapshot.get("ast_summary") or {}),
        list(snapshot.get("active_files") or []),
    )


def _fmt_ast(ast_summary: dict[str, Any]) -> str:
    if not ast_summary:
        return "(none)"
    lines: list[str] = []
    for path, info in list(ast_summary.items())[:_MAX_AST_KEYS]:
        if not isinstance(info, dict):
            lines.append(f"- {path}: {info}")
            continue
        if info.get("error") or info.get("skipped") or info.get("kind"):
            tag = info.get("error") or info.get("skipped") or info.get("kind")
            lines.append(f"- {path}: {tag}")
            continue
        classes = ",".join(info.get("classes") or []) or "-"
        funcs = ",".join(info.get("functions") or []) or "-"
        lines.append(f"- {path}: classes={classes}; funcs={funcs}")
    return "\n".join(lines) if lines else "(none)"
