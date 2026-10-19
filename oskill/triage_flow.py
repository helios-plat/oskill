"""oskill.triage_flow — Issue 分流状态机 (mattpocock triage 3O 内化)。

把流入的 issue 移动到可处理状态:
  * **TriageIssue** — id/标题/描述/状态/标签/来源;
  * **TriageFlow** — 状态机: needs-triage → needs-info → ready-for-agent →
    ready-for-human → wontfix (合法迁移校验);
  * **agent_ready** — 判断 issue 是否可交给 agent (信息完整 + 未打 wontfix)。
零 veya 反向依赖: 纯状态机。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

STATUS_NEEDS_TRIAGE = "needs-triage"
STATUS_NEEDS_INFO = "needs-info"
STATUS_READY_AGENT = "ready-for-agent"
STATUS_READY_HUMAN = "ready-for-human"
STATUS_WONTFIX = "wontfix"
STATUSES = (
    STATUS_NEEDS_TRIAGE,
    STATUS_NEEDS_INFO,
    STATUS_READY_AGENT,
    STATUS_READY_HUMAN,
    STATUS_WONTFIX,
)

# 合法迁移表
_TRANSITIONS: dict[str, tuple[str, ...]] = {
    STATUS_NEEDS_TRIAGE: (
        STATUS_NEEDS_INFO,
        STATUS_READY_AGENT,
        STATUS_READY_HUMAN,
        STATUS_WONTFIX,
    ),
    STATUS_NEEDS_INFO: (STATUS_READY_AGENT, STATUS_READY_HUMAN, STATUS_WONTFIX),
    STATUS_READY_AGENT: (STATUS_READY_HUMAN, STATUS_NEEDS_INFO),
    STATUS_READY_HUMAN: (STATUS_READY_AGENT, STATUS_WONTFIX),
    STATUS_WONTFIX: (),
}


@dataclass
class TriageIssue:
    """一个待分流 issue。"""

    id: str = field(default_factory=lambda: f"issue_{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    source: str = ""  # bug report / feature request / ...
    labels: list[str] = field(default_factory=list)
    status: str = STATUS_NEEDS_TRIAGE
    created_ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "labels": self.labels,
            "status": self.status,
        }


class TriageFlow:
    """Issue 分流状态机。"""

    def __init__(self) -> None:
        self.issues: dict[str, TriageIssue] = {}

    def add_issue(self, issue: TriageIssue) -> TriageIssue:
        """登记新 issue (needs-triage)。"""
        issue.status = STATUS_NEEDS_TRIAGE
        self.issues[issue.id] = issue
        return issue

    def transition(self, issue_id: str, to_status: str, *, reason: str = "") -> TriageIssue:
        """迁移状态 (非法迁移抛 ValueError)。

        Args:
            issue_id: issue id。
            to_status: 目标状态。
            reason: 迁移原因 (记录到 labels/描述)。

        Returns:
            更新后的 issue。
        """
        issue = self._get(issue_id)
        if to_status not in _TRANSITIONS.get(issue.status, ()):
            raise ValueError(
                f"illegal transition: {issue.status} → {to_status} "
                f"(allowed: {_TRANSITIONS.get(issue.status, ())})"
            )
        issue.status = to_status
        if reason:
            issue.labels.append(f"reason:{reason}")
        return issue

    def agent_ready(self, issue_id: str) -> dict[str, Any]:
        """issue 是否可交给 agent (分流终态判断)。

        Returns:
            {ready, blockers} — ready 需: 信息完整 (有描述) + 状态
            ready-for-agent + 未打 wontfix。
        """
        issue = self._get(issue_id)
        blockers: list[str] = []
        if issue.status == STATUS_WONTFIX:
            blockers.append("wontfix")
        if issue.status == STATUS_NEEDS_INFO:
            blockers.append("缺信息")
        if issue.status == STATUS_NEEDS_TRIAGE:
            blockers.append("未分流")
        if not issue.description.strip():
            blockers.append("无描述")
        if issue.status not in (STATUS_READY_AGENT, STATUS_READY_HUMAN):
            blockers.append(f"状态 {issue.status}")
        ready = bool(issue.status == STATUS_READY_AGENT and issue.description.strip())
        return {"ready": ready, "blockers": blockers}

    def list_by_status(self, status: str) -> list[TriageIssue]:
        return [i for i in self.issues.values() if i.status == status]

    def _get(self, issue_id: str) -> TriageIssue:
        issue = self.issues.get(issue_id)
        if issue is None:
            raise KeyError(f"unknown issue: {issue_id!r}")
        return issue

    def summary(self) -> dict[str, int]:
        return {s: len(self.list_by_status(s)) for s in STATUSES}


__all__ = [
    "STATUS_NEEDS_INFO",
    "STATUS_NEEDS_TRIAGE",
    "STATUS_READY_AGENT",
    "STATUS_READY_HUMAN",
    "STATUS_WONTFIX",
    "STATUSES",
    "TriageFlow",
    "TriageIssue",
]
