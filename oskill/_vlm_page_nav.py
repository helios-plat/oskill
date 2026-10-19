"""oskill.vlm_page_nav — 基于 Bounding-Box 的多模态网页导航算法.

Stateless 纯算法。依赖 LLMCallerProtocol 注入（不在顶层 import oprim）.

组合: LLM caller (依赖注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol — 不 import oprim，由调用方注入."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def vlm_page_nav(
    page_state: dict[str, Any],
    goal: str,
    *,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """结合网页 Bounding-Box 与目标导向的多模态视觉导航定位算法.

    根据页面元素信息与用户目标，决策下一步交互操作。

    Args:
        page_state: 页面状态，包含:
            - url: str
            - elements: list[dict] (每个含 id, type, box, text)
        goal: 用户导航目标描述
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "status": "success" | "failed",
            "action_spec": {
                "action": "click" | "type" | "scroll" | "navigate" | "wait",
                "target_id": str,
                "value": str,
            }
        }
    """
    elements = page_state.get("elements", [])

    # 构建元素描述
    element_desc = []
    for elem in elements:
        if isinstance(elem, dict):
            eid = elem.get("id", elem.get("element_id", ""))
            etype = elem.get("type", elem.get("element_type", ""))
            etext = elem.get("text", "")
            ebox = elem.get("box", [])
            element_desc.append(f"  - id={eid}, type={etype}, box={ebox}, text='{etext}'")

    prompt = (
        f"Goal: {goal}\n\n"
        f"Page URL: {page_state.get('url', 'unknown')}\n\n"
        f"Available interactive elements:\n" + "\n".join(element_desc) + "\n\n"
        "Determine the next element to interact with to achieve the goal.\n"
        "Reply with a JSON object ONLY:\n"
        "{\n"
        '  "action": "click" or "type" or "navigate" or "scroll" or "wait",\n'
        '  "target_id": "element id",\n'
        '  "value": "text to type (only for action=type)"\n'
        "}"
    )

    try:
        raw = llm_caller(prompt, temperature=0.0)
        raw = raw.strip()
        # 提取 JSON
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("{") or part.startswith("json"):
                    raw = part.replace("json\n", "").replace("json", "").strip()
                    break

        parsed = json.loads(raw)
        return {
            "status": "success",
            "action_spec": {
                "action": parsed.get("action", "click"),
                "target_id": parsed.get("target_id", ""),
                "value": parsed.get("value", ""),
            },
        }
    except (json.JSONDecodeError, Exception):
        return {
            "status": "failed",
            "action_spec": {"action": "wait", "target_id": "", "value": ""},
        }
