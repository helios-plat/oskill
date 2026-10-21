"""oskill.soul_self_evolution — SOUL 自进化.

基于反馈（评估/教训）经 LLM（注入）演化 SOUL 配置，带收益门槛与
回归护栏（候选分不低于当前分才采纳）。stateless。

Example:
    >>> r = await soul_self_evolution(current_soul, feedback="回答太啰嗦", caller=llm)
    >>> r["evolved"] in (True, False)
    True
"""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class SoulCaller(Protocol):
    """LLM 调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def soul_self_evolution(
    current_soul: str,
    *,
    feedback: str,
    caller: SoulCaller,
    min_gain: float = 0.1,
) -> dict[str, Any]:
    """演化 SOUL 配置。

    Args:
        current_soul: 当前 SOUL 配置文本。
        feedback: 反馈（评估结果/失败教训/用户偏好）。
        caller: LLM（注入）。
        min_gain: 采纳所需的最低分数增益。

    Returns:
        {"evolved": bool, "candidate": str, "diff": str,
         "current_score": float, "candidate_score": float,
         "reason": str}

    Raises:
        OskillError: current_soul / feedback 为空。
        LLMOskillError: LLM 调用失败。
    """
    if not current_soul or not current_soul.strip():
        raise OskillError("soul_self_evolution: current_soul must not be empty")
    if not feedback.strip():
        raise OskillError("soul_self_evolution: feedback must not be empty")
    if caller is None:
        raise OskillError("soul_self_evolution: caller must be injected")

    try:
        candidate = await _evolve(current_soul, feedback, caller)
        current_score, candidate_score, reason = await _score_both(
            current_soul, candidate, feedback, caller
        )
    except LLMOskillError:
        raise
    except Exception as exc:
        raise LLMOskillError(f"soul_self_evolution failed: {exc}") from exc

    adopted = (
        candidate_score >= current_score + min_gain and candidate.strip() != current_soul.strip()
    )
    return {
        "evolved": adopted,
        "candidate": candidate if adopted else current_soul,
        "diff": _diff(current_soul, candidate),
        "current_score": current_score,
        "candidate_score": candidate_score,
        "reason": reason,
    }


async def _evolve(current: str, feedback: str, caller: SoulCaller) -> str:
    response = await caller(
        messages=[
            {
                "role": "user",
                "content": (
                    "你是 SOUL 配置进化器。根据反馈改进以下 Agent 人格/行为配置，"
                    "保留原有优点，只做必要修改，输出改进后的完整配置文本：\n\n"
                    f"当前配置:\n{current[:4000]}\n\n反馈:\n{feedback[:2000]}"
                ),
            }
        ],
        tools=None,
        max_tokens=2048,
    )
    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(content).strip()


async def _score_both(
    current: str, candidate: str, feedback: str, caller: SoulCaller
) -> tuple[float, float, str]:
    scores: list[float] = []
    for label, text in (("当前", current), ("候选", candidate)):
        response = await caller(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"评估以下 Agent 配置对反馈「{feedback[:500]}」的适配度，"
                        f"0-10 分，只输出数字：\n\n[{label}配置]\n{text[:3000]}"
                    ),
                }
            ],
            tools=None,
            max_tokens=16,
        )
        content = response.get("content", "")
        if isinstance(content, list):
            content = "".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        m = re.search(r"\d+(\.\d+)?", str(content))
        scores.append(max(0.0, min(10.0, float(m.group(0)))) if m else 0.0)
    reason = "candidate scored higher" if scores[1] > scores[0] else "no gain"
    return scores[0], scores[1], reason


def _diff(current: str, candidate: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            fromfile="current",
            tofile="candidate",
        )
    )[:2000]
