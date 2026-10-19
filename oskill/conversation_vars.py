"""oskill.conversation_vars — 会话变量生命周期 (Dify conversation 变量 3O 内化)。

会话级变量 (跨轮上下文): 读写/生命周期/版本:
  * **ConversationVars** — 会话变量存储 (读写/过期/版本);
  * 变量作用域: session (本会话) / project (跨会话共享);
  * 过期策略: ttl 或显式清除。
零 veya 反向依赖: 纯数据结构。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

SCOPE_SESSION = "session"
SCOPE_PROJECT = "project"


@dataclass
class VarEntry:
    """一个会话变量。"""

    key: str
    value: Any
    scope: str = SCOPE_SESSION
    version: int = 1
    expires_at: float | None = None
    updated_at: float = field(default_factory=time.time)

    def expired(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or time.time()) > self.expires_at


class ConversationVars:
    """会话变量存储: 跨轮上下文管理。"""

    def __init__(self) -> None:
        self.vars: dict[str, VarEntry] = {}

    def set(
        self, key: str, value: Any, *, scope: str = SCOPE_SESSION, ttl_s: float | None = None
    ) -> VarEntry:
        """写入变量 (同键覆盖, 版本自增, 可选 TTL)。"""
        entry = self.vars.get(key)
        if entry is None:
            entry = VarEntry(key=key, value=value, scope=scope)
        else:
            entry.value = value
            entry.scope = scope
            entry.version += 1
            entry.updated_at = time.time()
        entry.expires_at = time.time() + ttl_s if ttl_s else None
        self.vars[key] = entry
        return entry

    def get(self, key: str, *, default: Any = None) -> Any:
        """读取变量 (过期返回默认并清除)。"""
        entry = self.vars.get(key)
        if entry is None:
            return default
        if entry.expired():
            del self.vars[key]
            return default
        return entry.value

    def get_entry(self, key: str) -> VarEntry | None:
        entry = self.vars.get(key)
        if entry is not None and entry.expired():
            del self.vars[key]
            return None
        return entry

    def clear(self, key: str) -> None:
        self.vars.pop(key, None)

    def snapshot(self, *, scope: str | None = None) -> dict[str, Any]:
        """当前有效变量快照 (供上下文注入)。"""
        now = time.time()
        return {
            key: entry.value
            for key, entry in self.vars.items()
            if (scope is None or entry.scope == scope) and not entry.expired(now)
        }

    def touch(self, key: str, *, ttl_s: float | None = None) -> None:
        """刷新过期时间 (会话续期)。"""
        entry = self.vars.get(key)
        if entry is not None:
            entry.expires_at = time.time() + ttl_s if ttl_s else None

    def summary(self) -> dict[str, Any]:
        return {"vars": list(self.vars), "count": len(self.vars)}


__all__ = ["ConversationVars", "SCOPE_PROJECT", "SCOPE_SESSION", "VarEntry"]
