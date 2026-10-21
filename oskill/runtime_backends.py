"""oskill.runtime_backends — 执行后端能力注册 (cloudflare/computer runtime 机制补全)。

把 execution.py 的单入口路由升级为**能力驱动**的注册/选择:
  * **RuntimeBackend** — 声明 (id/kind: shell|module|container/capabilities);
  * **BackendRegistry** — 注册/能力查询/按需求选择 (Discovery-First);
  * **BackendExecutor** — 懒连接 (首次使用才初始化) + 按 id 路由执行;
  * 与 veya.execution 组合: 能力选择 → runtime_exec。
零 veya 反向依赖: 执行函数注入; 纯注册/选择。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

KIND_SHELL = "shell"
KIND_MODULE = "module"
KIND_CONTAINER = "container"
KINDS = (KIND_SHELL, KIND_MODULE, KIND_CONTAINER)

CAP_STRUCTURED_INPUT = "structured_input"
CAP_STRUCTURED_OUTPUT = "structured_output"
CAP_ISOLATED = "isolated"
CAP_NETWORK = "network"
CAP_FS_SYNC = "fs_sync"  # push/pull 同步
CAP_FAST_PATH = "fast_path"  # 零往返
CAPS = (
    CAP_STRUCTURED_INPUT,
    CAP_STRUCTURED_OUTPUT,
    CAP_ISOLATED,
    CAP_NETWORK,
    CAP_FS_SYNC,
    CAP_FAST_PATH,
)

ExecFn = Callable[[str, dict[str, Any]], dict[str, Any]]
"""执行函数: (source, options) → 结果 dict (注入)。"""


@dataclass
class RuntimeBackend:
    """一个执行后端声明。

    Attributes:
        id: 后端 id (稳定)。
        kind: shell/module/container。
        capabilities: 能力集合。
        init: 懒初始化函数 (None 表示无状态无需初始化)。
        exec: 执行函数。
    """

    id: str
    kind: str = KIND_SHELL
    capabilities: list[str] = field(default_factory=list)
    init: Callable[[], Any] | None = None
    exec: ExecFn | None = None
    _initialized: bool = False

    def ensure_init(self) -> None:
        """懒连接: 首次使用才初始化。"""
        if not self._initialized and self.init is not None:
            self.init()
            self._initialized = True


class BackendRegistry:
    """后端注册表: 注册/能力查询/按需求选择。"""

    def __init__(self) -> None:
        self.backends: dict[str, RuntimeBackend] = {}

    def register(self, backend: RuntimeBackend) -> None:
        self.backends[backend.id] = backend

    def get(self, backend_id: str) -> RuntimeBackend:
        if backend_id not in self.backends:
            raise ValueError(f"unknown backend: {backend_id!r}; available: {self.list_backends()}")
        return self.backends[backend_id]

    def list_backends(self) -> list[str]:
        return sorted(self.backends)

    def find_by_capability(self, cap: str) -> list[str]:
        return sorted(b.id for b in self.backends.values() if cap in b.capabilities)

    def select(
        self,
        *,
        kind: str | None = None,
        require: list[str] | None = None,
        prefer: list[str] | None = None,
    ) -> list[str]:
        """按需求选择后端 (能力过滤 + 偏好排序)。

        Args:
            kind: 按类型过滤。
            require: 必须满足的能力。
            prefer: 优先排序的能力 (先满足的排前)。

        Returns:
            后端 id 列表 (分数降序)。
        """
        require = require or []
        candidates = []
        for backend in self.backends.values():
            if kind is not None and backend.kind != kind:
                continue
            caps = set(backend.capabilities)
            if not all(c in caps for c in require):
                continue
            score = sum(1 for p in prefer or [] if p in caps)
            candidates.append((score, backend.id))
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return [bid for _, bid in candidates]

    def capabilities(self) -> dict[str, Any]:
        """capabilities 聚合视图 (Discovery-First)。"""
        return {
            "backends": {
                bid: {"kind": b.kind, "capabilities": b.capabilities}
                for bid, b in self.backends.items()
            },
            "counts": {k: len(self.find_by_capability(k)) for k in CAPS},
        }


class BackendExecutor:
    """后端执行器: 选后端 → 懒连接 → 执行。"""

    def __init__(self, registry: BackendRegistry | None = None) -> None:
        self.registry = registry or BackendRegistry()

    def execute(
        self,
        source: str,
        *,
        backend_id: str | None = None,
        require: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """按后端执行 (指定 id 或按能力选择)。"""
        if backend_id is not None:
            backend = self.registry.get(backend_id)
        else:
            selected = self.registry.select(require=require, prefer=["fast_path"])
            if not selected:
                return {
                    "ok": False,
                    "error": "no backend satisfies requirements",
                    "required": require or [],
                }
            backend = self.registry.get(selected[0])
        backend.ensure_init()
        if backend.exec is None:
            return {"ok": False, "error": f"backend {backend.id} has no executor"}
        return backend.exec(source, options or {})


# ── 默认装配 (三档后端: 快路径/结构化/隔离) ─────────────────────────


def _default_registry() -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(
        RuntimeBackend(
            id="fast-shell",
            kind=KIND_SHELL,
            capabilities=[CAP_FAST_PATH, CAP_NETWORK],
        )
    )
    registry.register(
        RuntimeBackend(
            id="structured-module",
            kind=KIND_MODULE,
            capabilities=[CAP_STRUCTURED_INPUT, CAP_STRUCTURED_OUTPUT, CAP_ISOLATED],
        )
    )
    registry.register(
        RuntimeBackend(
            id="isolated-container",
            kind=KIND_CONTAINER,
            capabilities=[CAP_ISOLATED, CAP_NETWORK, CAP_FS_SYNC],
        )
    )
    return registry


__all__ = [
    "BackendExecutor",
    "BackendRegistry",
    "CAPS",
    "KINDS",
    "KIND_CONTAINER",
    "KIND_MODULE",
    "KIND_SHELL",
    "RuntimeBackend",
    "_default_registry",
]
