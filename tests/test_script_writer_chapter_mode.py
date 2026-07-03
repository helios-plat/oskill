"""Tests for oskill.script_writer chapter_mode extension (M7 — ≥6 tests)."""

from __future__ import annotations

import json

from oskill._schemas import ChapterScript, Script
from oskill.script_writer import script_writer


def _make_legacy_llm() -> object:
    """LLM returning a valid legacy Script JSON."""

    async def _llm(messages: list, **_: object) -> dict:
        return {
            "content": json.dumps(
                {
                    "title": "Test Script",
                    "description": "A test",
                    "scenes": [
                        {
                            "index": 0,
                            "narration": "intro",
                            "duration_s": 10.0,
                            "visual_description": "sky",
                        },
                    ],
                    "estimated_duration_s": 10.0,
                }
            )
        }

    return _llm


def _make_chapter_llm(num_chapters: int = 2, num_chars: int = 2) -> object:
    """LLM returning a valid ChapterScript JSON."""

    async def _llm(messages: list, **_: object) -> dict:
        chapters = [
            {
                "chapter_id": f"ch_{i}",
                "title": f"Chapter {i + 1}",
                "scenes": [{"index": 0, "description": "scene"}],
                "dialogues": [
                    {"speaker_id": f"speaker_{j}", "text": f"line {j}"} for j in range(num_chars)
                ],
            }
            for i in range(num_chapters)
        ]
        return {
            "content": json.dumps(
                {
                    "chapters": chapters,
                    "total_duration_s": 180.0,
                    "characters": [f"speaker_{j}" for j in range(num_chars)],
                }
            )
        }

    return _llm


class TestScriptWriterChapterMode:
    async def test_chapter_mode_false_legacy_behaviour(self) -> None:
        """chapter_mode=False → returns Script (backward compatible)."""
        result = await script_writer(topic="cats", llm=_make_legacy_llm(), chapter_mode=False)
        assert isinstance(result, Script)
        assert result.title == "Test Script"

    async def test_chapter_mode_true_1_to_5_min(self) -> None:
        """chapter_mode=True, <5min → ChapterScript with few chapters."""
        result = await script_writer(
            topic="short video",
            target_duration_s=120.0,
            llm=_make_chapter_llm(num_chapters=2),
            chapter_mode=True,
        )
        assert isinstance(result, ChapterScript)
        assert len(result.chapters) == 2

    async def test_chapter_mode_true_5_to_15_min(self) -> None:
        """chapter_mode=True, 5–15min → ChapterScript (mainstream)."""
        result = await script_writer(
            topic="medium video",
            target_duration_s=600.0,
            llm=_make_chapter_llm(num_chapters=4),
            chapter_mode=True,
        )
        assert isinstance(result, ChapterScript)
        assert len(result.chapters) >= 1

    async def test_chapter_mode_true_45_plus_min(self) -> None:
        """chapter_mode=True, 45+min → ChapterScript with many chapters."""
        result = await script_writer(
            topic="documentary",
            target_duration_s=3600.0,
            llm=_make_chapter_llm(num_chapters=16),
            chapter_mode=True,
        )
        assert isinstance(result, ChapterScript)
        assert len(result.chapters) == 16

    async def test_num_characters_4_speaker_lines(self) -> None:
        """num_characters=4 → 4 distinct speakers in dialogues."""
        result = await script_writer(
            topic="multi-role drama",
            target_duration_s=300.0,
            llm=_make_chapter_llm(num_chapters=1, num_chars=4),
            chapter_mode=True,
            num_characters=4,
        )
        assert isinstance(result, ChapterScript)
        speakers = {line.speaker_id for ch in result.chapters for line in ch.dialogues}
        assert len(speakers) == 4

    async def test_chinese_and_english_language(self) -> None:
        """chapter_mode accepts language param without error."""
        for lang in ("zh", "en"):
            result = await script_writer(
                topic="language test",
                target_duration_s=120.0,
                llm=_make_chapter_llm(num_chapters=2),
                chapter_mode=True,
                language=lang,
            )
            assert isinstance(result, ChapterScript)
