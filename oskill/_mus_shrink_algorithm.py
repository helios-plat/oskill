"""oskill 技能层：MUS 最小矛盾核收缩算法。通过 Protocol 注入判定器，实现引擎解耦。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class OracleProtocol(Protocol):
    """可满足性判定器 Protocol —— 与 Z3/具体引擎物理隔离."""

    def __call__(self, subset: Sequence[str]) -> str: ...  # "sat", "unsat", "unknown"


def _mus_shrink_algorithm(
    core_subset: Sequence[str],
    *,
    oracle_checker: OracleProtocol,
    protected_ids: frozenset = frozenset(),
    max_checks: int = 200,
) -> dict[str, Any]:
    """删除法收缩 MUS (Minimal Unsatisfiable Subset).

    给定一个 UNSAT 核心约束集，通过逐个删除候选约束并询问 oracle 来寻找最小矛盾核。
    与具体求解引擎（Z3 / CVC5）完全解耦。

    算法:
    1. 对 core_subset 排序（确定性）
    2. 逐个尝试删除候选约束 cid
    3. 询问 oracle: trial_set 是否仍然 unsat?
       - 是 → 确认删除 cid
       - 否 → 保留 cid
    4. 受保护约束 (protected_ids) 不参与删除尝试

    Args:
        core_subset: 初始 UNSAT 约束集
        oracle_checker: 可满足性判定器
        protected_ids: 受保护不可删除的约束 ID 集合
        max_checks: 最大 oracle 询问次数（防止过度收缩）

    Returns:
        {
            "mus": list[str] — 最小矛盾核,
            "verified": bool — 是否经过充分验证,
            "checks": int — oracle 询问次数,
            "dropped": list[str] — 被确认可安全删除的约束,
        }
    """
    candidates = sorted(core_subset)
    current = list(candidates)
    checks = 0
    verified = True
    dropped: list[str] = []

    for cid in candidates:
        if cid not in current or cid in protected_ids:
            continue
        if checks >= max_checks:
            verified = False
            break

        trial = [x for x in current if x != cid]
        verdict = oracle_checker(trial)
        checks += 1

        if verdict == "unsat":
            current = trial
            dropped.append(cid)
        elif verdict == "unknown":
            verified = False

    return {
        "mus": sorted(current),
        "verified": verified,
        "checks": checks,
        "dropped": dropped,
    }
