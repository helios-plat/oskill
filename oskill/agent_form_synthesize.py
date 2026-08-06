"""oskill.agent_form_synthesize — NL → agent form (AutoAgent "zero-code" core).

Takes a natural-language user request and produces a structured agent form
(XML or dict) ready for ``oprim.agent_codegen``.  Uses an LLM caller when
mounted; deterministic fallback extracts name/tools/instructions from simple
NL patterns.

3O element: ``oskill.agent_form_synthesize``.
"""

from __future__ import annotations

import re
from typing import Any, Callable


def agent_form_synthesize(
    user_request: str,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convert a natural-language agent description into a structured spec.

    Args:
        user_request: Human description (e.g. "做一个代码审查agent, 用pytest和git工具")
        llm_caller: Optional LLM callable (messages, tools, config) → {content}
        context: Optional runtime context

    Returns:
        AgentSpec dict: {name, description, tools, instructions, model, handoffs}
    """
    ctx = context or {}

    # LLM path — when mounted
    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            out = llm_caller(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an agent form generator.  Output a JSON object with keys: "
                            "name, description, tools (list of tool names), instructions (system prompt), "
                            "model (optional, default 'claude-sonnet-4-6'), handoffs (optional dict)."
                            "\nOutput ONLY valid JSON between ```json and ```."
                        ),
                    },
                    {"role": "user", "content": user_request},
                ],
                tools=None,
                config=ctx,
            )
            raw = out.get("content") or "" if isinstance(out, dict) else str(out)
            import json

            m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            if m:
                return {**_default_form(user_request), **json.loads(m.group(1))}
            return {**_default_form(user_request), **json.loads(raw)} if raw.strip().startswith("{") else _default_form(user_request)
        except Exception:
            return _default_form(user_request)

    return _default_form(user_request)


def _default_form(request: str) -> dict[str, Any]:
    """Deterministic fallback parser for simple NL agent requests."""
    name = "CustomAgent"
    tools: list[str] = []
    desc = request.strip()[:120]

    # heuristic name extraction
    m = re.search(r"(?:叫|名字是|名称是|创建|做一个)\s*(.+?)\s*(?:agent|助手|机器人)", request)
    if m:
        name = m.group(1).strip()

    # tool detection by keyword
    tool_map = {
        "pytest": "pytest",
        "git": "git",
        "代码审查": "code_review",
        "code_review": "code_review",
        "search": "search",
        "搜索": "search",
        "file": "file",
        "terminal": "terminal",
        "docker": "docker",
        "memory": "memory",
        "memory_save": "memory_save",
        "memory_query": "memory_query",
        "web": "web",
        "scrape": "web",
        "github": "github",
    }
    for keyword, tool_name in tool_map.items():
        if keyword.lower() in request.lower():
            tools.append(tool_name)

    return {
        "name": name,
        "description": desc,
        "tools": list(set(tools)) or ["terminal"],
        "instructions": f"你是 {name}。{request.strip()}",
        "model": "claude-sonnet-4-6",
        "handoffs": {},
    }
