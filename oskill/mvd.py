"""oskill.mvd — 最小可行部署 (FDE 书第2章 3O 内化)。

MVD (Minimum Viable Deployment): 用最小工程投入, 在客户真实环境里对真实
痛点验证一次价值真实发生。MVP 裁判是市场, MVD 裁判是客户的具体业务。

三条军规 (确定性合规检查) + 五步流水线 (阶段机):
  * 军规1 真实数据 — 假数据验证 = 概念验证坟墓第一块砖;
  * 军规2 缩小范围不缩价值 — 只砍覆盖面不砍深度 (切口价值密度);
  * 军规3 定死截止时间 — 周级验证 (Palantir 训练营 5 天 / Sierra 4 周)。
流水线: Day0 筹备 → Day1 接入 → Day2-3 构建 → Day4-5 演示拍板。

零 veya 反向依赖: 数据源/范围/期限由调用方注入; 纯检查 + 阶段机。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ── 三条军规 ─────────────────────────────────────────────────────────

RULE_REAL_DATA = "real_data"
RULE_SCOPE_NOT_VALUE = "scope_not_value"
RULE_DEADLINE = "deadline"
RULES = (RULE_REAL_DATA, RULE_SCOPE_NOT_VALUE, RULE_DEADLINE)


@dataclass
class MvdVerdict:
    """MVD 三军规合规检查结果。

    Attributes:
        ok: 三条军规全部通过。
        violations: 违规军规列表。
        details: 每条军规检查详情。
    """

    ok: bool
    violations: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "violations": self.violations, "details": self.details}


def mvd_check(
    *,
    data_source: str,
    scope_depth_kept: bool,
    deadline_weeks: float,
    customer_data: bool | None = None,
) -> MvdVerdict:
    """MVD 三军规合规检查。

    Args:
        data_source: 数据来源说明 ("客户真实业务数据" / "脱敏样例" / "演示数据")。
        scope_depth_kept: 是否保持方案深度 (只缩小覆盖面)。
        deadline_weeks: 验证期限 (周)。
        customer_data: 客户是否带自己的真实业务数据 (None 时按 data_source 判断)。

    Returns:
        MvdVerdict (violations 列出违规军规)。

    Example:
        >>> v = mvd_check(data_source="客户真实数据", scope_depth_kept=True, deadline_weeks=5)
        >>> v.ok
        True
    """
    violations: list[str] = []
    details: dict[str, Any] = {}

    # 军规1: 真实数据
    real = (
        customer_data
        if customer_data is not None
        else ("真实" in data_source and "客户" in data_source)
    )
    details[RULE_REAL_DATA] = {
        "ok": real,
        "data_source": data_source,
        "note": "假数据验证 = 概念验证坟墓第一块砖" if not real else "",
    }
    if not real:
        violations.append(RULE_REAL_DATA)

    # 军规2: 缩小范围不缩价值
    details[RULE_SCOPE_NOT_VALUE] = {
        "ok": bool(scope_depth_kept),
        "note": "只砍覆盖面, 不砍方案深度 (端到端单点价值密度)",
    }
    if not scope_depth_kept:
        violations.append(RULE_SCOPE_NOT_VALUE)

    # 军规3: 定死截止时间 (周级)
    deadline_ok = 0 < deadline_weeks <= 4
    details[RULE_DEADLINE] = {
        "ok": deadline_ok,
        "deadline_weeks": deadline_weeks,
        "note": "周级验证 (Palantir 训练营 5 天 / Sierra 4 周); 6 个月 = 概念验证坟墓再开工",
    }
    if not deadline_ok:
        violations.append(RULE_DEADLINE)

    return MvdVerdict(ok=not violations, violations=violations, details=details)


# ── 五步流水线 (阶段机) ──────────────────────────────────────────────

PHASE_DAY0 = "day0_prep"
PHASE_DAY1 = "day1_ingest"
PHASE_DAY2_3 = "day2_3_build"
PHASE_DAY4_5 = "day4_5_demo"
PHASE_DONE = "done"
PHASES = (PHASE_DAY0, PHASE_DAY1, PHASE_DAY2_3, PHASE_DAY4_5, PHASE_DONE)

PHASE_NAMES = {
    PHASE_DAY0: "筹备: 锁定聚焦战场 (拒绝宏大叙事)",
    PHASE_DAY1: "接入: 打通客户系统, 真实数据 + 本体模型",
    PHASE_DAY2_3: "构建: FDE 与客户背靠背写代码, 可执行自动化工作流",
    PHASE_DAY4_5: "演示拍板: 活软件界面, 业务高管亲手点击",
    PHASE_DONE: "完成",
}


@dataclass
class MvdPipeline:
    """MVD 五步流水线状态机 (Palantir 训练营形态, 五天封顶)。"""

    phase: str = PHASE_DAY0
    max_days: int = 5
    log: list[str] = field(default_factory=list)

    def advance(self) -> str:
        """推进到下一阶段 (返回新阶段名)。

        Raises:
            RuntimeError: 已 done 或超期。
        """
        if self.phase == PHASE_DONE:
            raise RuntimeError("pipeline already done")
        idx = PHASES.index(self.phase)
        self.phase = PHASES[min(idx + 1, len(PHASES) - 1)]
        self.log.append(self.phase)
        return self.phase

    def current(self) -> str:
        """当前阶段名称 (人读)。"""
        return PHASE_NAMES[self.phase]

    def is_done(self) -> bool:
        """流水线完成 (演示拍板)。"""
        return self.phase == PHASE_DONE

    def summary(self) -> dict[str, Any]:
        """流水线概览。"""
        return {
            "phase": self.phase,
            "phase_name": self.current(),
            "max_days": self.max_days,
            "log": list(self.log),
        }


__all__ = [
    "MvdPipeline",
    "MvdVerdict",
    "PHASE_DAY0",
    "PHASE_DAY1",
    "PHASE_DAY2_3",
    "PHASE_DAY4_5",
    "PHASE_DONE",
    "PHASES",
    "RULE_DEADLINE",
    "RULE_REAL_DATA",
    "RULE_SCOPE_NOT_VALUE",
    "RULES",
    "mvd_check",
]
