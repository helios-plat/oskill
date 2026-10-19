"""oskill: 反例解析器。纯字符串与正则算法，无底层依赖。

Stateless 纯算法。

从 CrossHair / Z3 的 SMT 报错日志中提取结构化反例输入，
用于反馈给 LLM 进行定向修复。
"""

from __future__ import annotations

import re
from typing import Any


def _extract_counterexample(stderr: str) -> dict[str, Any]:
    """从 CrossHair 输出中提取具体的反例输入 (Counterexample).

    解析 CrossHair 的典型输出格式:
    - "error: false when calling f(x=...)"
    - "Exception: ZeroDivisionError when ..."
    - "Found counterexample: ..."

    Args:
        stderr: CrossHair 的 stderr 输出

    Returns:
        {
            "found": bool,
            "failing_call": str | None,
            "error_type": str | None,
            "raw_error": str,
        }
    """
    if not stderr:
        return {
            "found": False,
            "failing_call": None,
            "error_type": None,
            "raw_error": "",
        }

    # 模式 1: CrossHair 反例 "false when calling f(args)"
    match = re.search(
        r"(?:false|error)\s+when\s+calling\s+(.+?)(?:\n|$)",
        stderr,
        re.IGNORECASE,
    )
    if match:
        return {
            "found": True,
            "failing_call": match.group(1).strip(),
            "error_type": "contract_violation",
            "raw_error": stderr.strip()[:2000],
        }

    # 模式 2: Counterexample found
    match = re.search(
        r"counterexample[:\s]+(.*)",
        stderr,
        re.IGNORECASE,
    )
    if match:
        return {
            "found": True,
            "failing_call": match.group(1).strip()[:200],
            "error_type": "counterexample",
            "raw_error": stderr.strip()[:2000],
        }

    # 模式 3: Python 异常 (ZeroDivisionError, IndexError, AssertionError...)
    match = re.search(
        r"(ZeroDivisionError|IndexError|OverflowError|AssertionError|ValueError|TypeError|KeyError)[:\s]*(.*)",
        stderr,
    )
    if match:
        return {
            "found": True,
            "failing_call": f"{match.group(1)}: {match.group(2).strip()[:100]}",
            "error_type": match.group(1),
            "raw_error": stderr.strip()[:2000],
        }

    # 模式 4: 通用 Error/Exception
    if re.search(r"(Exception|Error)[:\s]", stderr, re.IGNORECASE):
        return {
            "found": True,
            "failing_call": "unknown_trigger",
            "error_type": "generic_error",
            "raw_error": stderr.strip()[:2000],
        }

    return {
        "found": False,
        "failing_call": None,
        "error_type": None,
        "raw_error": stderr.strip()[:1000],
    }
