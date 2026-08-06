"""oskill.team_plan_gen — ClawTeam-style team task plan decomposition.

Takes a high-level goal and decomposes it into subtasks for a team, estimating
dependencies (blocked_by chains) and assigning initial priorities.  Uses LLM
when mounted; deterministic fallback splits by delimiter keywords.

3O element: ``oskill.team_plan_gen``.
"""

from __future__ import annotations

from typing import Any, Callable


def team_plan_gen(
    goal: str,
    members: list[dict[str, Any]] | None = None,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Decompose a goal into subtasks with dependencies.

    Args:
        goal: High-level team objective.
        members: Optional team members (used for role-based assignment hints).
        llm_caller: Optional LLM → structured task decomposition.
        context: Optional config.

    Returns:
        [{id, subject, description, priority, blocks, blocked_by, suggested_owner}, ...]
    """
    ctx = context or {}

    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            out = llm_caller(
                messages=[
                    {"role": "system", "content": (
                        "You are a team planner. Decompose the goal into subtasks. "
                        "Output JSON array of {subject, description, priority(low|medium|high|urgent), "
                        "blocks:[task_ids that this blocks], blocked_by:[task_ids this depends on], suggested_owner}."
                        "\nOutput ONLY valid JSON array between ```json and ```."
                    )},
                    {"role": "user", "content": f"Goal: {goal}\nTeam members: {[m.get('name','') for m in (members or [])]}"},
                ],
                tools=None, config=ctx,
            )
            import json, re
            raw = out.get("content") or "" if isinstance(out, dict) else str(out)
            m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            if m:
                parsed = json.loads(m.group(1))
                if isinstance(parsed, list) and parsed:
                    return _normalize(parsed)
        except Exception:
            pass

    return _deterministic_split(goal)


def _deterministic_split(goal: str) -> list[dict[str, Any]]:
    """Fallback: split by numbered items or delimiter patterns."""
    import re
    items = re.split(r"\n\s*\d+[\.\)]\s+|(?:\n?\s*[-•*]\s+)", goal.strip())
    if len(items) <= 1:
        items = [goal]
    tasks = []
    for i, item in enumerate(items):
        item = item.strip()
        if not item:
            continue
        tid = f"t{i+1}"
        blocked_by = [f"t{i}"] if i > 0 else []
        tasks.append({
            "id": tid,
            "subject": item[:80],
            "description": item,
            "priority": "high" if i == 0 else "medium",
            "blocks": [f"t{i+2}"] if i + 1 < len(items) else [],
            "blocked_by": blocked_by,
            "suggested_owner": "",
        })
    return tasks


def _normalize(tasks: list[dict]) -> list[dict[str, Any]]:
    for i, t in enumerate(tasks):
        t.setdefault("id", f"t{i+1}")
        t.setdefault("blocks", [])
        t.setdefault("blocked_by", [])
        t.setdefault("priority", "medium")
        t.setdefault("suggested_owner", "")
    return tasks
