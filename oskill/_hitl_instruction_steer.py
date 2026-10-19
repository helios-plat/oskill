"""oskill.hitl_instruction_steer — 干预指令融合算子.

把人工干预指令（中途打断时的纠正/重定向）融合进当前执行上下文，
产出带标记的转向指令。纯算法（stateless），支持三种融合模式：
- replace: 指令整体替换原计划片段（按 anchor 定位）
- prepend: 指令置于原文本之前（最高优先级）
- append:  指令追加在末尾（弱干预）

Example:
    >>> r = hitl_instruction_steer(
    ...     "改用 PostgreSQL", original_text=plan, mode="replace", anchor="数据库"
    ... )
    >>> r["steered"]
    True
"""

from __future__ import annotations

from typing import Any, Literal

from oskill._exceptions import OskillError

SteerMode = Literal["replace", "prepend", "append"]


def hitl_instruction_steer(
    instruction: str,
    *,
    original_text: str,
    mode: SteerMode = "prepend",
    anchor: str | None = None,
    markers: bool = True,
) -> dict[str, Any]:
    """融合人工干预指令到原文本。

    Args:
        instruction: 人工干预指令（打断时给出的纠正/重定向）。
        original_text: 当前执行计划/上下文文本。
        mode: 融合模式；replace 需 anchor 定位替换区间。
        anchor: replace 模式的定位锚（首个出现位置起整行替换）。
        markers: 是否加 [HITL] 标记。

    Returns:
        {
            "steered": bool,
            "mode": str,
            "text": str,            # 融合后文本
            "anchor": str | None,
            "replaced": bool,       # replace 模式是否命中锚
        }

    Raises:
        OskillError: instruction / original_text 为空；replace 无 anchor。
    """
    if not instruction or not instruction.strip():
        raise OskillError("hitl_instruction_steer: instruction must not be empty")
    if not original_text:
        raise OskillError("hitl_instruction_steer: original_text must not be empty")
    if mode == "replace" and not anchor:
        raise OskillError("hitl_instruction_steer: replace mode requires anchor")

    steered_instruction = f"[HITL 干预] {instruction}" if markers else instruction

    if mode == "prepend":
        return {
            "steered": True,
            "mode": mode,
            "text": f"{steered_instruction}\n\n{original_text}",
            "anchor": None,
            "replaced": False,
        }

    if mode == "append":
        return {
            "steered": True,
            "mode": mode,
            "text": f"{original_text}\n\n{steered_instruction}",
            "anchor": None,
            "replaced": False,
        }

    # replace：锚定位整行替换
    lines = original_text.splitlines()
    for i, line in enumerate(lines):
        if anchor in line:
            lines[i] = steered_instruction
            return {
                "steered": True,
                "mode": mode,
                "text": "\n".join(lines),
                "anchor": anchor,
                "replaced": True,
            }
    return {
        "steered": False,
        "mode": mode,
        "text": original_text,
        "anchor": anchor,
        "replaced": False,
    }
