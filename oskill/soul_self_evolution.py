"""oskill.soul_self_evolution — DeerFlow agent self-evolution (SOUL.md / config).

Evaluates the agent's own execution results and proposes updates to SOUL.md
and config files.  Mirrors DeerFlow's ``update_agent_tool``: the agent can
persist its own behavior changes (skills, model settings, thinking mode).

3O element: ``oskill.soul_self_evolution``.
"""

from __future__ import annotations

from typing import Any, Callable


def soul_self_evolution(
    agent_name: str,
    current_soul: str,
    current_config: dict[str, Any],
    execution_feedback: str,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Evaluate execution results and propose SOUL.md / config changes.

    Args:
        agent_name: The agent evaluating itself.
        current_soul: Current SOUL.md content.
        current_config: Current config dict (model_settings, skills, thinking_enabled, etc.).
        execution_feedback: What went well/poorly (tool output, error traces, user feedback).
        llm_caller: Optional LLM for structured evolution proposal.
        context: Runtime context.

    Returns:
        {proposed_soul, proposed_config, changes: [{field, old, new, reason}], status}
    """
    ctx = context or {}

    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            import json, re
            prompt = (
                f"You are {agent_name} evaluating your own performance. "
                f"Current SOUL.md: {current_soul[:2000]}\n"
                f"Current config: {json.dumps(current_config, ensure_ascii=False)[:1000]}\n"
                f"Execution feedback: {execution_feedback[:2000]}\n\n"
                "Propose specific, minimal changes to SOUL.md and config. "
                "Output JSON: {\"soul_changes\": [{\"line\": \"old text\", \"new\": \"new text\", \"reason\": \"...\"}], "
                "\"config_changes\": {\"key\": \"new_value\", ...}}"
            )
            out = llm_caller(messages=[{"role": "user", "content": prompt}], tools=None, config=ctx)
            raw = out.get("content") or "" if isinstance(out, dict) else str(out)
            m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            parsed = json.loads(m.group(1)) if m else (json.loads(raw) if raw.strip().startswith("{") else {})
        except Exception:
            parsed = {}

        return {
            "proposed_soul": _apply_soul_changes(current_soul, parsed.get("soul_changes", [])),
            "proposed_config": {**current_config, **parsed.get("config_changes", {})},
            "changes": [
                {"field": "soul", "old": sc.get("line", "")[:80], "new": sc.get("new", "")[:80], "reason": sc.get("reason", "")}
                for sc in parsed.get("soul_changes", [])
            ] + [
                {"field": k, "old": str(current_config.get(k, "")), "new": str(v), "reason": "performance feedback"}
                for k, v in parsed.get("config_changes", {}).items()
            ],
            "status": "analyzed",
        }

    # deterministic fallback: add a feedback annotation to SOUL.md
    new_soul = current_soul
    if execution_feedback:
        new_soul += f"\n\n<!-- Self-evaluation ({_now()}): {execution_feedback[:300]} -->\n"
    return {
        "proposed_soul": new_soul,
        "proposed_config": current_config,
        "changes": [{"field": "soul", "old": "", "new": "evaluation annotation appended", "reason": execution_feedback[:80]}],
        "status": "analyzed",
    }


def _apply_soul_changes(soul: str, changes: list[dict[str, Any]]) -> str:
    out = soul
    for ch in changes:
        old = ch.get("line", "")
        new = ch.get("new", "")
        if old and old in out:
            out = out.replace(old, new, 1)
    return out


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M:%S")
