"""oskill.agent_context_pool — 多 Agent 上下文共享/隔离 (ai-agent-book 第10章 3O 内化)。

机制: 上下文池, 每项带可见性 (shared / isolated / derived), 按 agent 角色
投影可见上下文:
  * shared — 所有 agent 可见 (共享事实/目标/约定);
  * isolated — 仅写入者可见 (私有工作记忆);
  * derived — 由调用方注入的派生视图 (如汇总/脱敏)。
确定性规则保证: isolated 不会泄漏给其他 agent, shared 幂等合并,
projected() 返回某 agent 的完整可见快照 (供上下文窗口组装)。

零 veya 反向依赖: 纯数据结构。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

VISIBILITY_SHARED = "shared"
VISIBILITY_ISOLATED = "isolated"
VISIBILITY_DERIVED = "derived"

_VISIBILITIES = (VISIBILITY_SHARED, VISIBILITY_ISOLATED, VISIBILITY_DERIVED)


@dataclass
class ContextItem:
    """一条上下文项。

    Attributes:
        key: 键 (同 agent 内唯一)。
        value: 值 (任意可序列化)。
        visibility: shared / isolated / derived。
        owner: 写入者 agent id (isolated 必填)。
        version: 版本号 (更新自增)。
        updated_at: 更新时间。
    """

    key: str
    value: Any
    visibility: str = VISIBILITY_SHARED
    owner: str | None = None
    version: int = 1
    updated_at: float = field(default_factory=time.time)


class ContextPool:
    """多 Agent 上下文池: 按可见性投影, 防止 isolated 泄漏。"""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], ContextItem] = {}  # (owner, key) → item

    # ── 写入 ──────────────────────────────────────────────────────────

    def set(
        self,
        owner: str,
        key: str,
        value: Any,
        *,
        visibility: str = VISIBILITY_SHARED,
    ) -> ContextItem:
        """写入/更新一条上下文 (幂等覆盖, 版本自增)。

        Args:
            owner: 写入者 agent id。
            key: 上下文键。
            value: 值。
            visibility: shared / isolated / derived。

        Returns:
            ContextItem。

        Raises:
            ValueError: 非法 visibility; isolated 未给 owner。
        """
        if visibility not in _VISIBILITIES:
            raise ValueError(f"invalid visibility: {visibility!r}; expected {_VISIBILITIES}")
        entry = self._items.get((owner, key))
        if entry is None:
            entry = ContextItem(key=key, value=value, visibility=visibility, owner=owner)
        else:
            entry.value = value
            entry.visibility = visibility
            entry.version += 1
            entry.updated_at = time.time()
        self._items[(owner, key)] = entry
        return entry

    def get(self, owner: str, key: str) -> ContextItem | None:
        """按 (owner, key) 取条目。"""
        return self._items.get((owner, key))

    # ── 投影 ──────────────────────────────────────────────────────────

    def projected(self, agent_id: str) -> dict[str, Any]:
        """返回某 agent 的完整可见上下文快照 (键 → 值)。

        规则:
          * shared — 全部共享项可见;
          * isolated — 仅 owner == agent_id 的项可见;
          * derived — 全部派生项可见 (值即注入视图)。
        同名键冲突时: agent 自己的 isolated 优先于 shared (私有覆盖共享)。

        Args:
            agent_id: 请求方 agent id。

        Returns:
            可见上下文 {key: value}。
        """
        view: dict[str, Any] = {}
        # 第一遍: shared + derived
        for (owner, key), item in self._items.items():
            if item.visibility in (VISIBILITY_SHARED, VISIBILITY_DERIVED):
                view[key] = item.value
        # 第二遍: 自己的 isolated 覆盖
        for (owner, key), item in self._items.items():
            if item.visibility == VISIBILITY_ISOLATED and owner == agent_id:
                view[key] = item.value
        return view

    def shared_view(self) -> dict[str, Any]:
        """仅共享+派生项 (不属任何 agent 的视图, 用于汇总/审计)。"""
        return {
            key: item.value
            for (owner, key), item in self._items.items()
            if item.visibility in (VISIBILITY_SHARED, VISIBILITY_DERIVED)
        }

    def isolation_check(self, agent_id: str, other_agent_id: str) -> list[str]:
        """隔离守卫: 返回 agent_id 从 other_agent_id 读到的 isolated 键 (应为空)。

        Args:
            agent_id: 请求方。
            other_agent_id: 另一方 (其 isolated 不应泄漏给 agent_id)。

        Returns:
            泄漏的 isolated 键列表 (正确实现下恒为空)。
        """
        leaked = [
            key
            for (owner, key), item in self._items.items()
            if item.visibility == VISIBILITY_ISOLATED
            and owner == other_agent_id
            and key in self.projected(agent_id)
        ]
        return leaked

    def summary(self) -> dict[str, int]:
        """池概览。"""
        return {
            "shared": sum(1 for i in self._items.values() if i.visibility == VISIBILITY_SHARED),
            "isolated": sum(1 for i in self._items.values() if i.visibility == VISIBILITY_ISOLATED),
            "derived": sum(1 for i in self._items.values() if i.visibility == VISIBILITY_DERIVED),
        }
