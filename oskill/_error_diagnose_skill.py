"""oskill.error_diagnose_skill — 代码运行报错堆栈自动诊断与修复方案推荐.

组合 oprim.ast_parse_code（定位报错符号）+ oprim.llm_chat_call（诊断推演），
输出根因假设、证据与修复建议。stateless。

Example:
    >>> r = await error_diagnose_skill(
    ...     traceback_text, file_paths=["/repo/app.py"], caller=my_caller,
    ... )
    >>> "root_cause" in r
    True
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from oprim import ast_parse_code, llm_chat_call

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class DiagCaller(Protocol):
    """诊断 LLM 调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def error_diagnose_skill(
    traceback_text: str,
    *,
    caller: DiagCaller,
    file_paths: list[str] | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """诊断报错并推荐修复方案。

    Args:
        traceback_text: 报错堆栈文本。
        caller: LLM 调用器（注入）。
        file_paths: 相关代码文件（用于符号定位），可选。
        max_tokens: 诊断输出上限。

    Returns:
        {
            "root_cause": str,
            "confidence": float,        # 0..1
            "evidence": [str],
            "fix_suggestions": [str],
            "related_symbols": [str],
        }

    Raises:
        OskillError: traceback 为空。
        LLMOskillError: 诊断调用失败。
    """
    if not traceback_text or not traceback_text.strip():
        raise OskillError("error_diagnose_skill: traceback_text must not be empty")


    related_symbols: list[str] = []
    code_context: list[str] = []
    for path in file_paths or []:
        try:
            parsed = await ast_parse_code(path)
            symbols = [f["name"] for f in parsed["functions"]] + [
                c["name"] for c in parsed["classes"]
            ]
            related_symbols.extend(symbols)
            code_context.append(f"# {path}: {', '.join(symbols[:20])}")
        except Exception:  # noqa: BLE001 - 单文件失败不致命
            continue

    # 从堆栈提取文件名线索（辅助证据）
    evidence = list(dict.fromkeys(re.findall(r'File "([^"]+\.py)", line \d+', traceback_text)))

    prompt = (
        "你是资深调试工程师。分析以下报错堆栈并输出 JSON："
        '{"root_cause": "...", "confidence": 0.0-1.0, "fix_suggestions": ["..."]}\n\n'
        f"报错堆栈:\n{traceback_text[:6000]}\n"
        + ("\n相关代码符号:\n" + "\n".join(code_context) if code_context else "")
    )
    try:
        resp = await llm_chat_call(
            [{"role": "user", "content": prompt}],
            caller=caller,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        raise LLMOskillError("error_diagnose_skill: diagnosis call failed", cause=exc) from exc

    text = resp["text"]
    parsed: dict[str, Any] = _try_json(text)
    return {
        "root_cause": str(parsed.get("root_cause") or text[:500]),
        "confidence": float(parsed.get("confidence") or 0.5),
        "evidence": evidence,
        "fix_suggestions": list(parsed.get("fix_suggestions") or []),
        "related_symbols": related_symbols,
    }


def _try_json(text: str) -> dict[str, Any]:
    """容错提取 JSON 对象（截取首尾大括号）。"""
    import json

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}
