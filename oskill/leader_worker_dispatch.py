"""oskill.leader_worker_dispatch — ClawTeam auto-spawning specialized workers.

Takes a high-level goal, decomposes it into worker roles, and generates
custom system prompts for each worker. The Leader agent dynamically spawns
workers with role-specific tool access and git worktree isolation.

3O element: ``oskill.leader_worker_dispatch``.
"""

from __future__ import annotations

from typing import Any, Callable


def leader_worker_dispatch(
    goal: str,
    members: list[dict[str, Any]] | None = None,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Decompose a goal into specialized worker assignments.

    Args:
        goal: Team objective.
        members: Available team members (name, agent_type, skills).
        llm_caller: Optional LLM for role-based decomposition.
        context: Optional config.

    Returns:
        [{worker_name, role, prompt, skills, depends_on, worktree_branch}, ...]
    """
    ctx = context or {}
    member_names = [m.get("name", "") for m in (members or [])]

    # LLM path
    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            import json, re
            out = llm_caller(
                messages=[{"role": "system", "content": (
                    "You are a team leader. Decompose the goal into specialized worker roles. "
                    "Output JSON array of {worker_name, role, prompt (system prompt for worker), "
                    "skills: [skill names], depends_on: [worker names that must finish first]}."
                    "\nOutput ONLY valid JSON array between ```json and ```."
                )}, {"role": "user", "content": f"Goal: {goal}\nAvailable members: {member_names}"}],
                tools=None, config=ctx,
            )
            raw = out.get("content", "") if isinstance(out, dict) else str(out)
            m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            parsed = json.loads(m.group(1)) if m else json.loads(raw) if raw.strip().startswith("[") else []
            if isinstance(parsed, list) and parsed:
                return _normalize_workers(parsed, member_names)
        except Exception:
            pass

    # Fallback: one worker per goal segment
    import re
    items = re.split(r"\n\s*\d+[\.\)]\s+|(?:\n?\s*[-•*]\s+)", goal.strip())
    if len(items) <= 1:
        items = [goal]
    workers = []
    for i, item in enumerate(items):
        item = item.strip()
        if not item:
            continue
        name = member_names[i] if i < len(member_names) else f"worker-{i+1}"
        deps = [member_names[i-1]] if i > 0 and i-1 < len(member_names) else []
        workers.append({
            "worker_name": name,
            "role": item[:40],
            "prompt": f"你是 {name}，负责 {item}。使用你的专业工具完成任务后报告结果。",
            "skills": [],
            "depends_on": deps,
            "worktree_branch": f"swarm/{name}",
        })
    return workers


def _normalize_workers(parsed: list[dict], member_names: list[str]) -> list[dict]:
    for i, w in enumerate(parsed):
        w.setdefault("worker_name", member_names[i] if i < len(member_names) else f"worker-{i+1}")
        w.setdefault("depends_on", [])
        w.setdefault("skills", [])
        w.setdefault("worktree_branch", f"swarm/{w.get('worker_name', f'w{i}')}")
    return parsed
