"""oskill.code_review_gate — 独立 Reviewer Agent 审查 Git Diff 代码质量与缺陷.

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


def code_review_gate(
    git_diff_str: str,
    *,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """独立 Reviewer Agent 审查 Git Diff 代码质量与缺陷 (Stateless).

    检查项：
    1. 逻辑 Bug
    2. 安全问题
    3. 代码风格

    Args:
        git_diff_str: Git diff 文本
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "approved": bool,
            "issues": list[str],
            "suggestions": str,
        }
    """
    prompt = (
        "Perform strict Code Review on the following Git Diff:\n"
        f"```diff\n{git_diff_str}\n```\n"
        "Check for: 1. Logic Bugs 2. Security Issues 3. Code Style.\n"
        "Reply with a JSON object ONLY (no markdown, no extra text):\n"
        "{\n"
        '  "approved": true/false,\n'
        '  "critical_issues": ["issue1", "issue2"],\n'
        '  "suggestions": "summary of suggestions"\n'
        "}"
    )
    try:
        raw = llm_caller(prompt, temperature=0.0)
        # 提取 JSON（处理可能的 markdown 包装）
        raw = raw.strip()
        if "```" in raw:
            # 提取 code block 内容
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("{") or part.startswith("json"):
                    raw = part.replace("json\n", "").replace("json", "").strip()
                    break

        parsed = json.loads(raw)
        return {
            "approved": parsed.get("approved", False),
            "issues": parsed.get("critical_issues", []),
            "suggestions": parsed.get("suggestions", ""),
        }
    except (json.JSONDecodeError, Exception):
        return {
            "approved": False,
            "issues": ["Failed to parse review response from LLM."],
            "suggestions": raw if "raw" in dir() else "",
        }
