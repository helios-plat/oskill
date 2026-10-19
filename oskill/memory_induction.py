"""3O 范式内化 — ReasoningBank 经验归纳技能 (oskill).

后置反思: 将 MCTS 树中失败分支与成功分支同时喂给 LLM,
抽象出因果规则 (防坑点)。LLM 经协议注入, 无状态 (落盘由上层完成)。
"""

from __future__ import annotations

import json
from typing import Any

from oskill.protocols import LLMCaller
from oskill.pure_parsers import extract_json_block


async def induce_experience(
    failed_trajectory: dict[str, Any],
    *,
    successful_trajectory: dict[str, Any],
    llm: LLMCaller,
) -> dict[str, Any]:
    """归纳经验三元组: {context_description, failed_attempt, successful_strategy}。

    Composes oskill: [extract_json_block]
    """
    prompt = (
        "Study the failed and successful evolution trajectories below. "
        "Abstract the causal rule: why did plan A fail while plan B succeeded? "
        "Return a JSON block with keys: "
        "'context_description', 'failed_attempt' (object with 'action' and 'reason'), "
        "'successful_strategy' (object with 'action' and 'reason').\n\n"
        f"FAILED trajectory:\n{json.dumps(failed_trajectory, ensure_ascii=False, indent=1)}\n\n"
        f"SUCCESSFUL trajectory:\n{json.dumps(successful_trajectory, ensure_ascii=False, indent=1)}"
    )
    response = await llm(messages=[{"role": "user", "content": prompt}])
    return extract_json_block(str(response.get("content", "")))
