"""3O 范式全栈 — 工具协议翻译技能 (纯计算, 无 IO).

在 OpenAI function-call 与 Anthropic tool_use 两种工具调用格式间互转。
"""

from __future__ import annotations

import json
from typing import Any

_SUPPORTED_TARGETS = {"openai", "anthropic"}


def translate_tool_calls(
    calls: list[dict[str, Any]],
    *,
    target: str = "anthropic",
) -> list[dict[str, Any]]:
    """技能 18: 工具调用格式互转。

    OpenAI 形如 {"name": ..., "arguments": {...} | "<json 字符串>"};
    Anthropic 形如 {"name": ..., "input": {...}}。

    Args:
        calls: 源格式工具调用列表。
        target: 目标格式, "anthropic" 或 "openai"。

    Raises:
        ValueError: 目标格式不支持。
    """
    if target not in _SUPPORTED_TARGETS:
        raise ValueError(f"Unsupported target format: {target}")

    translated: list[dict[str, Any]] = []
    for call in calls:
        if target == "anthropic":
            args: Any = call.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            translated.append({"name": call["name"], "input": args})
        else:
            translated.append({"name": call["name"], "arguments": call.get("input", {})})
    return translated
