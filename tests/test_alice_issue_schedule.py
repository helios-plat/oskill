from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from oskill.alice_issue_schedule import (
    IssueScheduleError,
    ScheduledResearchIssue,
    advance_schedule,
    plan_due_runs,
    scheduled_ticket_digest,
)

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def _issue(issue_id: str = "issue-1", **updates) -> ScheduledResearchIssue:
    values = dict(
        issue_id=issue_id,
        workspace_id="ws-btc",
        title="Review BTC catalysts",
        instruction="Summarize sourced updates; do not propose orders.",
        cadence="daily",
        next_run_at=NOW - timedelta(hours=1),
        enabled=True,
    )
    values.update(updates)
    return ScheduledResearchIssue(**values)


def test_due_planning_is_deterministic_and_never_claims_to_execute() -> None:
    issues = [_issue("weekly", cadence="weekly"), _issue("future", next_run_at=NOW + timedelta(seconds=1)), _issue("paused", enabled=False)]
    first = plan_due_runs(issues, now=NOW)
    second = plan_due_runs(issues, now=NOW)
    assert [ticket.to_dict() for ticket in first] == [ticket.to_dict() for ticket in second]
    assert [ticket.issue_id for ticket in first] == ["weekly"]
    assert first[0].mode == "research_only"
    assert scheduled_ticket_digest(first) == scheduled_ticket_digest(second)
    assert len(first[0].ticket_id) == 64


def test_advance_schedule_skips_missed_slots_without_drift() -> None:
    issue = _issue(next_run_at=NOW - timedelta(days=5))
    advanced = advance_schedule(issue, completed_at=NOW + timedelta(hours=2))
    assert advanced.next_run_at == NOW + timedelta(days=1)
    assert advanced.cadence == issue.cadence
    assert advanced.issue_id == issue.issue_id


def test_aware_times_required_and_duplicate_batch_rejected() -> None:
    with pytest.raises(IssueScheduleError, match="timezone-aware"):
        plan_due_runs([_issue()], now=datetime(2026, 10, 21, 12))
    with pytest.raises(IssueScheduleError, match="duplicate"):
        plan_due_runs([_issue(), _issue()], now=NOW)
    with pytest.raises(IssueScheduleError, match="unsupported"):
        _issue(cadence="monthly")


def test_ticket_identity_tracks_issue_and_scheduled_slot() -> None:
    a = plan_due_runs([_issue()], now=NOW)[0]
    b = plan_due_runs([_issue(next_run_at=NOW - timedelta(hours=2))], now=NOW)[0]
    c = plan_due_runs([_issue("issue-2")], now=NOW)[0]
    assert len({a.ticket_id, b.ticket_id, c.ticket_id}) == 3
