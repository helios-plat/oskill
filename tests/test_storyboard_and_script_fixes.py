"""B7/B8 回迁修复:storyboard model_dump 兼容 dict scenes + script_writer 旁白量目标。"""

from __future__ import annotations

import json
from typing import Any

from oskill._schemas import Chapter
from oskill.script_writer import _narration_words_target, script_writer
from oskill.storyboard_planner import storyboard_planner


def _capturing_llm(sink: dict, response: dict) -> Any:
    async def _llm(*, messages: list, **_: Any) -> dict:
        sink["messages"] = messages
        return {"content": json.dumps(response)}

    return _llm


_VALID_SHOTS = {
    "shots": [
        {
            "shot_id": "s0",
            "scene_index": 0,
            "visual_description": "v",
            "narration": "n",
            "duration_s": 5.0,
        }
    ]
}


class TestB7StoryboardDictScenes:
    async def test_accepts_chapter_list_dict_scenes(self) -> None:
        """B7: Chapter.scenes 是 list[dict] —— storyboard_planner 不再 AttributeError。"""
        sink: dict = {}
        chapter = Chapter(
            chapter_id="c0",
            title="t",
            scenes=[{"index": 0, "narration": "hi"}],
            dialogues=[],
        )
        board = await storyboard_planner(script=chapter, llm=_capturing_llm(sink, _VALID_SHOTS))
        assert len(board.shots) == 1
        # 传给 LLM 的 user content 就是原始 dict(未被 model_dump 破坏)
        user_content = sink["messages"][1]["content"]
        assert json.loads(user_content) == [{"index": 0, "narration": "hi"}]

    async def test_accepts_model_scenes_via_model_dump(self) -> None:
        """含 model_dump 的 scene 仍走 model_dump 分支。"""
        sink: dict = {}

        class _Scene:
            def model_dump(self) -> dict:
                return {"kind": "model"}

        class _Script:
            scenes = [_Scene()]

        board = await storyboard_planner(script=_Script(), llm=_capturing_llm(sink, _VALID_SHOTS))
        assert len(board.shots) == 1
        assert json.loads(sink["messages"][1]["content"]) == [{"kind": "model"}]


class TestB8NarrationVolume:
    def test_words_target_math(self) -> None:
        assert _narration_words_target(180) == 450  # 3min × 150wpm
        assert _narration_words_target(60) == 150
        assert _narration_words_target(0) == 20  # floor

    async def test_legacy_prompt_includes_word_target(self) -> None:
        sink: dict = {}
        resp = {
            "title": "t",
            "description": "d",
            "scenes": [
                {"index": 0, "narration": "n", "duration_s": 10.0, "visual_description": "v"}
            ],
            "estimated_duration_s": 10.0,
        }
        await script_writer(
            topic="cats", target_duration_s=180, llm=_capturing_llm(sink, resp), chapter_mode=False
        )
        system = sink["messages"][0]["content"]
        assert "450 words" in system
        assert "do not under-write" in system

    async def test_chapter_prompt_includes_word_target(self) -> None:
        sink: dict = {}
        resp = {
            "chapters": [
                {"chapter_id": "ch_0", "title": "c", "scenes": [{"index": 0}], "dialogues": []}
            ],
            "total_duration_s": 180.0,
            "characters": ["speaker_0"],
        }
        await script_writer(
            topic="cats", target_duration_s=180, llm=_capturing_llm(sink, resp), chapter_mode=True
        )
        system = sink["messages"][0]["content"]
        assert "450 words" in system
        assert "per chapter" in system

    async def test_template_prompt_not_augmented(self) -> None:
        """显式 template_prompt 时不注入(尊重调用方完整覆盖)。"""
        sink: dict = {}
        resp = {"title": "t", "description": "d", "scenes": [], "estimated_duration_s": 0.0}
        await script_writer(
            topic="x",
            target_duration_s=180,
            llm=_capturing_llm(sink, resp),
            template_prompt="ONLY THIS",
            chapter_mode=False,
        )
        assert sink["messages"][0]["content"] == "ONLY THIS"
