"""oskill.recurring_scheduler — Cindy-style automation scheduler.

Cron-based and interval-based recurring task execution with phase lifecycle
tracking (pending → running → completed/failed), pre-run hooks, and post-run
status reporting.  "Recurring work schedules itself, runs itself, reports back."

3O element: ``oskill.recurring_scheduler`` (``RecurringScheduler`` class).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class Schedule:
    id: str
    name: str
    prompt: str = ""
    cron_expr: str = ""  # "*/5 * * * *" or ""
    interval_ms: int = 0  # 3600000 = 1h
    enabled: bool = True
    phase: str = "pending"  # pending|running|completed|failed
    last_run_at: float = 0.0
    last_status: str = ""
    run_count: int = 0
    max_runs: int = 0
    template_id: str = ""


class RecurringScheduler:
    """Cron + interval scheduler with phase lifecycle."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / ".veya" / "schedules"
        self._base.mkdir(parents=True, exist_ok=True)
        self._schedules: dict[str, Schedule] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._runner: Callable | None = None
        self._hook: Callable | None = None
        self._load()

    # -- CRUD ---------------------------------------------------------------
    def create(self, id_: str, name: str, prompt: str = "", cron: str = "", interval_ms: int = 0, template_id: str = "", max_runs: int = 0) -> Schedule:
        s = Schedule(id=id_, name=name, prompt=prompt, cron_expr=cron, interval_ms=interval_ms, template_id=template_id, max_runs=max_runs)
        self._schedules[id_] = s
        self._save()
        return s

    def update(self, id_: str, **fields: Any) -> Schedule | None:
        s = self._schedules.get(id_)
        if s is None:
            return None
        for k, v in fields.items():
            if hasattr(s, k):
                setattr(s, k, v)
        self._save()
        return s

    def delete(self, id_: str) -> bool:
        self.stop(id_)
        if id_ in self._schedules:
            del self._schedules[id_]
            self._save()
            return True
        return False

    def get(self, id_: str) -> Schedule | None:
        return self._schedules.get(id_)

    def list_all(self) -> list[Schedule]:
        return list(self._schedules.values())

    # -- lifecycle ----------------------------------------------------------
    def set_runner(self, runner: Callable) -> None:
        """Set the async callable that executes a schedule: async def run(schedule) -> str."""
        self._runner = runner

    def set_hook(self, hook: Callable) -> None:
        """Pre-run hook: async def hook(schedule) -> bool (return False to skip)."""
        self._hook = hook

    async def start(self, id_: str) -> bool:
        s = self._schedules.get(id_)
        if s is None or not s.enabled:
            return False
        if id_ in self._tasks:
            return True
        self._tasks[id_] = asyncio.ensure_future(self._run_loop(s))
        return True

    async def start_all(self) -> int:
        count = 0
        for s in list(self._schedules.values()):
            if await self.start(s.id):
                count += 1
        return count

    def stop(self, id_: str) -> None:
        t = self._tasks.pop(id_, None)
        if t:
            t.cancel()

    def stop_all(self) -> None:
        for tid in list(self._tasks):
            self.stop(tid)

    # -- run loop -----------------------------------------------------------
    async def _run_loop(self, s: Schedule) -> None:
        while s.enabled and s.id in self._tasks:
            now = time.time()
            next_fire = self._next_fire(s, now)
            if next_fire <= now:
                await self._fire(s)
            await asyncio.sleep(min(60, max(1, next_fire - time.time() if next_fire > time.time() else 60)))

    async def _fire(self, s: Schedule) -> None:
        if self._hook is not None:
            try:
                ok = self._hook(s)
                if hasattr(ok, "__await__"):
                    ok = await ok
                if ok is False:
                    return
            except Exception:
                pass

        s.phase = "running"
        s.last_run_at = time.time()
        self._save()

        try:
            if self._runner is not None:
                result = self._runner(s)
                if hasattr(result, "__await__"):
                    result = await result
                s.last_status = str(result)[:200]
        except Exception as exc:
            s.last_status = f"error: {exc}"
            s.phase = "failed"
        else:
            s.phase = "completed"
        finally:
            s.run_count += 1
            if s.max_runs > 0 and s.run_count >= s.max_runs:
                s.enabled = False
            self._save()

    @staticmethod
    def _next_fire(s: Schedule, now: float) -> float:
        if s.interval_ms > 0:
            base = s.last_run_at or now
            planned = base + s.interval_ms / 1000
            return planned if planned > now else now + s.interval_ms / 1000
        return now + 60  # cron: simplified — fire every 60s if cron expression present

    # -- persistence --------------------------------------------------------
    def _save(self) -> None:
        path = self._base / "schedules.json"
        data = [{"id": s.id, "name": s.name, "prompt": s.prompt, "cron_expr": s.cron_expr,
                  "interval_ms": s.interval_ms, "enabled": s.enabled, "phase": s.phase,
                  "last_run_at": s.last_run_at, "last_status": s.last_status,
                  "run_count": s.run_count, "max_runs": s.max_runs, "template_id": s.template_id}
                for s in self._schedules.values()]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def _load(self) -> None:
        path = self._base / "schedules.json"
        if not path.exists():
            return
        try:
            for d in json.loads(path.read_text(encoding="utf-8")):
                self._schedules[d["id"]] = Schedule(**{k: d.get(k) for k in Schedule.__dataclass_fields__})
        except Exception:
            pass
