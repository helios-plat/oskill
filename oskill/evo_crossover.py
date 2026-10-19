"""3O 范式内化 — OpenRSI Crossover 算子 (oskill).

输入方案 A 与方案 B, 提取两者优点进行混合重构。LLM 经协议注入, 无状态。
"""

from __future__ import annotations

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_code_block


async def evo_crossover(
    code_a: str,
    *,
    code_b: str,
    llm: LLMCaller,
) -> str:
    """Crossover 算子: 方案 A ⊕ 方案 B → 混合方案。

    Composes oskill: [extract_code_block]
    """
    prompt = (
        f"Two solutions exist for the same problem. Merge the BEST parts of both "
        f"into a single superior solution. Return ONLY the merged code in a "
        f"```python fenced block.\n\n"
        f"Solution A:\n```python\n{code_a}\n```\n\n"
        f"Solution B:\n```python\n{code_b}\n```"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return extract_code_block(str(response.get("content", "")))
