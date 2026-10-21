"""oskill.worktree_conflict_resolve — Worktree 合并冲突解决.

纯算法：对冲突块（ours/theirs 文本对）按策略解决：
- "ours"：保留本地版本
- "theirs"：保留分支版本
- "merge"：行级智能合并（相同行保留，差异行 both 拼接）

stateless。

Example:
    >>> r = worktree_conflict_resolve([{"file": "a.py", "ours": "x=1", "theirs": "x=2"}],
    ...                                strategy="theirs")
    >>> r["resolved"][0]["content"]
    'x=2'
"""

from __future__ import annotations

from typing import Any, Literal

from oskill._exceptions import OskillError

Strategy = Literal["ours", "theirs", "merge"]


def worktree_conflict_resolve(
    conflicts: list[dict[str, Any]],
    *,
    strategy: Strategy = "merge",
) -> dict[str, Any]:
    """解决合并冲突块。

    Args:
        conflicts: 冲突列表，每项 {"file", "ours", "theirs"}（行文本）。
        strategy: ours / theirs / merge。

    Returns:
        {"resolved": [{"file", "strategy", "content"}],
         "unresolved": [{"file", "reason"}], "total": int}

    Raises:
        OskillError: conflicts 为空 / strategy 非法。
    """
    if not conflicts:
        raise OskillError("worktree_conflict_resolve: conflicts must not be empty")
    if strategy not in ("ours", "theirs", "merge"):
        raise OskillError(f"worktree_conflict_resolve: unknown strategy {strategy!r}")

    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for c in conflicts:
        file = str(c.get("file", "?"))
        ours = str(c.get("ours", ""))
        theirs = str(c.get("theirs", ""))
        if strategy == "ours":
            resolved.append({"file": file, "strategy": "ours", "content": ours})
        elif strategy == "theirs":
            resolved.append({"file": file, "strategy": "theirs", "content": theirs})
        else:
            merged, ok = _line_merge(ours, theirs)
            if ok:
                resolved.append({"file": file, "strategy": "merge", "content": merged})
            else:
                unresolved.append({"file": file, "reason": "unmergeable blocks"})

    return {"resolved": resolved, "unresolved": unresolved, "total": len(conflicts)}


def _line_merge(ours: str, theirs: str) -> tuple[str, bool]:
    """行级合并：相同行保留，差异行拼接（marker 标注）。"""
    ours_lines = ours.splitlines()
    theirs_lines = theirs.splitlines()
    if ours_lines == theirs_lines:
        return ours, True
    # 一方为空 → 非空方胜出
    if not ours_lines:
        return theirs, True
    if not theirs_lines:
        return ours, True
    merged: list[str] = []
    max_len = max(len(ours_lines), len(theirs_lines))
    for i in range(max_len):
        o = ours_lines[i] if i < len(ours_lines) else None
        t = theirs_lines[i] if i < len(theirs_lines) else None
        if o is None:
            merged.append(f"+ {t}")
        elif t is None:
            merged.append(f"- {o}")
        elif o == t:
            merged.append(o)
        else:
            # 行级冲突：无法自动裁决 → 标记并判不可自动合并
            return _marked(ours_lines, theirs_lines), False
    return "\n".join(merged), True


def _marked(ours_lines: list[str], theirs_lines: list[str]) -> str:
    out = ["<<<<<<< ours"]
    out.extend(ours_lines)
    out.append("=======")
    out.extend(theirs_lines)
    out.append(">>>>>>> theirs")
    return "\n".join(out)
