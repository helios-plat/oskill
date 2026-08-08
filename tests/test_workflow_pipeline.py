"""Tests for workflow_pipeline (mattpocock idea→ship 流程 3O 内化)."""

from __future__ import annotations

import pytest

from oskill.workflow_pipeline import (
    TICKET_DONE,
    Ticket,
    WorkflowState,
    pipeline_next_action,
    pipeline_transition,
    ticket_set_status,
    tickets_check_cycles,
    tickets_next_runnable,
)


class TestTickets:
    def test_next_runnable_respects_blocking(self) -> None:
        a = Ticket("t1", "a")
        b = Ticket("t2", "b", blocked_by=["t1"])
        c = Ticket("t3", "c", blocked_by=["t2"])
        runnable = tickets_next_runnable([a, b, c])
        assert [t.id for t in runnable] == ["t1"]

    def test_unblock_after_done(self) -> None:
        a = Ticket("t1", "a")
        b = Ticket("t2", "b", blocked_by=["t1"])
        tickets = ticket_set_status([a, b], "t1", TICKET_DONE)
        assert tickets_next_runnable(tickets)[0].id == "t2"

    def test_set_status_recomputes_blocked(self) -> None:
        a = Ticket("t1", "a")
        b = Ticket("t2", "b", blocked_by=["t1"])
        tickets = ticket_set_status([a, b], "t1", TICKET_DONE)
        by_id = {t.id: t for t in tickets}
        assert by_id["t2"].status == TICKET_DONE or by_id["t2"].status == "open"

    def test_cycle_detection(self) -> None:
        a = Ticket("t1", "a", blocked_by=["t2"])
        b = Ticket("t2", "b", blocked_by=["t1"])
        cycles = tickets_check_cycles([a, b])
        assert len(cycles) == 1
        assert set(cycles[0]) == {"t1", "t2"}

    def test_no_cycle(self) -> None:
        a = Ticket("t1", "a")
        b = Ticket("t2", "b", blocked_by=["t1"])
        assert tickets_check_cycles([a, b]) == []


class TestPipeline:
    def test_full_flow(self) -> None:
        state = WorkflowState(idea="做一个 X")
        assert pipeline_next_action(state).action == "run_interview"
        state = pipeline_transition(state, "run_interview")
        assert state.stage == "GRILLING"

        # 模拟访谈完成 (interview 状态非空即可)
        from oskill.requirements_interview import InterviewState, is_interview_complete

        iv = InterviewState()
        iv.add_question(
            __import__(
                "oskill.requirements_interview", fromlist=["InterviewQuestion"]
            ).InterviewQuestion(id="q1", title="t", body="b", recommended="r")
        )
        __import__(
            "oskill.requirements_interview", fromlist=["record_interview_answers"]
        ).record_interview_answers(iv, {"q1": "r"})
        assert is_interview_complete(iv)
        state.interview = iv

        action = pipeline_next_action(state)
        assert action.action == "transition_to_spec"
        state = pipeline_transition(state, "interview_done")
        assert state.stage == "SPEC"

        state = pipeline_transition(state, "spec_written", spec="spec 文本")
        assert state.stage == "TICKETS"

        tickets = [Ticket("t1", "a"), Ticket("t2", "b", blocked_by=["t1"])]
        state = pipeline_transition(state, "tickets_split", tickets=tickets)
        assert state.stage == "IMPLEMENT"

        assert pipeline_next_action(state).payload.id == "t1"
        state = pipeline_transition(state, "ticket_done", ticket_id="t1")
        assert pipeline_next_action(state).payload.id == "t2"
        state = pipeline_transition(state, "ticket_done", ticket_id="t2")

        # 进入 review
        state.stage = "REVIEW"
        action = pipeline_next_action(state)
        assert action.action == "run_review"
        state = pipeline_transition(state, "review_done", review={"ok": True})
        assert state.stage == "DONE"

    def test_invalid_transition_raises(self) -> None:
        state = WorkflowState()
        with pytest.raises(ValueError, match="cannot spec_written from IDEA"):
            pipeline_transition(state, "spec_written", spec="x")

    def test_unknown_event_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown event"):
            pipeline_transition(WorkflowState(), "nope")


class TestSerialization:
    def test_roundtrip_with_interview_and_tickets(self) -> None:
        from oskill.requirements_interview import (
            InterviewQuestion,
            InterviewState,
            record_interview_answers,
            record_interview_facts,
        )
        from oskill.workflow_pipeline import workflow_from_dict, workflow_to_dict

        iv = InterviewState()
        iv.add_question(InterviewQuestion(id="q1", title="目标", body="做什么?", recommended="A",
                                          depends_on=[], facts_needed=["repo_lang"]))
        record_interview_answers(iv, {"q1": "A"})
        record_interview_facts(iv, {"repo_lang": "python"})

        state = WorkflowState(idea="x", spec="spec", stage="IMPLEMENT",
                              interview=iv,
                              tickets=[Ticket("t1", "a"), Ticket("t2", "b", blocked_by=["t1"])])
        restored = workflow_from_dict(workflow_to_dict(state))
        assert restored.stage == "IMPLEMENT"
        assert restored.spec == "spec"
        assert [t.id for t in restored.tickets] == ["t1", "t2"]
        assert restored.tickets[1].blocked_by == ["t1"]
        assert restored.interview is not None
        assert restored.interview.answers == {"q1": "A"}
        assert restored.interview.facts == {"repo_lang": "python"}

    def test_roundtrip_bare(self) -> None:
        from oskill.workflow_pipeline import workflow_from_dict, workflow_to_dict

        restored = workflow_from_dict(workflow_to_dict(WorkflowState()))
        assert restored.stage == "IDEA"
        assert restored.interview is None
        assert restored.tickets == []
