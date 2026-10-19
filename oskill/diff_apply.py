"""3O 范式全栈 — Unified Diff 应用技能 (纯内存, 无 IO).

扁平命名空间规范入口; 实现委托自既有 oskill._apply_unified_diff 单源。
"""

from __future__ import annotations

from oskill._apply_unified_diff import apply_unified_diff as _apply_unified_diff
from oskill._types import ApplyResult


def apply_unified_diff(
    original: str,
    *,
    diff: str,
) -> ApplyResult:
    """技能 16: 将 unified diff 应用到原始内容 (纯内存, 无 IO)。

    Composes oskill: [apply_unified_diff (内部 _apply_unified_diff)]
    """
    return _apply_unified_diff(original, diff=diff)
