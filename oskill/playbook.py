"""oskill.playbook — 场景打法手册 (FDE 书第7章 3O 内化)。

"用打法手册沉淀复制效率" — 三属性 + 场景七件套:
  * **按场景组织** (非按功能): 每场景固定七件套 — ①典型痛点与契合检验
    ②尽调清单 (高危信号) ③数据集成雷区 ④评估验收指标模板 ⑤变革管理角色
    地图 ⑥计价扩容参考 ⑦历史复盘教训库;
  * **长在流程里**: 手册嵌入工作流 (尽调清单自动弹出/检查清单是硬关卡/
    复盘更新是必填产出) — 不嵌入流程 = 考古资料;
  * **必须"活"**: 负责人 / 版本 / 折旧 (半年检修删过时合并重复) — 没有
    负责人 = 比没有手册更糟。

零 veya 反向依赖: 纯数据模型 + 生命周期。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# ── 场景七件套 ───────────────────────────────────────────────────────

SECTION_PAIN_POINTS = "pain_points"  # ① 典型痛点与契合检验要点
SECTION_DUE_DILIGENCE = "due_diligence"  # ② 尽调清单 (高危信号)
SECTION_LANDMINES = "landmines"  # ③ 数据与集成已知雷区
SECTION_METRICS = "metrics"  # ④ 评估与验收指标模板
SECTION_ROLES = "roles"  # ⑤ 变革管理角色地图
SECTION_PRICING = "pricing"  # ⑥ 计价与扩容参考
SECTION_LESSONS = "lessons"  # ⑦ 历史复盘教训库
SECTIONS = (
    SECTION_PAIN_POINTS,
    SECTION_DUE_DILIGENCE,
    SECTION_LANDMINES,
    SECTION_METRICS,
    SECTION_ROLES,
    SECTION_PRICING,
    SECTION_LESSONS,
)

SECTION_NAMES = {
    SECTION_PAIN_POINTS: "典型痛点与契合检验",
    SECTION_DUE_DILIGENCE: "尽调清单 (高危信号)",
    SECTION_LANDMINES: "数据与集成雷区",
    SECTION_METRICS: "评估验收指标模板",
    SECTION_ROLES: "变革管理角色地图",
    SECTION_PRICING: "计价与扩容参考",
    SECTION_LESSONS: "历史复盘教训库",
}


@dataclass
class ScenarioPlaybook:
    """一个场景的打法手册。

    Attributes:
        scenario: 场景名 (如 "金融反洗钱场景")。
        sections: 七件套 (key → 内容列表)。
        owner: 负责人 (最资深交付团队)。
        version: 版本号。
        deprecated_ts: 折旧时间戳 (None 未折旧)。
        created_ts: 创建时间。
        updated_ts: 最近更新。
    """

    scenario: str
    sections: dict[str, list[str]] = field(default_factory=dict)
    owner: str = ""
    version: int = 1
    deprecated_ts: float | None = None
    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)

    def set_section(self, section: str, items: list[str]) -> None:
        """写入七件套之一 (校验合法 section)。"""
        if section not in SECTIONS:
            raise ValueError(f"invalid section: {section!r}; expected {SECTIONS}")
        self.sections[section] = list(items)
        self.updated_ts = time.time()

    def add_item(self, section: str, item: str) -> None:
        """追加一条 (去重)。"""
        if section not in SECTIONS:
            raise ValueError(f"invalid section: {section!r}; expected {SECTIONS}")
        items = self.sections.setdefault(section, [])
        if item not in items:
            items.append(item)
            self.updated_ts = time.time()

    def completeness(self) -> dict[str, Any]:
        """七件套完整度 (哪些缺失)。"""
        missing = [s for s in SECTIONS if not self.sections.get(s)]
        return {
            "complete": not missing,
            "missing": missing,
            "filled": sum(1 for s in SECTIONS if self.sections.get(s)),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "sections": dict(self.sections),
            "owner": self.owner,
            "version": self.version,
            "deprecated": self.deprecated_ts is not None,
        }


# ── 手册库 + 生命周期 ────────────────────────────────────────────────


class PlaybookLibrary:
    """场景打法手册库: 注册/检索/检修/折旧。"""

    def __init__(self) -> None:
        self.playbooks: dict[str, ScenarioPlaybook] = {}

    def register(self, playbook: ScenarioPlaybook) -> None:
        """注册/更新手册 (同场景覆盖, 版本自增)。"""
        existing = self.playbooks.get(playbook.scenario)
        if existing is not None:
            playbook.version = existing.version + 1
        self.playbooks[playbook.scenario] = playbook

    def get(self, scenario: str) -> ScenarioPlaybook | None:
        """取手册 (折旧的返回 None 或标记)。"""
        playbook = self.playbooks.get(scenario)
        if playbook is None or playbook.deprecated_ts is not None:
            return None
        return playbook

    def list_scenarios(self) -> list[str]:
        """全部场景 (非折旧)。"""
        return sorted(s for s, p in self.playbooks.items() if p.deprecated_ts is None)

    def mandatory_update(
        self,
        scenario: str,
        section: str,
        item: str,
    ) -> ScenarioPlaybook:
        """复盘强制更新 (嵌入流程的硬关卡: 复盘更新是必填产出)。

        Returns:
            更新后的手册。

        Raises:
            KeyError: 场景未注册或已折旧。
        """
        playbook = self.get(scenario)
        if playbook is None:
            raise KeyError(f"unknown or deprecated scenario: {scenario!r}")
        playbook.add_item(section, item)
        return playbook

    def deprecate(self, scenario: str) -> None:
        """折旧手册 (半年检修删除过时的)。"""
        playbook = self.playbooks.get(scenario)
        if playbook is not None:
            playbook.deprecated_ts = time.time()

    def review(
        self,
        *,
        prune_deprecated_older_than_s: float = 60 * 86400,
        now: float | None = None,
    ) -> dict[str, Any]:
        """半年检修: 删过时折旧的, 报告完整度。"""
        now = now or time.time()
        removed: list[str] = []
        for scenario, playbook in list(self.playbooks.items()):
            if (
                playbook.deprecated_ts is not None
                and now - playbook.deprecated_ts > prune_deprecated_older_than_s
            ):
                removed.append(scenario)
                del self.playbooks[scenario]
        incomplete = [
            s
            for s, p in self.playbooks.items()
            if p.deprecated_ts is None and not p.completeness()["complete"]
        ]
        return {
            "removed": removed,
            "incomplete_scenarios": incomplete,
            "active": len(self.list_scenarios()),
        }

    def summary(self) -> dict[str, Any]:
        """库概览。"""
        return {
            "scenarios": self.list_scenarios(),
            "count": len(self.list_scenarios()),
            "total": len(self.playbooks),
        }


__all__ = [
    "PlaybookLibrary",
    "ScenarioPlaybook",
    "SECTION_LANDMINES",
    "SECTION_LESSONS",
    "SECTION_METRICS",
    "SECTION_NAMES",
    "SECTION_PAIN_POINTS",
    "SECTION_PRICING",
    "SECTION_ROLES",
    "SECTIONS",
    "SECTION_DUE_DILIGENCE",
]
