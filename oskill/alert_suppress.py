"""alert_suppress — 层级告警抑制 (aegis DESIGN §3.2).

Composition note: pure algorithm, no I/O. 父级(宿主/节点)down 时抑制其子告警,消除
发版/重启告警风暴(风暴的长期后果是训练人忽略告警,比无告警更危险)。视为"下线"的
状态集为可注入参数(默认 down/unreachable/dead/offline),业务知识不焊死。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_DEFAULT_DOWN_STATES = ("down", "unreachable", "dead", "offline")


class SuppressVerdict(BaseModel):
    suppressed: bool
    reason: str | None


def alert_suppress(
    *,
    alert: dict[str, Any],
    parent_states: dict[str, str],
    down_states: list[str] | tuple[str, ...] | None = None,
) -> SuppressVerdict:
    """父级处于下线态时抑制子告警。

    Args:
        alert: 告警 dict,应含 "parent" 键(父级标识,如所在宿主/节点 id);无该键则不抑制。
        parent_states: {parent_id: state} 父级当前状态映射。
        down_states: 视为"下线"的状态集(默认 down/unreachable/dead/offline,可注入覆盖)。

    Returns:
        SuppressVerdict(suppressed, reason)。
    """
    down = set(down_states) if down_states is not None else set(_DEFAULT_DOWN_STATES)
    parent = alert.get("parent")
    if parent is not None:
        state = parent_states.get(parent)
        if state in down:
            return SuppressVerdict(suppressed=True, reason=f"parent {parent!r} is {state!r}")
    return SuppressVerdict(suppressed=False, reason=None)
