"""3O 范式内化 — OpenRSI Debug 算子 (oskill).

输入当前代码 + 沙盒捕获的 stderr/报错行, 输出修复补丁。
LLM 经协议注入, 无状态。
"""

from __future__ import annotations

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_code_block


async def evo_debug(
    code: str,
    *,
    error_trace: str,
    llm: LLMCaller,
    constraints: list[str] | None = None,
) -> str:
    """Debug 算子: 代码 + 错误轨迹 → 修复后的完整代码。

    Composes oskill: [extract_code_block]
    """
    hard_rules = ""
    if constraints:
        hard_rules = "Hard constraints (MUST follow):\n" + "\n".join(f"- {c}" for c in constraints)
    prompt = (
        f"Fix the bug in the code below using the error trace. "
        f"Return ONLY the fixed full code in a ```python fenced block.\n\n"
        f"Error trace:\n{error_trace}\n\n"
        f"Current code:\n```python\n{code}\n```\n\n"
        f"{hard_rules}"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return extract_code_block(str(response.get("content", "")))
