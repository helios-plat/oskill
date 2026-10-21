"""SOUL configuration evolution.

The original four-argument proposal API remains available. Supplying
``feedback``/``caller`` selects the Veya scored-evolution API.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class SoulCaller(Protocol):
    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


def soul_self_evolution(
    agent_name_or_soul: str,
    current_soul: str | None = None,
    current_config: dict[str, Any] | None = None,
    execution_feedback: str | None = None,
    llm_caller: SoulCaller | None = None,
    context: dict[str, Any] | None = None,
    *,
    feedback: str = "",
    caller: SoulCaller | None = None,
    min_gain: float = 0.1,
    agent_name: str = "",
    **kwargs: Any,
) -> Any:
    """Return the legacy proposal result or the scored-evolution coroutine."""
    is_new_api = caller is not None or bool(feedback)
    if is_new_api:
        return _soul_self_evolution_async(
            agent_name_or_soul,
            feedback=feedback or execution_feedback or "",
            caller=caller or llm_caller,
            min_gain=min_gain,
        )
    return _legacy_soul_self_evolution(
        agent_name_or_soul,
        current_soul or "",
        current_config or {},
        execution_feedback or "",
        llm_caller,
        context,
    )


def _legacy_soul_self_evolution(
    agent_name: str,
    current_soul: str,
    current_config: dict[str, Any],
    execution_feedback: str,
    llm_caller: Callable | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    ctx = context or {}
    if llm_caller is not None and ctx.get("use_llm", True):
        try:
            import json

            prompt = (
                f"You are {agent_name} evaluating your own performance. "
                f"Current SOUL.md: {current_soul[:2000]}\n"
                f"Current config: {json.dumps(current_config, ensure_ascii=False)[:1000]}\n"
                f"Execution feedback: {execution_feedback[:2000]}\n\n"
                "Propose specific, minimal changes to SOUL.md and config. "
                'Output JSON: {"soul_changes": [{"line": "old", "new": "new", '
                '"reason": "..."}], "config_changes": {"key": "new_value"}}'
            )
            out = llm_caller(
                messages=[{"role": "user", "content": prompt}],
                tools=None,
                config=ctx,
            )
            raw = out.get("content") or "" if isinstance(out, dict) else str(out)
            match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            parsed = (
                json.loads(match.group(1))
                if match
                else (json.loads(raw) if raw.strip().startswith("{") else {})
            )
        except Exception:
            parsed = {}

        return {
            "proposed_soul": _apply_soul_changes(current_soul, parsed.get("soul_changes", [])),
            "proposed_config": {**current_config, **parsed.get("config_changes", {})},
            "changes": [
                {
                    "field": "soul",
                    "old": change.get("line", "")[:80],
                    "new": change.get("new", "")[:80],
                    "reason": change.get("reason", ""),
                }
                for change in parsed.get("soul_changes", [])
            ]
            + [
                {
                    "field": key,
                    "old": str(current_config.get(key, "")),
                    "new": str(value),
                    "reason": "performance feedback",
                }
                for key, value in parsed.get("config_changes", {}).items()
            ],
            "status": "analyzed",
        }

    new_soul = current_soul
    if execution_feedback:
        new_soul += f"\n\n<!-- Self-evaluation ({_now()}): {execution_feedback[:300]} -->\n"
    return {
        "proposed_soul": new_soul,
        "proposed_config": current_config,
        "changes": [
            {
                "field": "soul",
                "old": "",
                "new": "evaluation annotation appended",
                "reason": execution_feedback[:80],
            }
        ],
        "status": "analyzed",
    }


def _apply_soul_changes(soul: str, changes: list[dict[str, Any]]) -> str:
    result = soul
    for change in changes:
        old = change.get("line", "")
        new = change.get("new", "")
        if old and old in result:
            result = result.replace(old, new, 1)
    return result


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%d %H:%M:%S")


async def _soul_self_evolution_async(
    current_soul: str,
    *,
    feedback: str,
    caller: SoulCaller | None,
    min_gain: float,
) -> dict[str, Any]:
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
    return _response_text(response).strip()


async def _score_both(
    current: str,
    candidate: str,
    feedback: str,
    caller: SoulCaller,
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
        match = re.search(r"\d+(\.\d+)?", _response_text(response))
        scores.append(max(0.0, min(10.0, float(match.group(0)))) if match else 0.0)
    reason = "candidate scored higher" if scores[1] > scores[0] else "no gain"
    return scores[0], scores[1], reason


def _response_text(response: dict[str, Any]) -> str:
    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return str(content)


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
