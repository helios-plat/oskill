"""compose_drift_detect — 声明态 vs 运行态漂移 (aegis DESIGN §3.7 config-as-code 对账).

Composition note: pure algorithm, no I/O. git 声明的 compose 与实际运行容器对比出漂移,
喂"干净机器 30 分钟重建"验收。对比字段为可注入参数(默认 ['image']),业务知识不焊死。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

_DEFAULT_COMPARE_FIELDS = ("image",)


class ServiceDrift(BaseModel):
    service: str
    field: str
    declared: Any
    running: Any


class Drift(BaseModel):
    added: list[str]  # 声明有、运行缺(应起未起)
    removed: list[str]  # 运行有、声明无(多出来的)
    changed: list[ServiceDrift]  # 名字都在但对比字段不同
    in_sync: bool


def _normalize_running(running: dict[str, dict] | list[dict]) -> dict[str, dict]:
    if isinstance(running, dict):
        return running
    out: dict[str, dict] = {}
    for c in running:
        name = c.get("name") or c.get("Name") or ""
        if name:
            out[name] = c
    return out


def compose_drift_detect(
    *,
    declared: dict[str, dict],
    running: dict[str, dict] | list[dict],
    compare_fields: list[str] | tuple[str, ...] | None = None,
) -> Drift:
    """对比声明态与运行态,给出漂移。

    Args:
        declared: {service_name: {field: value, ...}} —— git 声明态。
        running: {name: {...}} 或 [{name/Name, ...}] —— 实际运行态(容器)。
        compare_fields: 对两侧都存在的服务需逐一比较的字段(默认 ("image",),可注入)。

    Returns:
        Drift(added / removed / changed / in_sync)。
    """
    fields = tuple(compare_fields) if compare_fields is not None else _DEFAULT_COMPARE_FIELDS
    running_map = _normalize_running(running)

    declared_keys = set(declared)
    running_keys = set(running_map)
    added = sorted(declared_keys - running_keys)
    removed = sorted(running_keys - declared_keys)

    changed: list[ServiceDrift] = []
    for name in sorted(declared_keys & running_keys):
        d = declared[name]
        r = running_map[name]
        for f in fields:
            if d.get(f) != r.get(f):
                changed.append(
                    ServiceDrift(service=name, field=f, declared=d.get(f), running=r.get(f))
                )

    in_sync = not added and not removed and not changed
    return Drift(added=added, removed=removed, changed=changed, in_sync=in_sync)
