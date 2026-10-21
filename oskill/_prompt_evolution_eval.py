"""oskill.prompt_evolution_eval — SOUL / Prompt 配置自调优与效能评估算法.

纯算法 + LLM 评估：对一组 prompt 变体（system prompt / SOUL 配置），用
注入的 judge caller 逐样本打分，输出排名与胜出变体建议。stateless。

Example:
    >>> r = await prompt_evolution_eval(
    ...     {"v1": "你是助手", "v2": "你是严谨的助手"},
    ...     samples=["1+1=?", "解释 3O"],
    ...     judge=my_caller,
    ... )
    >>> r["best_variant"] in ("v1", "v2")
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class JudgeCaller(Protocol):
    """LLM 评估器协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def prompt_evolution_eval(
    variants: dict[str, str],
    *,
    samples: list[str],
    judge: JudgeCaller,
    criteria: str = "回答的正确性、完整性、简洁性（0-10 打分，只输出数字）",
) -> dict[str, Any]:
    """对 prompt 变体做交叉评估并排序。

    Args:
        variants: {变体名: prompt 文本}，至少 2 个变体。
        samples: 评估样本（任务输入）。
        judge: LLM 评估器（注入）。
        criteria: 评分标准说明。

    Returns:
        {
            "best_variant": str,
            "scores": {variant: {avg: float, per_sample: [float]}},
            "ranked": [str],          # 按 avg 降序
            "samples": int,
        }

    Raises:
        OskillError: variants < 2 或 samples 为空。
        LLMOskillError: 评估调用失败。
    """
    if len(variants) < 2:
        raise OskillError("prompt_evolution_eval: need >= 2 variants")
    if not samples:
        raise OskillError("prompt_evolution_eval: samples must not be empty")

    scores: dict[str, dict[str, Any]] = {}
    for name, prompt in variants.items():
        per_sample: list[float] = []
        for sample in samples:
            per_sample.append(await _score_one(prompt, sample, criteria=criteria, judge=judge))
        avg = round(sum(per_sample) / len(per_sample), 2) if per_sample else 0.0
        scores[name] = {"avg": avg, "per_sample": per_sample}

    ranked = sorted(scores, key=lambda n: scores[n]["avg"], reverse=True)
    return {
        "best_variant": ranked[0] if ranked else "",
        "scores": scores,
        "ranked": ranked,
        "samples": len(samples),
    }


async def _score_one(prompt: str, sample: str, *, criteria: str, judge: JudgeCaller) -> float:
    try:
        response = await judge(
            messages=[
                {"role": "system", "content": f"你是 prompt 评估器。{criteria}"},
                {
                    "role": "user",
                    "content": (
                        f"Prompt:\n{prompt}\n\n任务输入:\n{sample}\n\n只输出一个 0-10 的数字。"
                    ),
                },
            ],
            tools=None,
            max_tokens=16,
        )
    except Exception as exc:
        raise LLMOskillError("prompt_evolution_eval: judge call failed", cause=exc) from exc

    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    try:
        return max(0.0, min(10.0, float(str(content).strip())))
    except ValueError:
        return 0.0
