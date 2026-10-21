"""3O 范式内化 — OpenRSI Draft 算子 (oskill).

输入需求描述, 生成初版完整代码。LLM 经协议注入, 无状态。
"""

from __future__ import annotations

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_code_block


async def evo_draft(
    requirement: str,
    *,
    llm: LLMCaller,
    constraints: list[str] | None = None,
) -> str:
    """Draft 算子: 需求 → 初版代码。

    Composes oskill: [extract_code_block]
    """
    hard_rules = ""
    if constraints:
        hard_rules = "Hard constraints (MUST follow):\n" + "\n".join(f"- {c}" for c in constraints)
    prompt = (
        f"Write a complete, runnable solution for the following requirement.\n"
        f"Return ONLY the code in a ```python fenced block.\n\n"
        f"Requirement:\n{requirement}\n\n"
        f"{hard_rules}"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return extract_code_block(str(response.get("content", "")))
