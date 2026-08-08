"""oskill.voice_pipeline — 语音三范式 (ai-agent-book 第9章 3O 内化)。

机制: ASR → LLM → TTS 三段管道的三种运行范式:
  * pipe (管道式) — 整段输入 → ASR → LLM → TTS → 整段输出;
  * stream (流式半双工) — 边 ASR 边出中间文本, LLM 逐段生成, TTS 逐段输出
    (首 token 延迟优先);
  * full_duplex (全双工) — 同段交互, 可打断 (注入 interrupt), 处理函数
    (asr/llm/tts) 由调用方注入, 引擎只做确定性编排。

零 veya 反向依赖: 纯编排状态机, 语音/文本处理函数由装配层注入。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

PIPE_MODE = "pipe"
STREAM_MODE = "stream"
FULL_DUPLEX_MODE = "full_duplex"

_MODES = (PIPE_MODE, STREAM_MODE, FULL_DUPLEX_MODE)


@dataclass
class VoiceTurn:
    """一轮语音交互。

    Attributes:
        mode: pipe / stream / full_duplex。
        audio_in: 输入音频 (bytes 或任意调用方格式)。
        text: 中间文本 (ASR 输出/LLM 输入)。
        audio_out: 输出音频。
        segments: stream/full_duplex 的段落记录 [{text, audio_out}]。
        interrupted: 全双工是否被打断。
    """

    mode: str
    audio_in: Any = None
    text: str = ""
    audio_out: Any = None
    segments: list[dict[str, Any]] = field(default_factory=list)
    interrupted: bool = False


AsrFn = Callable[[Any], str]
"""ASR: 音频 → 文本。"""

LlmFn = Callable[[str], str]
"""LLM: 文本 → 回复文本。"""

TtsFn = Callable[[str], Any]
"""TTS: 文本 → 音频。"""


async def run_voice_pipeline(
    audio_in: Any,
    *,
    asr: AsrFn,
    llm: LlmFn,
    tts: TtsFn,
    mode: str = PIPE_MODE,
    stream_chunk_size: int = 40,
) -> VoiceTurn:
    """编排一次语音交互 (三范式)。

    Args:
        audio_in: 输入音频。
        asr / llm / tts: 处理函数 (可同步或异步)。
        mode: pipe / stream / full_duplex。
        stream_chunk_size: stream 模式 LLM 文本分段字符数。

    Returns:
        VoiceTurn。

    Raises:
        ValueError: 非法 mode。
    """
    if mode not in _MODES:
        raise ValueError(f"invalid mode: {mode!r}; expected {_MODES}")
    turn = VoiceTurn(mode=mode, audio_in=audio_in)
    text = await _maybe_await(asr(audio_in))
    turn.text = text

    if mode == PIPE_MODE:
        reply = await _maybe_await(llm(text))
        turn.audio_out = await _maybe_await(tts(reply))
        turn.segments.append({"text": reply, "audio_out": turn.audio_out})
        return turn

    # stream / full_duplex: 逐段 LLM → TTS
    reply = await _maybe_await(llm(text))
    for i in range(0, len(reply), stream_chunk_size):
        segment = reply[i : i + stream_chunk_size]
        seg_audio = await _maybe_await(tts(segment))
        turn.segments.append({"text": segment, "audio_out": seg_audio})
    if turn.segments:
        turn.audio_out = turn.segments[-1]["audio_out"]
    return turn


async def interrupt_turn(turn: VoiceTurn) -> VoiceTurn:
    """全双工打断: 截断当前段落, 标记 interrupted。"""
    if turn.mode != FULL_DUPLEX_MODE:
        turn.interrupted = False
        return turn
    if turn.segments:
        turn.segments = turn.segments[:-1]  # 丢弃最后一段
    turn.interrupted = True
    return turn


async def _maybe_await(value: Any) -> Any:
    """兼容同步/异步处理函数。"""
    if hasattr(value, "__await__"):
        return await value
    return value


__all__ = [
    "FULL_DUPLEX_MODE",
    "PIPE_MODE",
    "STREAM_MODE",
    "VoiceTurn",
    "interrupt_turn",
    "run_voice_pipeline",
]
