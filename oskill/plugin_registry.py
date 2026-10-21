"""oskill.plugin_registry — 插件市场机制 (Dify 机制 3O 内化)。

插件声明 + 依赖解析 + 启用禁用 (与 veya skill_hub/agent_wiring 互补):
  * **PluginDecl** — 插件声明 (id/version/依赖/能力点);
  * **PluginRegistry** — 注册/查找/依赖解析 (拓扑排序, 循环拒绝)/启用禁用;
  * **resolve_dependencies** — 按依赖图求安装顺序。

零 veya 反向依赖: 纯数据结构 + 拓扑排序。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

STATE_DISCOVERED = "discovered"
STATE_ENABLED = "enabled"
STATE_DISABLED = "disabled"
STATES = (STATE_DISCOVERED, STATE_ENABLED, STATE_DISABLED)


@dataclass
class PluginDecl:
    """插件声明。

    Attributes:
        id: 插件唯一 id。
        version: 版本号。
        dependencies: 依赖插件 id 列表。
        capabilities: 提供的能力点 (工具/模型/流程等)。
        state: discovered/enabled/disabled。
    """

    id: str
    version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    state: str = STATE_DISCOVERED

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "dependencies": list(self.dependencies),
            "capabilities": list(self.capabilities),
            "state": self.state,
        }


class PluginRegistry:
    """插件注册表: 注册/查找/依赖解析/启用禁用。"""

    def __init__(self) -> None:
        self.plugins: dict[str, PluginDecl] = {}

    def register(self, plugin: PluginDecl) -> None:
        """注册插件 (幂等覆盖)。"""
        self.plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> PluginDecl | None:
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> list[str]:
        return sorted(self.plugins)

    def list_by_capability(self, capability: str) -> list[str]:
        """按能力点查找插件。"""
        return sorted(p.id for p in self.plugins.values() if capability in p.capabilities)

    def enable(self, plugin_id: str) -> None:
        """启用插件 (自动启用依赖)。"""
        for dep in self._dependency_chain(plugin_id):
            self.plugins[dep].state = STATE_ENABLED

    def disable(self, plugin_id: str) -> None:
        """禁用插件 (依赖它的插件也禁用)。"""
        for dependent in self._dependents(plugin_id):
            self.plugins[dependent].state = STATE_DISABLED

    def resolve_dependencies(self, plugin_id: str) -> list[str]:
        """求插件及其依赖的安装顺序 (拓扑序, 依赖在前)。

        Args:
            plugin_id: 目标插件。

        Returns:
            插件 id 列表 (依赖在前, 含自身)。

        Raises:
            KeyError: 依赖缺失。
            ValueError: 依赖循环。
        """
        order = self._dependency_chain(plugin_id)
        return order

    # ── 内部 ──────────────────────────────────────────────────────────

    def _dependency_chain(self, plugin_id: str) -> list[str]:
        """BFS 收集依赖链 + 循环检测。"""
        if plugin_id not in self.plugins:
            raise KeyError(f"unknown plugin: {plugin_id!r}")
        chain: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def collect(current: str) -> None:
            if current in visiting:
                raise ValueError(f"dependency cycle involving {current}")
            if current in visited:
                return
            visiting.add(current)
            for dep in self.plugins[current].dependencies:
                if dep not in self.plugins:
                    raise KeyError(f"missing dependency: {dep!r} (needed by {current!r})")
                collect(dep)
            visiting.discard(current)
            visited.add(current)
            chain.append(current)

        collect(plugin_id)
        return chain

    def _dependents(self, plugin_id: str) -> list[str]:
        """直接/间接依赖该插件的插件 (含自身)。"""
        result: list[str] = []
        for pid in self.plugins:
            try:
                chain = self._dependency_chain(pid)
            except (KeyError, ValueError):
                continue
            if plugin_id in chain:
                result.append(pid)
        return result

    def summary(self) -> dict[str, Any]:
        """注册表概览。"""
        return {
            "total": len(self.plugins),
            "enabled": sum(1 for p in self.plugins.values() if p.state == STATE_ENABLED),
            "disabled": sum(1 for p in self.plugins.values() if p.state == STATE_DISABLED),
        }


__all__ = ["PluginDecl", "PluginRegistry", "STATE_DISABLED", "STATE_DISCOVERED", "STATE_ENABLED"]
