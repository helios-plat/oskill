"""oskill.skill_teach — Cindy-style "teach once, reuse everywhere" skill system.

Natural language → skill template (name, trigger, steps, tools). Skills are
persisted to a knowledge store and can be exported/imported across harnesses
and teams.

3O element: ``oskill.skill_teach``.
"""

from __future__ import annotations

import json
from typing import Any, Callable


def skill_teach(
    description: str,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Teach a new skill from natural language description.

    Args:
        description: Natural-language description of "how to do X".
        llm_caller: Optional LLM for structured skill extraction.
        context: Optional config.

    Returns:
        {skill: {name, trigger, steps: [...], tools: [...], template}, status}
    """
    ctx = context or {}

    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            import re
            out = llm_caller(
                messages=[{"role": "system", "content": (
                    "Extract a reusable skill from this description. Output JSON: "
                    '{"name": "skill name", "trigger": "when to use (keyword pattern)", '
                    '"steps": ["step 1", "step 2", ...], "tools": ["tool1", ...], '
                    '"template": "reusable prompt template with {placeholders}"}'
                    "\nOutput ONLY valid JSON between ```json and ```."
                )}, {"role": "user", "content": description}],
                tools=None, config=ctx,
            )
            raw = out.get("content", "") if isinstance(out, dict) else str(out)
            m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            parsed = json.loads(m.group(1)) if m else (json.loads(raw) if raw.strip().startswith("{") else {})
            skill = {
                "name": parsed.get("name", "unnamed_skill"),
                "trigger": parsed.get("trigger", description[:60]),
                "steps": parsed.get("steps", []),
                "tools": parsed.get("tools", []),
                "template": parsed.get("template", ""),
            }
        except Exception:
            skill = _deterministic_skill(description)
    else:
        skill = _deterministic_skill(description)

    # persist to knowledge store
    try:
        from obase.knowledge_store import KnowledgeStore
        store = KnowledgeStore()
        store.write(
            id_=f"skill/{skill['name']}", type_="skill",
            body=f"# {skill['name']}\n\n**Trigger:** {skill['trigger']}\n\n**Steps:**\n" +
                 "\n".join(f"- {s}" for s in skill['steps']) +
                 f"\n\n**Template:**\n```\n{skill['template']}\n```",
            covers=skill.get("tools", []),
        )
    except Exception:
        pass

    return {"status": "taught", "skill": skill}


def skill_list(context: dict[str, Any] | None = None, **kwargs: Any) -> list[dict[str, Any]]:
    """List all taught skills from the knowledge store."""
    try:
        from obase.knowledge_store import KnowledgeStore
        store = KnowledgeStore()
        return store.list_all(type_="skill")
    except Exception:
        return []


def skill_export(skill_id: str, output_dir: str | None = None) -> dict[str, Any]:
    """Export a skill as a shareable markdown package."""
    try:
        from obase.knowledge_store import KnowledgeStore
        store = KnowledgeStore()
        doc = store.read(f"skill/{skill_id}")
        if doc is None:
            return {"status": "not_found", "skill_id": skill_id}
        return {"status": "exported", "skill_id": skill_id, "content": doc["body"], "frontmatter": doc["frontmatter"]}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def skill_import_(content: str, frontmatter: dict[str, Any] | None = None) -> dict[str, Any]:
    """Import a shared skill from its markdown content."""
    try:
        from obase.knowledge_store import KnowledgeStore
        store = KnowledgeStore()
        skill_id = (frontmatter or {}).get("id", "imported_skill")
        store.write(id_=skill_id, type_="skill", body=content, **(frontmatter or {}))
        return {"status": "imported", "skill_id": skill_id}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _deterministic_skill(description: str) -> dict[str, Any]:
    words = description.split()
    name = next((w for w in words if len(w) > 2), "custom_skill")
    return {
        "name": name.lower(),
        "trigger": description[:60],
        "steps": [description],
        "tools": [],
        "template": f"Task: {description}\n\nSteps:\n{description}",
    }
