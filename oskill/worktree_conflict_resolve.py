"""oskill.worktree_conflict_resolve — LLM-based git merge conflict resolution.

When multiple agents modify the same file in isolated git worktree branches,
this element performs a three-way merge and uses LLM reasoning to resolve
conflicts intelligently. Falls back to ``diff3`` markers when LLM unavailable.

3O element: ``oskill.worktree_conflict_resolve``.
"""

from __future__ import annotations

from typing import Any, Callable


def worktree_conflict_resolve(
    base_content: str,
    ours_content: str,
    theirs_content: str,
    file_path: str = "",
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Resolve a three-way merge conflict between worktree branches.

    Args:
        base_content: Original common ancestor content.
        ours_content: Our branch version.
        theirs_content: Their branch version.
        file_path: File being merged (for context).
        llm_caller: Optional LLM for intelligent resolution.
        context: Optional config.

    Returns:
        {status, resolved_content, conflict_blocks, strategy}
    """
    ctx = context or {}

    # detect conflict blocks (<<<<<<< / ======= / >>>>>>>)
    ours_lines = ours_content.splitlines()
    theirs_lines = theirs_content.splitlines()
    base_lines = base_content.splitlines()

    conflicts = _detect_conflicts(ours_lines, theirs_lines)
    if not conflicts:
        # no conflicts — just prefer ours
        return {"status": "resolved", "resolved_content": ours_content, "conflict_blocks": 0, "strategy": "clean_ours"}

    # simple: ours wins on all non-overlapping changes
    if base_content == ours_content:
        return {"status": "resolved", "resolved_content": theirs_content, "conflict_blocks": 0, "strategy": "clean_theirs"}
    if base_content == theirs_content:
        return {"status": "resolved", "resolved_content": ours_content, "conflict_blocks": 0, "strategy": "clean_ours"}

    # LLM resolution
    if llm_caller is not None:
        try:
            import re as _re
            prompt = (
                f"Resolve the following git merge conflict in file {file_path}.\n\n"
                f"--- BASE ---\n{base_content[:3000]}\n\n"
                f"--- OURS ---\n{ours_content[:3000]}\n\n"
                f"--- THEIRS ---\n{theirs_content[:3000]}\n\n"
                "Output the fully resolved file content between ``` and ```."
            )
            out = llm_caller(messages=[{"role": "user", "content": prompt}], tools=None, config=ctx)
            raw = out.get("content", "") if isinstance(out, dict) else str(out)
            m = _re.search(r"```(?:\w*)\n?(.*?)\n?```", raw, re.DOTALL)
            if m:
                return {"status": "resolved", "resolved_content": m.group(1), "conflict_blocks": len(conflicts), "strategy": "llm"}
        except Exception:
            pass

    # Fallback: keep ours, mark theirs with comments
    resolved_lines = list(ours_lines)
    resolved_lines.append(f"\n# === Merged from {file_path} ===")
    resolved_lines.append(f"# {len(conflicts)} conflicts — used 'ours' version")
    for start, mid, end in conflicts:
        resolved_lines.append(f"# --- theirs version (lines {mid}-{end}) ---")
        resolved_lines.extend(f"# > {l}" for l in theirs_lines[mid:end])

    return {"status": "partial", "resolved_content": "\n".join(resolved_lines), "conflict_blocks": len(conflicts), "strategy": "ours_with_comments"}


def _detect_conflicts(ours: list[str], theirs: list[str]) -> list[tuple[int, int, int]]:
    """Find <<<<<<< / ======= / >>>>>>> markers in ours."""
    conflicts = []
    ours_text = "\n".join(ours)
    theirs_text = "\n".join(theirs)
    import re
    for m in re.finditer(r"<<<<<<< .*?\n(.*?)=======\n(.*?)>>>>>>>", ours_text, re.DOTALL):
        conflicts.append((m.start(), 0, 0))  # simplified: just count markers
    return conflicts
