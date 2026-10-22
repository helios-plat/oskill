"""Deterministic scheduler for research Issues; creates tickets but executes nothing."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Sequence

Cadence = Literal["hourly", "daily", "weekly"]
_INTERVALS = {"hourly": timedelta(hours=1), "daily": timedelta(days=1), "weekly": timedelta(days=7)}


class IssueScheduleError(ValueError):
    """Invalid research issue schedule."""


def _aware(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise IssueScheduleError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class ScheduledResearchIssue:
    issue_id: str
    workspace_id: str
    title: str
    instruction: str
    cadence: Cadence
    next_run_at: datetime
    enabled: bool = True

    def __post_init__(self) -> None:
        for name, value, limit in (
            ("issue_id", self.issue_id, 128),
            ("workspace_id", self.workspace_id, 128),
            ("title", self.title, 200),
            ("instruction", self.instruction, 4000),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise IssueScheduleError(f"{name} must contain 1..{limit} characters")
        if self.cadence not in _INTERVALS:
            raise IssueScheduleError(f"unsupported research cadence: {self.cadence}")
        _aware(self.next_run_at, "next_run_at")
        if not isinstance(self.enabled, bool):
            raise IssueScheduleError("enabled must be a boolean")


@dataclass(frozen=True)
class ResearchRunTicket:
    ticket_id: str
    issue_id: str
    workspace_id: str
    title: str
    instruction: str
    scheduled_for: str
    created_at: str
    mode: Literal["research_only"] = "research_only"

    def to_dict(self) -> dict[str, str]:
        return {
            "ticket_id": self.ticket_id,
            "issue_id": self.issue_id,
            "workspace_id": self.workspace_id,
            "title": self.title,
            "instruction": self.instruction,
            "scheduled_for": self.scheduled_for,
            "created_at": self.created_at,
            "mode": self.mode,
        }


def plan_due_runs(
    issues: Sequence[ScheduledResearchIssue], *, now: datetime
) -> list[ResearchRunTicket]:
    """Return stable tickets for enabled issues whose due time is at or before now."""
    instant = _aware(now, "now")
    tickets: list[ResearchRunTicket] = []
    seen: set[str] = set()
    for issue in issues:
        if not issue.enabled:
            continue
        due = _aware(issue.next_run_at, "next_run_at")
        if due > instant:
            continue
        if issue.issue_id in seen:
            raise IssueScheduleError(f"duplicate issue_id in schedule batch: {issue.issue_id}")
        seen.add(issue.issue_id)
        scheduled_for = due.isoformat(timespec="seconds")
        identity = hashlib.sha256(f"alice-research-v1\0{issue.issue_id}\0{scheduled_for}".encode()).hexdigest()
        tickets.append(
            ResearchRunTicket(
                ticket_id=identity,
                issue_id=issue.issue_id,
                workspace_id=issue.workspace_id,
                title=issue.title,
                instruction=issue.instruction,
                scheduled_for=scheduled_for,
                created_at=instant.isoformat(timespec="seconds"),
            )
        )
    return sorted(tickets, key=lambda item: (item.scheduled_for, item.issue_id))


def advance_schedule(issue: ScheduledResearchIssue, *, completed_at: datetime) -> ScheduledResearchIssue:
    """Advance to the first cadence slot strictly after completion; never execute work."""
    completed = _aware(completed_at, "completed_at")
    due = _aware(issue.next_run_at, "next_run_at")
    interval = _INTERVALS[issue.cadence]
    steps = max(1, int((completed - due) // interval) + 1)
    next_run = due + steps * interval
    return ScheduledResearchIssue(
        issue_id=issue.issue_id,
        workspace_id=issue.workspace_id,
        title=issue.title,
        instruction=issue.instruction,
        cadence=issue.cadence,
        next_run_at=next_run,
        enabled=issue.enabled,
    )


def scheduled_ticket_digest(tickets: Sequence[ResearchRunTicket]) -> str:
    """Deterministic digest useful for evidence and duplicate-batch detection."""
    encoded = json.dumps([ticket.to_dict() for ticket in tickets], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()
