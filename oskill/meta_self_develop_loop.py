"""oskill.meta_self_develop_loop — AutoAgent self-development retry loop.

When an agent run returns "Case not resolved", a *meta agent* takes over,
creates new tools/agents via codegen + registry, then retries.  This is the
heart of AutoAgent's "Self-Managing Workflow Generation".

3O element: ``oskill.meta_self_develop_loop``.
"""

from __future__ import annotations

from typing import Any, Callable


async def meta_self_develop_loop(
    task: dict[str, Any],
    run_turn_fn: Callable,
    meta_fn: Callable,
    max_retry: int = 3,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a task through an agent with meta self-development retries.

    Args:
        task: {goal, agent_name, messages, context_variables}
        run_turn_fn: async (agent_id, messages, ctx) → Response {messages, agent, context_variables, resolved}
        meta_fn: async (messages, ctx) → {new_agents: [...], new_tools: [...], resolved}
        max_retry: Maximum retries before giving up
        context: Optional config

    Returns:
        {status, resolved, attempts, final_response, new_agents_created, new_tools_created}
    """
    ctx = context or {}
    goal = str(task.get("goal", ""))
    messages = list(task.get("messages") or [{"role": "user", "content": goal}])
    cvars = dict(task.get("context_variables") or {})

    new_agents: list[str] = []
    new_tools: list[str] = []

    turn_threshold = int(ctx.get("meta_turn_threshold", 2))
    total_attempts = 0
    resolved = False
    final_response: dict[str, Any] = {}

    for attempt in range(max_retry):
        total_attempts = attempt + 1
        try:
            resp = run_turn_fn(agent_id=task.get("agent_name"), messages=messages, context=cvars)
            if hasattr(resp, "__await__"):
                resp = await resp
        except Exception as exc:
            return {"status": "failed", "error": str(exc), "attempts": total_attempts}

        final_response = resp if isinstance(resp, dict) else {}
        messages = list(final_response.get("messages", []))
        cvars.update(final_response.get("context_variables") or {})

        # Check resolved signal (AutoAgent uses "Case resolved"/"Case not resolved")
        last_content = str(messages[-1].get("content", "")) if messages else ""
        if "case resolved" in last_content.lower() or "resolved" in last_content.lower():
            resolved = True
            break

        if "case not resolved" not in last_content.lower() and attempt < turn_threshold:
            messages.append({"role": "user", "content": "请继续尝试解决。"})
            continue

        # Meta agent takes over — create new tools/agents
        try:
            meta_resp = meta_fn(messages=messages, context=cvars)
            if hasattr(meta_resp, "__await__"):
                meta_resp = await meta_resp
        except Exception:
            meta_resp = {"resolved": False}

        if isinstance(meta_resp, dict):
            if meta_resp.get("resolved"):
                resolved = True
                break
            new_agents.extend(meta_resp.get("new_agents") or [])
            new_tools.extend(meta_resp.get("new_tools") or [])
            messages.extend(meta_resp.get("messages") or [])

    return {
        "status": "completed" if resolved else "exhausted_retries",
        "resolved": resolved,
        "attempts": total_attempts,
        "final_response": final_response,
        "new_agents_created": new_agents,
        "new_tools_created": new_tools,
    }
