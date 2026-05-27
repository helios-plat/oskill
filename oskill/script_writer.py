"""oskill.script_writer — LLM-based video script generation.

Example:
    >>> from oskill.script_writer import script_writer
    >>> script = await script_writer(topic="AI history", target_duration_s=180, llm=llm)

Raises:
    ScriptWriterError: Script generation failed.
"""

from __future__ import annotations

import json
from typing import Any

from oskill._schemas import Script, SubjectRef


class ScriptWriterError(Exception):
    """Script writing failed."""


async def script_writer(
    *,
    topic: str,
    target_duration_s: float,
    llm: Any,
    template_prompt: str | None = None,
    language: str = "zh",
    subjects: list[SubjectRef] | None = None,
) -> Script:
    """Generate a video script using LLM.

    Args:
        topic: Video topic/subject.
        target_duration_s: Target video duration in seconds.
        llm: LLMCaller protocol instance.
        template_prompt: Optional industry template prompt to inject.
        language: Output language code.
        subjects: Optional character/subject references. When provided, each
            subject's name and description are appended to the system prompt so
            the LLM writes the script around the listed characters. Default
            None — identical behaviour to all prior versions (backward compatible).

    Returns:
        Script Pydantic model with scenes.

    Raises:
        ScriptWriterError: On empty topic, LLM failure, or invalid response.

    Example:
        >>> script = await script_writer(topic="cats", target_duration_s=60, llm=llm)
        >>> from oskill._schemas import SubjectRef
        >>> script = await script_writer(
        ...     topic="cats", target_duration_s=60, llm=llm,
        ...     subjects=[SubjectRef(subject_id="c1", name="Whiskers", description="主角")],
        ... )
    """
    if not topic:
        raise ScriptWriterError("topic must not be empty")

    system = template_prompt or (
        f"You are a video script writer. Write in {language}. "
        f"Target duration: {target_duration_s}s. "
        "Return valid JSON with keys: title, description, scenes, estimated_duration_s. "
        "Each scene has: index, narration, duration_s, visual_description."
    )

    # P7-B4: inject character context when subjects provided
    if subjects:
        char_lines = "\n".join(
            f"{s.name}: {s.description}" if s.description else s.name for s in subjects
        )
        system = system + f"\n以下角色将出现在视频中:\n{char_lines}"

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Write a video script about: {topic}"},
    ]

    result = llm(messages=messages)
    content = result.get("content", "")

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ScriptWriterError(f"LLM returned invalid JSON: {content[:200]}") from exc

    try:
        return Script.model_validate(data)
    except Exception as exc:
        raise ScriptWriterError(f"Script validation failed: {exc}") from exc
