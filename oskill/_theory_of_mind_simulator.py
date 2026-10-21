"""oskill.theory_of_mind_simulator — 基于 ToM 心智矩阵的人类反应预测与表达博弈.

模拟评估消息在目标用户心智下的接受度，自动优化表达策略。stateless，
LLM Protocol 注入。

Example:
    >>> r = theory_of_mind_simulator("消息", user_tom_profile={"risk_aversion": "high"}, llm_caller=llm)
    >>> r["status"] in ("success", "fallback")
    True
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class LLMCallerProtocol(Protocol):
    """LLM 调用协议。"""

    def __call__(self, prompt: str, *, temperature: float = 0.2) -> str: ...


def theory_of_mind_simulator(
    proposed_message: str,
    user_tom_profile: dict[str, Any],
    *,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """模拟用户反应并优化消息。

    Args:
        proposed_message: 拟发送消息。
        user_tom_profile: 目标用户 ToM 画像（tom_profile_extract 产出）。
        llm_caller: LLM 调用器（注入）。

    Returns:
        {"status": "success"|"fallback", "optimized_message": str,
         "reaction": str|None}

    Raises:
        OskillError: proposed_message 为空 / llm_caller 未注入。
    """
    if not proposed_message or not proposed_message.strip():
        raise OskillError("theory_of_mind_simulator: proposed_message must not be empty")
    if llm_caller is None:
        raise OskillError("theory_of_mind_simulator: llm_caller must be injected")

    prompt = (
        f"Original Message: {proposed_message}\n"
        f"Target User ToM Profile: {json.dumps(user_tom_profile, ensure_ascii=False)[:2000]}\n"
        "Predict user reaction and optimize tone. Reply JSON: {\n"
        '  "predicted_reaction": "positive/neutral/resistant",\n'
        '  "optimized_message": "..."\n'
        "}"
    )
    try:
        raw = llm_caller(prompt, temperature=0.2)
    except Exception as exc:
        raise OskillError(f"theory_of_mind_simulator: LLM call failed: {exc}") from exc

    try:
        res = json.loads(raw if isinstance(raw, str) else str(raw))
    except Exception:  # noqa: BLE001 - 回退原消息
        return {
            "status": "fallback",
            "optimized_message": proposed_message,
            "reaction": "unknown",
        }

    return {
        "status": "success",
        "optimized_message": str(res.get("optimized_message") or proposed_message),
        "reaction": res.get("predicted_reaction"),
    }
