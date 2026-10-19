"""oskill.voice_interruption_handler — 语音打断处理.

判断用户话语是否打断当前 Agent 回合：LLM（注入）语义判定优先，
关键词启发式兜底；输出打断决策与建议动作（pause/yield/continue）。

stateless。

Example:
    >>> r = await voice_interruption_handler("停一下，我改主意了", current_turn="正在执行任务...")
    >>> r["interrupts"] in (True, False)
    True
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from oskill._exceptions import OskillError

INTERRUPT_KEYWORDS = (
    "停",
    "打断",
    "等一下",
    "别",
    "不要",
    "改主意",
    "听我说",
    "先别",
    "stop",
    "wait",
    "hold on",
    "pause",
    "cancel",
)

InterruptAction = Literal["pause", "yield", "continue"]


@runtime_checkable
class InterruptCaller(Protocol):
    """LLM 调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def voice_interruption_handler(
    utterance: str,
    *,
    current_turn: str,
    caller: InterruptCaller | None = None,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """判定语音打断。

    Args:
        utterance: 用户话语（转写文本）。
        current_turn: 当前 Agent 回合内容。
        caller: LLM（可选，注入）。
        threshold: LLM 置信度阈值。

    Returns:
        {"interrupts": bool, "confidence": float, "action": str,
         "method": "llm"|"heuristic"}

    Raises:
        OskillError: utterance 为空。
    """
    if not utterance or not utterance.strip():
        raise OskillError("voice_interruption_handler: utterance must not be empty")

    if caller is not None:
        try:
            return await _llm_judge(utterance, current_turn, caller, threshold)
        except Exception:  # noqa: BLE001 - LLM 失败回退启发式
            pass

    return _heuristic_judge(utterance)


def _heuristic_judge(utterance: str) -> dict[str, Any]:
    lowered = utterance.lower()
    hits = sum(1 for kw in INTERRUPT_KEYWORDS if kw in lowered)
    interrupts = hits > 0
    confidence = min(0.95, 0.4 + 0.2 * hits) if interrupts else 0.1
    action: InterruptAction = "pause" if interrupts else "continue"
    return {
        "interrupts": interrupts,
        "confidence": round(confidence, 2),
        "action": action,
        "method": "heuristic",
    }


async def _llm_judge(
    utterance: str,
    current_turn: str,
    caller: InterruptCaller,
    threshold: float,
) -> dict[str, Any]:
    prompt = (
        "你是语音打断判定器。判断用户话语是否打断了助手当前正在进行的回合"
        "（命令助手停止/更改方向/提出新需求优先于当前回合）。\n"
        f"当前回合: {current_turn[:800]}\n用户话语: {utterance}\n\n"
        '只输出 JSON：{"interrupts": true/false, "confidence": 0.0-1.0}'
    )
    try:
        response = await caller(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            max_tokens=64,
        )
    except Exception as exc:
        raise OskillError(f"voice_interruption_handler: LLM failed: {exc}") from exc

    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    import json
    import re

    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(str(content))
    except json.JSONDecodeError:
        m = re.search(r'"(interrupts)"\s*:\s*(true|false)', str(content))
        if m:
            parsed = {"interrupts": m.group(2) == "true"}
    interrupts = bool(parsed.get("interrupts", False))
    confidence = float(parsed.get("confidence", 0.9 if interrupts else 0.1))
    action: InterruptAction = (
        "pause" if interrupts and confidence >= threshold else "yield" if interrupts else "continue"
    )
    return {
        "interrupts": interrupts,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "action": action,
        "method": "llm",
    }
