"""3O 范式内化 — OpenRSI Improve 算子 (oskill).

输入当前代码 + 性能/测试反馈, 输出重构代码。LLM 经协议注入, 无状态。
"""

from __future__ import annotations

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_code_block


async def evo_improve(
    code: str,
    *,
    feedback: str,
    llm: LLMCaller,
) -> str:
    """Improve 算子: 代码 + 反馈 → 重构代码。

    Composes oskill: [extract_code_block]
    """
    prompt = (
        f"Improve the following code based on the feedback. Keep the public API stable.\n"
        f"Return ONLY the improved code in a ```python fenced block.\n\n"
        f"Feedback:\n{feedback}\n\n"
        f"Current code:\n```python\n{code}\n```"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return extract_code_block(str(response.get("content", "")))
