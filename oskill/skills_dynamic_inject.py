"""oskill.skills_dynamic_inject — Cindy-style dynamic skill injection into agent context.

When plugins are installed or skills are taught, this element dynamically
injects the relevant prompts, tools, and configuration into the agent's
runtime context — without restarting the harness.  Mirrors Cindy's plugin
capability listing and customization injection.

3O element: ``oskill.skills_dynamic_inject``.
"""

from __future__ import annotations

from typing import Any


def skills_dynamic_inject(
    agent_context: dict[str, Any],
    plugin_name: str | None = None,
    skill_id: str | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dynamically inject a skill or plugin capability into the agent context.

    Args:
        agent_context: The current agent runtime context (system_prompt, tools, config).
        plugin_name: Optional plugin to inject (loads its capabilities).
        skill_id: Optional skill to inject (loads its template + steps).
        context: Optional config.

    Returns:
        {injected, system_prompt_additions, tools_added, config_updates}
    """
    ctx = context or {}
    injected: dict[str, Any] = {
        "system_prompt_additions": [],
        "tools_added": [],
        "config_updates": {},
    }

    # plugin injection
    if plugin_name:
        try:
            from obase.plugin_registry import PluginRegistry

            reg = PluginRegistry()
            plugins = reg.list_installed()
            for p in plugins:
                if p["name"] == plugin_name and p.get("enabled", True):
                    caps = p.get("capabilities", [])
                    injected["system_prompt_additions"].append(
                        f"[Plugin: {plugin_name} v{p.get('version', '?')}] "
                        f"Capabilities: {', '.join(caps)}."
                    )
                    injected["config_updates"][f"plugin.{plugin_name}"] = p.get("config", {})
                    for cap in caps:
                        if cap.startswith("tool."):
                            injected["tools_added"].append(cap[5:])
        except Exception:
            pass

    # skill injection
    if skill_id:
        try:
            from oskill.skill_teach import skill_list

            skills = skill_list()
            for s in skills:
                fm = s.get("frontmatter", {})
                if fm.get("id") == f"skill/{skill_id}" or fm.get("id") == skill_id:
                    body = s.get("body", "")
                    injected["system_prompt_additions"].append(
                        f"[Skill: {skill_id}]\n{body[:500]}"
                    )
                    # extract tools from markdown body
                    for line in body.splitlines():
                        if line.strip().startswith("- ") and "tool" in line.lower():
                            injected["tools_added"].append(line.strip("- ").strip())
        except Exception:
            pass

    # inject all skills by default
    if plugin_name is None and skill_id is None:
        try:
            from oskill.skill_teach import skill_list

            for s in skill_list():
                fm = s.get("frontmatter", {})
                sid = fm.get("id", "")
                body = s.get("body", "")
                if body:
                    injected["system_prompt_additions"].append(
                        f"[Skill: {sid}]\n{body[:300]}"
                    )
        except Exception:
            pass

    # apply to agent context
    sys_prompt = agent_context.get("system_prompt", "")
    if injected["system_prompt_additions"]:
        sys_prompt += "\n\n## Dynamic Skills & Plugins\n" + "\n".join(injected["system_prompt_additions"])
    agent_context["system_prompt"] = sys_prompt
    agent_context.setdefault("tools", []).extend(injected["tools_added"])
    agent_context.setdefault("config", {}).update(injected["config_updates"])

    return {"status": "injected", **injected}
