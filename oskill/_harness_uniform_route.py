"""oskill.harness_uniform_route — 运行架统一路由.

把异构事件（来源/格式各异）归一化后按路由表（注入 handlers）分发：
- 事件归一化：统一 {kind, source, payload, ts}
- 路由匹配：精确 kind → 前缀 → 通配符
- fallback 兜底

stateless。

Example:
    >>> r = await harness_uniform_route({"type": "task.done", "data": {"id": 1}},
    ...                                 handlers={"task.*": handler})
    >>> r["handled"]
    True
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError

RouteHandler = Callable[[dict[str, Any]], Awaitable[Any] | Any]


@runtime_checkable
class RouteTable(Protocol):
    """路由表协议（注入面）。"""

    async def handle(self, event: dict[str, Any]) -> Any: ...


async def harness_uniform_route(
    event: dict[str, Any],
    *,
    handlers: dict[str, RouteHandler] | None = None,
    router: RouteTable | None = None,
    fallback: RouteHandler | None = None,
    source: str = "unknown",
) -> dict[str, Any]:
    """统一路由事件。

    Args:
        event: 原始事件（含 type/kind/topic 任一字段 + 载荷）。
        handlers: 路由表 {pattern: handler}；pattern 支持精确名 / "a.*" 前缀 / "*"。
        router: 路由器（注入，优先于 handlers）。
        fallback: 无命中时的兜底处理器。
        source: 事件来源标注。

    Returns:
        {"status": "ok", "handled": bool, "route": str|None, "kind": str,
         "normalized": dict, "result": Any}

    Raises:
        OskillError: event 为空 / 无任何路由能力。
    """
    if not event:
        raise OskillError("harness_uniform_route: event must not be empty")
    if router is None and not handlers:
        raise OskillError("harness_uniform_route: need handlers or router to dispatch")

    kind = str(event.get("kind") or event.get("type") or event.get("topic") or "event")
    payload = event.get("payload") or event.get("data") or event
    normalized = {
        "kind": kind,
        "source": source,
        "payload": payload,
        "ts": time.time(),
    }

    if router is not None:
        try:
            result = await router.handle(normalized)
        except Exception as exc:
            raise OskillError(f"harness_uniform_route: router failed: {exc}") from exc
        return {
            "status": "ok",
            "handled": True,
            "route": "router",
            "kind": kind,
            "normalized": normalized,
            "result": result,
        }

    route = _match_route(kind, list(handlers or {}))
    if route is None and fallback is not None:
        route = "__fallback__"
    handler = (handlers or {}).get(route) if route and route != "__fallback__" else None
    if route == "__fallback__":
        handler = fallback
    if handler is None:
        return {
            "status": "ok",
            "handled": False,
            "route": None,
            "kind": kind,
            "normalized": normalized,
            "result": None,
        }

    try:
        result = handler(normalized)
        if hasattr(result, "__await__") or isinstance(result, Awaitable):  # type: ignore[arg-type]
            result = await result  # type: ignore[misc]
    except Exception as exc:
        raise OskillError(f"harness_uniform_route: handler {route!r} failed: {exc}") from exc

    return {
        "status": "ok",
        "handled": True,
        "route": route,
        "kind": kind,
        "normalized": normalized,
        "result": result,
    }


def _match_route(kind: str, patterns: list[str]) -> str | None:
    if kind in patterns:
        return kind
    # 最长前缀匹配
    prefix_hits = sorted(
        (p for p in patterns if p.endswith(".*") and kind.startswith(p[:-1])),
        key=len,
        reverse=True,
    )
    if prefix_hits:
        return prefix_hits[0]
    if "*" in patterns:
        return "*"
    return None
