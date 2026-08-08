"""oskill.memory_layers — L0-L3 分层记忆蒸馏 (TencentDB Agent Memory 机制 3O 内化)。

对话 → 原子 → 场景 → 人格 的分层蒸馏管线:
  * **L0 Conversation** — 原始对话 (验证/溯源);
  * **L1 Atom** — 事实/偏好/约束/事件, 带**可替代性 score (0-10)** (LLM 注入);
  * **L2 Scenario** — 按项目/场景组织的知识块;
  * **L3 Persona** — 长期画像 (稳定模式/高层认知)。
确定性触发阈值 (源自 TencentDB): pending >= N 强制蒸馏; 未归属原子 >= N
触发场景构建。检索双层: 默认 L2/L3 快速引导, 具体事实时 RRF 回退 L1/L0。

零 veya 反向依赖: 各层 LLM 提炼函数由调用方注入。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

LAYER_L0 = "L0"
LAYER_L1 = "L1"
LAYER_L2 = "L2"
LAYER_L3 = "L3"

ATOM_FACT = "fact"
ATOM_PREFERENCE = "preference"
ATOM_CONSTRAINT = "constraint"
ATOM_EVENT = "event"
ATOM_TYPES = (ATOM_FACT, ATOM_PREFERENCE, ATOM_CONSTRAINT, ATOM_EVENT)


@dataclass
class MemoryEntry:
    """一条原始对话记录 (L0)。"""

    text: str
    ts: float = field(default_factory=time.time)
    session_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class L1Atom:
    """一个原子记忆 (L1): 事实/偏好/约束/事件 + 可替代性 score。"""

    kind: str = ATOM_FACT
    text: str = ""
    source_entry: str = ""  # 溯源 (L0 引用)
    score: float = 5.0  # 可替代性 0-10 (summary 能否替代原文)
    assigned_to: str | None = None  # 归属场景 (L2 id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "source_entry": self.source_entry,
            "score": self.score,
            "assigned_to": self.assigned_to,
        }


@dataclass
class L2Scenario:
    """场景知识块 (L2): 按项目/场景组织。"""

    id: str
    title: str
    content: str = ""  # 场景知识块 (LLM 构建)
    atom_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "atom_ids": list(self.atom_ids),
        }


@dataclass
class L3Persona:
    """长期人格画像 (L3)。"""

    profile: str = ""  # 稳定模式/高层认知
    updated_at: float = field(default_factory=time.time)


# 蒸馏函数注入类型
L1Fn = Callable[[list[MemoryEntry]], list[L1Atom]]
L2Fn = Callable[[list[L1Atom]], list[L2Scenario]]
L3Fn = Callable[[list[L2Scenario]], L3Persona]


class DistillPipeline:
    """L0-L3 分层蒸馏管线 (确定性触发 + LLM 提炼注入)。"""

    def __init__(
        self,
        *,
        l1_threshold: int = 4,  # pending >= N 强制 L1 蒸馏
        l2_threshold: int = 4,  # 未归属原子 >= N 触发 L2 构建
        score_threshold: float = 3.0,  # 低于该 score 的原子保留原文引用
    ) -> None:
        self.l1_threshold = l1_threshold
        self.l2_threshold = l2_threshold
        self.score_threshold = score_threshold
        self.l0: list[MemoryEntry] = []
        self.atoms: list[L1Atom] = []
        self.scenarios: dict[str, L2Scenario] = {}
        self.persona = L3Persona()
        self.pending_l1: list[MemoryEntry] = []  # 待蒸馏 (未处理)

    # ── 记录 (L0) ─────────────────────────────────────────────────────

    def record(
        self, text: str, *, session_id: str = "", meta: dict[str, Any] | None = None
    ) -> None:
        """记录一条对话 (L0) 并进入待蒸馏队列。"""
        entry = MemoryEntry(text=text, session_id=session_id, meta=meta or {})
        self.l0.append(entry)
        self.pending_l1.append(entry)

    # ── 蒸馏触发判断 (确定性) ─────────────────────────────────────────

    def should_distill(self) -> bool:
        """pending 达到阈值 → 强制 L1 蒸馏。"""
        return len(self.pending_l1) >= self.l1_threshold

    def should_build_scenario(self) -> bool:
        """未归属原子达到阈值 → 触发 L2。"""
        return len([a for a in self.atoms if a.assigned_to is None]) >= self.l2_threshold

    # ── 蒸馏执行 (LLM 注入) ───────────────────────────────────────────

    def distill_l1(self, l1_fn: L1Fn) -> list[L1Atom]:
        """L1 原子提取 (仅处理 pending 队列)。"""
        if not self.pending_l1:
            return []
        batch = list(self.pending_l1)
        self.pending_l1.clear()
        extracted = l1_fn(batch)
        for atom in extracted:
            atom.source_entry = atom.source_entry or batch[0].text[:60]
            self.atoms.append(atom)
        return extracted

    def build_scenarios(self, l2_fn: L2Fn) -> list[L2Scenario]:
        """L2 场景构建 (仅处理未归属原子)。"""
        unassigned = [a for a in self.atoms if a.assigned_to is None]
        if not unassigned:
            return []
        scenarios = l2_fn(unassigned)
        for scenario in scenarios:
            self.scenarios[scenario.id] = scenario
            for atom_id in scenario.atom_ids:
                for atom in self.atoms:
                    if atom.text == atom_id or id(atom) == id(atom_id):
                        atom.assigned_to = scenario.id
        return scenarios

    def stabilize_persona(self, l3_fn: L3Fn) -> L3Persona:
        """L3 人格稳定 (基于全部场景)。"""
        self.persona = l3_fn(list(self.scenarios.values()))
        return self.persona

    # ── 检索双层 ──────────────────────────────────────────────────────

    def recall_quick(self) -> str:
        """快速引导: L2 场景 + L3 人格 (不查 L1)。"""
        parts = []
        if self.persona.profile:
            parts.append(f"[Persona] {self.persona.profile}")
        for scenario in self.scenarios.values():
            parts.append(f"[{scenario.id}] {scenario.title}: {scenario.content[:200]}")
        return "\n".join(parts)

    def recall_atoms(self, *, min_score: float | None = None) -> list[L1Atom]:
        """具体事实回退: 全部 L1 原子 (可按 score 过滤)。"""
        threshold = min_score if min_score is not None else self.score_threshold
        return [a for a in self.atoms if a.score >= threshold]

    def summary(self) -> dict[str, Any]:
        """管线概览。"""
        return {
            "l0": len(self.l0),
            "pending_l1": len(self.pending_l1),
            "atoms": len(self.atoms),
            "scenarios": len(self.scenarios),
            "persona": bool(self.persona.profile),
        }
