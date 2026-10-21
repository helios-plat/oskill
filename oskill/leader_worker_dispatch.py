"""Leader/worker dispatch.

The original goal-decomposition API is retained. Supplying ``workers`` selects
the Veya task-dispatch API and returns an awaitable.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError

WorkerFn = Callable[[str, dict[str, Any]], Awaitable[Any] | Any]


@runtime_checkable
class LeaderHandle(Protocol):
    async def assign(self, task: str, workers: list[str]) -> str: ...


def leader_worker_dispatch(
    goal: str | list[str],
    members: list[dict[str, Any]] | None = None,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    *,
    tasks: list[str] | None = None,
    workers: dict[str, WorkerFn] | None = None,
    leader: LeaderHandle | None = None,
    strategy: str = "round_robin",
    task_payloads: dict[str, dict[str, Any]] | None = None,
    **kwargs: Any,
) -> Any:
    """Dispatch tasks when ``workers`` is provided, otherwise decompose a goal."""
    if workers is not None:
        dispatch_tasks = tasks if tasks is not None else (
            list(goal) if isinstance(goal, list) else [goal]
        )
        return _leader_worker_dispatch_async(
            dispatch_tasks,
            workers=workers,
            leader=leader,
            strategy=strategy,
            task_payloads=task_payloads,
        )
    return _legacy_dispatch(str(goal), members, llm_caller, context)


def _legacy_dispatch(
    goal: str,
    members: list[dict[str, Any]] | None,
    llm_caller: Callable | None,
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    ctx = context or {}
    member_names = [member.get("name", "") for member in (members or [])]

    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            import json

            out = llm_caller(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a team leader. Decompose the goal into specialized "
                            "worker roles. Output JSON array of {worker_name, role, prompt, "
                            "skills: [skill names], depends_on: [worker names]}."
                            "\nOutput ONLY valid JSON array between ```json and ```."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Goal: {goal}\nAvailable members: {member_names}",
                    },
                ],
                tools=None,
                config=ctx,
            )
            raw = out.get("content", "") if isinstance(out, dict) else str(out)
            match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            parsed = (
                json.loads(match.group(1))
                if match
                else json.loads(raw) if raw.strip().startswith("[") else []
            )
            if isinstance(parsed, list) and parsed:
                return _normalize_workers(parsed, member_names)
        except Exception:
            pass

    items = re.split(r"\n\s*\d+[\.\)]\s+|(?:\n?\s*[-•*]\s+)", goal.strip())
    if len(items) <= 1:
        items = [goal]
    workers = []
    for index, item in enumerate(items):
        item = item.strip()
        if not item:
            continue
        name = member_names[index] if index < len(member_names) else f"worker-{index + 1}"
        deps = [member_names[index - 1]] if index > 0 and index - 1 < len(member_names) else []
        workers.append(
            {
                "worker_name": name,
                "role": item[:40],
                "prompt": f"你是 {name}，负责 {item}。使用你的专业工具完成任务后报告结果。",
                "skills": [],
                "depends_on": deps,
                "worktree_branch": f"swarm/{name}",
            }
        )
    return workers


def _normalize_workers(parsed: list[dict], member_names: list[str]) -> list[dict]:
    for index, worker in enumerate(parsed):
        worker.setdefault(
            "worker_name",
            member_names[index] if index < len(member_names) else f"worker-{index + 1}",
        )
        worker.setdefault("depends_on", [])
        worker.setdefault("skills", [])
        worker.setdefault(
            "worktree_branch",
            f"swarm/{worker.get('worker_name', f'w{index}')}",
        )
    return parsed


async def _leader_worker_dispatch_async(
    tasks: list[str],
    *,
    workers: dict[str, WorkerFn],
    leader: LeaderHandle | None,
    strategy: str,
    task_payloads: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if not tasks:
        raise OskillError("leader_worker_dispatch: tasks must not be empty")
    if not workers:
        raise OskillError("leader_worker_dispatch: workers must not be empty")
    worker_names = list(workers)

    assignments: dict[str, str] = {}
    busy: dict[str, int] = {worker: 0 for worker in worker_names}
    counter = 0
    for task in tasks:
        if leader is not None:
            try:
                chosen = await leader.assign(task, worker_names)
            except Exception:
                chosen = worker_names[counter % len(worker_names)]
        elif strategy == "least_busy":
            chosen = min(busy, key=busy.get)
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
            if hasattr(outcome, "__await__") or isinstance(outcome, Awaitable):
                outcome = await outcome
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
