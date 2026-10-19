"""oskill._backtranslate_diff — 将状态快照差异逆向翻译为可执行修复计划.

Stateless 纯算法。依赖 SnapshotStore + LLMCallerProtocol 注入.

组合: SnapshotStore (注入) + LLM caller (注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

from typing import Any, Protocol


class SnapshotStoreProtocol(Protocol):
    """快照存储 Protocol — 不 import obase，由调用方注入."""

    def diff(self, entity_id: str, version_a: int, version_b: int) -> dict[str, Any]: ...


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def _backtranslate_diff(
    entity_id: str,
    version_a: int,
    version_b: int,
    *,
    snapshot_store: SnapshotStoreProtocol,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """将状态快照差异逆向翻译为可执行的修复/回滚计划.

    流程:
    1. 从 snapshot_store 获取两个版本的 diff
    2. 用 LLM 将 diff 翻译为自然语言修复计划

    Args:
        entity_id: 实体标识
        version_a: 基准版本
        version_b: 目标版本
        snapshot_store: 快照存储（注入）
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "diff": {...},
            "repair_plan": str,
            "rollback_possible": bool,
        }
    """
    try:
        diff = snapshot_store.diff(entity_id, version_a, version_b)
    except Exception:
        diff = {"added": {}, "removed": {}, "changed": {}}

    added_count = len(diff.get("added", {}))
    removed_count = len(diff.get("removed", {}))
    changed_count = len(diff.get("changed", {}))

    if added_count == 0 and removed_count == 0 and changed_count == 0:
        return {
            "diff": diff,
            "repair_plan": "No differences detected — no action needed.",
            "rollback_possible": True,
        }

    import json

    prompt = (
        f"Entity: {entity_id}\n"
        f"Version A (baseline v{version_a}) → Version B (target v{version_b})\n"
        f"Diff:\n{json.dumps(diff, indent=2, default=str)[:2000]}\n\n"
        f"Translate this state diff into a concise repair/rollback plan "
        f"(2-4 numbered steps). Start with '1.'"
    )

    try:
        repair_plan = llm_caller(prompt, temperature=0.0).strip()
    except Exception:
        repair_plan = (
            f"Manual review needed: {added_count} added, "
            f"{removed_count} removed, {changed_count} changed."
        )

    # 回滚可能性：如果没有不可逆的删除，则回滚可行
    rollback_possible = removed_count == 0

    return {
        "diff": diff,
        "repair_plan": repair_plan,
        "rollback_possible": rollback_possible,
    }
