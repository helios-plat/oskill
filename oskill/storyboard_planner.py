"""oskill.storyboard_planner — Break script into shots.

Example:
    >>> from oskill.storyboard_planner import storyboard_planner
    >>> board = await storyboard_planner(script=script, llm=llm)

Raises:
    StoryboardPlannerError: Planning failed.
"""

from __future__ import annotations

import json
from typing import Any

from oskill._schemas import Script, Storyboard


class StoryboardPlannerError(Exception):
    """Storyboard planning failed."""


async def storyboard_planner(
    *,
    script: Script,
    llm: Any,
    shots_per_scene_min: int = 3,
    shots_per_scene_max: int = 10,
) -> Storyboard:
    """Break a script into a shot-level storyboard.

    Args:
        script: Input Script model.
        llm: LLMCaller protocol instance.
        shots_per_scene_min: Minimum shots per scene.
        shots_per_scene_max: Maximum shots per scene.

    Returns:
        Storyboard with list of Shot objects.

    Raises:
        StoryboardPlannerError: On empty script, LLM failure, or invalid response.

    Example:
        >>> board = await storyboard_planner(script=script, llm=llm)
    """
    if not script.scenes:
        raise StoryboardPlannerError("script has no scenes")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": (
            f"Break each scene into {shots_per_scene_min}-{shots_per_scene_max} shots. "
            "Return JSON: {\"shots\": [{\"shot_id\", \"scene_index\", \"visual_description\", "
            "\"narration\", \"duration_s\", \"importance\", "
            "\"motion\": str|null (e.g. 'pan_left', 'zoom_in', 'static', or null)}]}"
        )},
        {"role": "user", "content": json.dumps(
            [s.model_dump() for s in script.scenes], ensure_ascii=False
        )},
    ]

    result = llm(messages=messages)
    content = result.get("content", "")

    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise StoryboardPlannerError(f"LLM returned invalid JSON: {content[:200]}") from exc

    try:
        return Storyboard.model_validate(data)
    except Exception as exc:
        raise StoryboardPlannerError(f"Storyboard validation failed: {exc}") from exc
