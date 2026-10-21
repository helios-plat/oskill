"""oskill.leader_worker_dispatch — 领导者-工作者任务分发.

把任务分发给注入的 worker callables；可选 leader（注入）决定任务-工作者
映射，缺省轮询（round_robin）/最少负载（least_busy）。stateless。

Example:
    >>> r = await leader_worker_dispatch(["t1", "t2"], workers={"w1": fn, "w2": fn})
    >>> r["completed"] == 2
    True
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError

WorkerFn = Callable[[str, dict[str, Any]], Awaitable[Any] | Any]


@runtime_checkable
class LeaderHandle(Protocol):
    """领导者协议（注入面）：决定任务 → worker 分配。"""

    async def assign(self, task: str, workers: list[str]) -> str: ...


async def leader_worker_dispatch(
    tasks: list[str],
    *,
    workers: dict[str, WorkerFn],
    leader: LeaderHandle | None = None,
    strategy: str = "round_robin",
    task_payloads: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """分发任务到 workers 并聚合结果。

    Args:
        tasks: 任务 ID 列表。
        workers: {worker_name: async callable(task_id, payload) -> Any}。
        leader: 领导者（可选，注入）。
        strategy: leader 缺省时的分配策略 round_robin | least_busy。
        task_payloads: 任务载荷（可选）。

    Returns:
        {"status": "completed", "completed": int, "failed": int,
         "assignments": {task: worker}, "results": {task: Any},
         "errors": {task: str}}

    Raises:
        OskillError: tasks / workers 为空。
    """
    if not tasks:
        raise OskillError("leader_worker_dispatch: tasks must not be empty")
    if not workers:
        raise OskillError("leader_worker_dispatch: workers must not be empty")
    worker_names = list(workers)

    assignments: dict[str, str] = {}
    busy: dict[str, int] = {w: 0 for w in worker_names}
    counter = 0
    for task in tasks:
        if leader is not None:
            try:
                chosen = await leader.assign(task, worker_names)
            except Exception:  # noqa: BLE001 - leader 失败回退轮询
                chosen = worker_names[counter % len(worker_names)]
        elif strategy == "least_busy":
            chosen = min(busy, key=busy.get)  # type: ignore[arg-type]
        else:
            chosen = worker_names[counter % len(worker_names)]
        assignments[task] = chosen
        busy[chosen] += 1
        counter += 1

    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for task, worker_name in assignments.items():
        try:
            outcome = workers[worker_name](task, (task_payloads or {}).get(task, {}))
            if hasattr(outcome, "__await__") or isinstance(outcome, Awaitable):  # type: ignore[arg-type]
                outcome = await outcome  # type: ignore[misc]
            results[task] = outcome
        except Exception as exc:
            errors[task] = f"{type(exc).__name__}: {exc}"

    return {
        "status": "completed",
        "completed": len(results),
        "failed": len(errors),
        "assignments": assignments,
        "results": results,
        "errors": errors,
    }
