"""oskill.counterfactual_reasoning — 反事实归因推演与替代路径模拟算法.

基于因果 DAG 与 LLM（注入）计算反事实问答：
"如果 step X 采取了动作 Y，任务是否还会失败？" stateless。

Example:
    >>> r = counterfactual_reasoning(graph, "step_3_action", llm_caller=llm)
    >>> "would_succeed" in r
    True
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class LLMCallerProtocol(Protocol):
    """LLM 调用协议（prompt 风格注入面）。"""

    def __call__(self, prompt: str, *, temperature: float = 0.0) -> str: ...


def counterfactual_reasoning(
    causal_graph: dict[str, Any],
    failed_step_id: str,
    *,
    llm_caller: LLMCallerProtocol,
    alternative_action: str = "",
) -> dict[str, Any]:
    """反事实推演。

    Args:
        causal_graph: 因果 DAG（oprim.causal_graph_build 的 graph 结构）。
        failed_step_id: 失败步骤 ID。
        llm_caller: LLM 调用器（注入）。
        alternative_action: 替代动作（干预变量）。

    Returns:
        {"status": "success", "would_succeed": bool, "root_cause": str,
         "explanation": str}
        解析失败时 status="failed" + error（不 raise）。

    Raises:
        OskillError: causal_graph 为空 / llm_caller 未注入。
    """
    if not causal_graph:
        raise OskillError("counterfactual_reasoning: causal_graph must not be empty")
    if not failed_step_id:
        raise OskillError("counterfactual_reasoning: failed_step_id must not be empty")
    if llm_caller is None:
        raise OskillError("counterfactual_reasoning: llm_caller must be injected")

    prompt = (
        "Given the causal DAG of an Agent execution:\n"
        f"{json.dumps(causal_graph, ensure_ascii=False)[:6000]}\n"
        f"Target Failed Step: {failed_step_id}\n"
        f"Counterfactual Intervention (Alternative Action): {alternative_action}\n"
        "Perform counterfactual deduction and reply in JSON:\n"
        '{"would_succeed": true/false, "root_cause": "...", "explanation": "..."}'
    )
    try:
        raw_output = llm_caller(prompt, temperature=0.1)
    except Exception as exc:
        raise OskillError(f"counterfactual_reasoning: LLM call failed: {exc}") from exc

    try:
        res = json.loads(raw_output if isinstance(raw_output, str) else str(raw_output))
    except Exception as exc:
        return {
            "status": "failed",
            "error": f"invalid JSON from LLM: {exc}",
            "would_succeed": False,
            "root_cause": "Unknown",
            "explanation": "",
        }

    return {
        "status": "success",
        "would_succeed": bool(res.get("would_succeed", False)),
        "root_cause": str(res.get("root_cause", "Unknown")),
        "explanation": str(res.get("explanation", "")),
    }
