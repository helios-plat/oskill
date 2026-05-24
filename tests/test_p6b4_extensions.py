"""Tests for P6-B4: script_writer template_prompt + storyboard_planner motion field."""

from __future__ import annotations

import json
from typing import Any

import pytest

from oskill._schemas import Script


# ═══════════════════════════════════════════════════════════════════════════════
# script_writer — template_prompt extension
# ═══════════════════════════════════════════════════════════════════════════════

class TestScriptWriterTemplatePrompt:
    def _make_llm(self, title: str = "Test") -> Any:
        resp = json.dumps({
            "title": title, "description": "d",
            "scenes": [{"index": 0, "narration": "n", "duration_s": 5.0,
                        "visual_description": "v"}],
            "estimated_duration_s": 5.0,
        })
        return lambda **kw: {"content": resp}

    async def test_template_prompt_injected_as_system(self) -> None:
        from oskill.script_writer import script_writer

        calls: list[dict[str, Any]] = []

        def _llm(**kw: Any) -> dict[str, Any]:
            calls.append(kw)
            return {"content": json.dumps({
                "title": "T", "description": "d",
                "scenes": [{"index": 0, "narration": "n", "duration_s": 5.0,
                            "visual_description": "v"}],
                "estimated_duration_s": 5.0,
            })}

        await script_writer(
            topic="test", target_duration_s=60, llm=_llm,
            template_prompt="You are a quant finance expert. Generate {topic} content.",
        )
        system_msg = calls[0]["messages"][0]["content"]
        assert "quant finance expert" in system_msg

    async def test_template_prompt_none_uses_default(self) -> None:
        from oskill.script_writer import script_writer

        calls: list[dict[str, Any]] = []

        def _llm(**kw: Any) -> dict[str, Any]:
            calls.append(kw)
            return {"content": json.dumps({
                "title": "T", "description": "d",
                "scenes": [{"index": 0, "narration": "n", "duration_s": 5.0,
                            "visual_description": "v"}],
                "estimated_duration_s": 5.0,
            })}

        await script_writer(topic="test", target_duration_s=60, llm=_llm)
        system_msg = calls[0]["messages"][0]["content"]
        assert "video script writer" in system_msg

    async def test_different_templates_produce_different_prompts(self) -> None:
        from oskill.script_writer import script_writer

        calls: list[dict[str, Any]] = []

        def _llm(**kw: Any) -> dict[str, Any]:
            calls.append(kw)
            return {"content": json.dumps({
                "title": "T", "description": "d",
                "scenes": [{"index": 0, "narration": "n", "duration_s": 5.0,
                            "visual_description": "v"}],
                "estimated_duration_s": 5.0,
            })}

        await script_writer(
            topic="t", target_duration_s=60, llm=_llm,
            template_prompt="TEMPLATE_A",
        )
        await script_writer(
            topic="t", target_duration_s=60, llm=_llm,
            template_prompt="TEMPLATE_B",
        )
        assert calls[0]["messages"][0]["content"] == "TEMPLATE_A"
        assert calls[1]["messages"][0]["content"] == "TEMPLATE_B"

    async def test_backward_compat_no_template(self) -> None:
        from oskill.script_writer import script_writer

        result = await script_writer(
            topic="cats", target_duration_s=30, llm=self._make_llm(),
        )
        assert isinstance(result, Script)
        assert result.title == "Test"


# ═══════════════════════════════════════════════════════════════════════════════
# storyboard_planner — motion field extension
# ═══════════════════════════════════════════════════════════════════════════════

class TestStoryboardPlannerMotion:
    def _script(self) -> Script:
        return Script(
            title="T", description="d",
            scenes=[{"index": 0, "narration": "n", "duration_s": 5.0,
                     "visual_description": "v"}],
            estimated_duration_s=5.0,
        )

    async def test_motion_field_parsed(self) -> None:
        from oskill.storyboard_planner import storyboard_planner

        resp = json.dumps({"shots": [{
            "shot_id": "s1", "scene_index": 0, "visual_description": "v",
            "narration": "n", "duration_s": 3.0, "importance": 5,
            "motion": "pan_left",
        }]})
        board = await storyboard_planner(
            script=self._script(), llm=lambda **kw: {"content": resp},
        )
        assert board.shots[0].motion == "pan_left"

    async def test_motion_null_compat(self) -> None:
        from oskill.storyboard_planner import storyboard_planner

        resp = json.dumps({"shots": [{
            "shot_id": "s1", "scene_index": 0, "visual_description": "v",
            "narration": "n", "duration_s": 3.0, "importance": 5,
            "motion": None,
        }]})
        board = await storyboard_planner(
            script=self._script(), llm=lambda **kw: {"content": resp},
        )
        assert board.shots[0].motion is None

    async def test_motion_absent_defaults_none(self) -> None:
        from oskill.storyboard_planner import storyboard_planner

        resp = json.dumps({"shots": [{
            "shot_id": "s1", "scene_index": 0, "visual_description": "v",
            "narration": "n", "duration_s": 3.0, "importance": 5,
        }]})
        board = await storyboard_planner(
            script=self._script(), llm=lambda **kw: {"content": resp},
        )
        assert board.shots[0].motion is None

    async def test_prompt_mentions_motion(self) -> None:
        from oskill.storyboard_planner import storyboard_planner

        calls: list[dict[str, Any]] = []

        def _llm(**kw: Any) -> dict[str, Any]:
            calls.append(kw)
            return {"content": json.dumps({"shots": [{
                "shot_id": "s1", "scene_index": 0, "visual_description": "v",
                "narration": "n", "duration_s": 3.0, "importance": 5,
            }]})}

        await storyboard_planner(script=self._script(), llm=_llm)
        system = calls[0]["messages"][0]["content"]
        assert "motion" in system
