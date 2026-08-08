"""oskill.memory_assets — 记忆资产注册 + ACL + loadout (TencentDB Agent Memory 机制 3O 内化)。

记忆资产统一注册 (Chat Memory / Skill / Wiki / CodeGraph 同形), 带
**所有权 / 可见性 / ACL**; 按 Agent 装配 loadout (Fixed Binding):
  * visibility — private (owner 专属) / team (成员可见) / restricted (ACL);
  * check_access — 主体验证 (owner/成员/ACL 匹配);
  * Loadout — Agent → 资产列表 + 优先级, assemble_loadout 按 ACL 过滤装配。

零 veya 反向依赖: 纯数据结构 + 权限矩阵。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ASSET_CHAT_MEMORY = "chat_memory"
ASSET_SKILL = "skill"
ASSET_WIKI = "wiki"
ASSET_CODEGRAPH = "codegraph"
ASSET_TYPES = (ASSET_CHAT_MEMORY, ASSET_SKILL, ASSET_WIKI, ASSET_CODEGRAPH)

VISIBILITY_PRIVATE = "private"
VISIBILITY_TEAM = "team"
VISIBILITY_RESTRICTED = "restricted"
VISIBILITIES = (VISIBILITY_PRIVATE, VISIBILITY_TEAM, VISIBILITY_RESTRICTED)


@dataclass
class ACL:
    """restricted 资产的授权 (User/Role/Agent)。"""

    users: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)

    def allows(self, principal: Principal) -> bool:
        """主体是否被授权。"""
        return (
            principal.user in self.users
            or bool(set(principal.roles) & set(self.roles))
            or principal.agent in self.agents
        )


@dataclass(frozen=True)
class Principal:
    """访问主体 (User/Role/Agent 三要素)。"""

    user: str
    roles: list[str] = field(default_factory=list)
    agent: str = ""


@dataclass
class MemoryAsset:
    """一个记忆资产。

    Attributes:
        id: 资产 id。
        asset_type: chat_memory / skill / wiki / codegraph。
        owner: 所有者 (Owner 自动有管理权限)。
        visibility: private / team / restricted。
        title: 标题。
        content: 内容 (按类型解释)。
        acl: restricted 时的授权。
        version: 版本号 (更新自增)。
    """

    id: str
    asset_type: str = ASSET_CHAT_MEMORY
    owner: str = ""
    visibility: str = VISIBILITY_TEAM
    title: str = ""
    content: str = ""
    acl: ACL = field(default_factory=ACL)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.asset_type,
            "owner": self.owner,
            "visibility": self.visibility,
            "title": self.title,
            "content": self.content,
            "version": self.version,
            "acl": {"users": self.acl.users, "roles": self.acl.roles, "agents": self.acl.agents},
        }


class AssetRegistry:
    """记忆资产注册表: 注册 → 访问检查 → loadout 装配。"""

    def __init__(self, *, team_members: list[str] | None = None) -> None:
        self.assets: dict[str, MemoryAsset] = {}
        self.team_members = list(team_members or [])

    # ── 注册 ──────────────────────────────────────────────────────────

    def register(self, asset: MemoryAsset) -> None:
        """注册/更新资产 (同 id 覆盖, 版本自增)。"""
        existing = self.assets.get(asset.id)
        if existing is not None:
            asset.version = existing.version + 1
        self.assets[asset.id] = asset

    def unregister(self, asset_id: str) -> None:
        """注销资产。"""
        self.assets.pop(asset_id, None)

    # ── 访问控制 ──────────────────────────────────────────────────────

    def check_access(self, asset: MemoryAsset, principal: Principal) -> bool:
        """资产可见性检查: private/team/restricted。

        Args:
            asset: 资产。
            principal: 访问主体。

        Returns:
            True 表示可访问。
        """
        if asset.visibility == VISIBILITY_PRIVATE:
            return principal.user == asset.owner
        if asset.visibility == VISIBILITY_TEAM:
            return principal.user in self.team_members or principal.user == asset.owner
        if asset.visibility == VISIBILITY_RESTRICTED:
            return asset.acl.allows(principal)
        return False

    def find_accessible(self, principal: Principal) -> list[MemoryAsset]:
        """该主体可见的全部资产。"""
        return [a for a in self.assets.values() if self.check_access(a, principal)]

    # ── loadout 装配 (Fixed Binding) ──────────────────────────────────

    def assemble_loadout(
        self,
        agent_id: str,
        principal: Principal,
        *,
        bindings: dict[str, list[str]] | None = None,
        priorities: dict[str, float] | None = None,
        top_k: int | None = None,
    ) -> list[MemoryAsset]:
        """为 Agent 装配记忆 loadout。

        Fixed Binding (bindings: agent → 资产 id 列表) 先确定候选, 再按
        ACL/可见性过滤; 可按优先级排序后截断。

        Args:
            agent_id: 目标 Agent。
            principal: 访问主体。
            bindings: agent → 资产 id 绑定; None 用全部资产。
            priorities: 资产 id → 优先级 (高在前)。
            top_k: 截断数量。

        Returns:
            装配后的资产列表 (按优先级降序)。
        """
        candidates: list[str] = bindings.get(agent_id) if bindings else list(self.assets)
        if candidates is None:
            candidates = list(self.assets)
        accessible = [
            asset
            for asset in self.assets.values()
            if asset.id in candidates and self.check_access(asset, principal)
        ]
        accessible.sort(key=lambda a: -priorities.get(a.id, 0.0) if priorities else 0.0)
        if top_k is not None:
            accessible = accessible[:top_k]
        return accessible

    def summary(self) -> dict[str, int]:
        """注册表概览。"""
        return {
            "assets": len(self.assets),
            "private": sum(1 for a in self.assets.values() if a.visibility == VISIBILITY_PRIVATE),
            "team": sum(1 for a in self.assets.values() if a.visibility == VISIBILITY_TEAM),
            "restricted": sum(
                1 for a in self.assets.values() if a.visibility == VISIBILITY_RESTRICTED
            ),
        }
