"""oskill.daemon_runtime — 守护进程运行时 (cloudflare computerd 机制 3O 内化)。

computerd daemon 的机制层 (FUSE 真实挂载属 OS 层, 此处做生命周期 + 同步):
  * **DaemonLifecycle** — 守护进程生命周期: start/stop/health/ping/优雅关闭;
  * **DirWatcher** — 目录变更监听 (文件哈希指纹 → 变更集), 支撑
    push (变更 → 权威存储) / pull (权威 → 工作区) 同步语义;
  * **SyncSession** — push→exec→pull 括号 (与 veya.execution.SyncBracket 同
    哲学, 此处面向 daemon 常驻场景)。
零 veya 反向依赖: 进程管理注入 (threading/subprocess); 纯状态机 + 哈希。
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WorkerFn = Callable[[], None]
"""daemon worker: 后台循环 (注入, 如 computerd 同步循环)。"""


@dataclass
class DaemonState:
    """daemon 状态。"""

    status: str = "stopped"  # stopped / starting / running / stopping / crashed
    started_at: float | None = None
    last_heartbeat: float | None = None
    restarts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "restarts": self.restarts,
        }


class DaemonLifecycle:
    """守护进程生命周期管理 (start/stop/health/重启)。"""

    def __init__(self, name: str, worker: WorkerFn, *, heartbeat_interval_s: float = 30.0) -> None:
        self.name = name
        self.worker = worker
        self.heartbeat_interval_s = heartbeat_interval_s
        self.state = DaemonState()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> DaemonState:
        """启动 daemon (后台线程, 首次启动)。"""
        if self.state.status in ("running", "starting"):
            return self.state
        self._stop.clear()
        self.state.status = "starting"
        self.state.started_at = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.state.status = "running"
        return self.state

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                self.worker()
                self.state.last_heartbeat = time.time()
                self._stop.wait(self.heartbeat_interval_s)
        except Exception:  # noqa: BLE001
            self.state.status = "crashed"
            self.state.restarts += 1

    def stop(self) -> DaemonState:
        """优雅停止。"""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self.state.status = "stopped"
        return self.state

    def health(self) -> dict[str, Any]:
        """健康检查: 运行中 + 心跳新鲜。"""
        fresh = (
            self.state.last_heartbeat is not None
            and time.time() - self.state.last_heartbeat <= self.heartbeat_interval_s * 2
        )
        return {"ok": self.state.status == "running" and fresh, "state": self.state.to_dict()}

    def restart(self) -> DaemonState:
        """重启 (stop → start, 计数)。"""
        self.stop()
        self.state.restarts += 1
        return self.start()


def _file_fingerprint(root: Path) -> dict[str, str]:
    """目录文件指纹 (path → sha1 前缀)。"""
    fingerprint: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            try:
                digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
                fingerprint[str(path.relative_to(root))] = digest
            except OSError:
                continue
    return fingerprint


class DirWatcher:
    """目录变更监听 (哈希指纹 diff → 变更集)。"""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._baseline: dict[str, str] = {}

    def snapshot(self) -> dict[str, str]:
        """记录当前指纹基线。"""
        self._baseline = _file_fingerprint(self.root)
        return self._baseline

    def changes_since(self, baseline: dict[str, str] | None = None) -> dict[str, Any]:
        """相对基线的变更集 (added/changed/removed)。"""
        baseline = baseline or self._baseline
        current = _file_fingerprint(self.root)
        added = [p for p in current if p not in baseline]
        changed = [p for p in current if p in baseline and baseline[p] != current[p]]
        removed = [p for p in baseline if p not in current]
        return {
            "added": added,
            "changed": changed,
            "removed": removed,
            "total": len(added) + len(changed) + len(removed),
        }

    def watch_once(self) -> dict[str, Any]:
        """单次监听: 记录基线并返回首次变更集 (供轮询循环)。"""
        changes = self.changes_since()
        self.snapshot()
        return changes


@dataclass
class SyncSession:
    """push→exec→pull 同步括号 (daemon 常驻语义)。"""

    watcher: DirWatcher
    apply_fn: Callable[[str, str], None]
    """变更应用: (相对路径, 变更类型) → 应用 (注入: 写权威/工作区)。"""

    def push(self) -> dict[str, Any]:
        """push: 工作区变更 → 应用 (同步到权威)。"""
        changes = self.watcher.changes_since()
        for kind in ("added", "changed"):
            for rel in changes[kind]:
                self.apply_fn(rel, kind)
        self.watcher.snapshot()  # 应用后更新基线
        return changes

    def pull(self, updates: dict[str, Any]) -> int:
        """pull: 外部更新 → 应用 (同步到工作区), 返回应用数。"""
        applied = 0
        for rel in updates.get("changed", []):
            self.apply_fn(rel, "changed")
            applied += 1
        return applied


__all__ = ["DaemonLifecycle", "DaemonState", "DirWatcher", "SyncSession"]
