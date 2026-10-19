"""Tests for requirements_interview (mattpocock grilling 3O 内化)."""

from __future__ import annotations

import pytest

from oskill.requirements_interview import (
    InterviewQuestion,
    InterviewState,
    interview_frontier,
    interview_pending_facts,
    interview_progress,
    is_interview_complete,
    record_interview_answers,
    record_interview_facts,
    resolve_interview_answer,
)


def _state() -> InterviewState:
    """构造两轮设计树: q2/q3 依赖 q1。"""
    state = InterviewState()
    state.add_question(
        InterviewQuestion(
            id="q1",
            title="目标",
            body="做什么?",
            options=["A", "B"],
            recommended="A",
            facts_needed=["repo_lang"],
        )
    )
    state.add_question(
        InterviewQuestion(
            id="q2",
            title="深度",
            body="做多深?",
            depends_on=["q1"],
            recommended="浅",
        )
    )
    state.add_question(
        InterviewQuestion(
            id="q3",
            title="范围",
            body="范围?",
            depends_on=["q1"],
            recommended="核心",
        )
    )
    return state


class TestFrontier:
    def test_first_round_only_independent(self) -> None:
        state = _state()
        frontier = interview_frontier(state)
        assert [q.id for q in frontier] == ["q1"]

    def test_dependencies_unlock_next_round(self) -> None:
        state = _state()
        record_interview_answers(state, {"q1": "A"})
        frontier = interview_frontier(state)
        assert {q.id for q in frontier} == {"q2", "q3"}

    def test_complete_when_frontier_empty(self) -> None:
        state = _state()
        record_interview_answers(state, {"q1": "A"})
        record_interview_answers(state, {"q2": "浅", "q3": "核心"})
        assert is_interview_complete(state) is True
        assert interview_frontier(state) == []


class TestFacts:
    def test_pending_facts_collected_from_frontier(self) -> None:
        state = _state()
        assert interview_pending_facts(state) == ["repo_lang"]

    def test_facts_resolved(self) -> None:
        state = _state()
        record_interview_facts(state, {"repo_lang": "python"})
        assert interview_pending_facts(state) == []


class TestAnswers:
    def test_rejects_out_of_frontier(self) -> None:
        state = _state()
        with pytest.raises(ValueError, match="not in current frontier"):
            record_interview_answers(state, {"q2": "浅"})  # q1 未答

    def test_rejects_unknown_id(self) -> None:
        state = _state()
        with pytest.raises(ValueError, match="unknown question"):
            record_interview_answers(state, {"nope": "x"})

    def test_round_increments(self) -> None:
        state = _state()
        progress = record_interview_answers(state, {"q1": "A"})
        assert progress["round"] == 1
        assert progress["answered"] == 1


class TestRecommend:
    def test_options_first(self) -> None:
        state = _state()
        assert resolve_interview_answer(state, "q1") == "A"

    def test_prefer_overrides(self) -> None:
        state = _state()
        assert resolve_interview_answer(state, "q1", prefer="B") == "B"

    def test_recommended_field_fallback(self) -> None:
        state = _state()
        assert resolve_interview_answer(state, "q2") == "浅"


class TestProgress:
    def test_view_shape(self) -> None:
        state = _state()
        progress = interview_progress(state)
        assert progress["total"] == 3
        assert progress["answered"] == 0
        assert progress["complete"] is False
