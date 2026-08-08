"""oskill.workflow_pipeline — 工程工作流编排状态机 (mattpocock idea→ship 流程 3O 内化)。

机制: 把 "grill → spec → tickets → implement → review" 编码为确定性阶段机:
  * 阶段 (Stage): IDEA → GRILLING → SPEC → TICKETS → IMPLEMENT → REVIEW → DONE;
  * 每个阶段给出 next_action (下一步该做什么) 与 transition (完成本阶段的事件);
  * Ticket 携带 blocked_by 阻塞边 (tracer-bullet 票), 引擎解算可运行集;
  * blocked_by 环检测, 防死锁编排。
状态持久化由调用方选择 (可用 veya_loop GoalKernel / AppendOnlyEventStore 作
事件溯源后端); 本模块是纯投影状态机, 不绑定存储。

零 veya 反向依赖: 纯状态机, 无外部命令。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ── 阶段 ────────────────────────────────────────────────────────────

Stage = Literal["IDEA", "GRILLING", "SPEC", "TICKETS", "IMPLEMENT", "REVIEW", "DONE"]

_STAGE_ORDER: list[Stage] = [
    "IDEA",
    "GRILLING",
    "SPEC",
    "TICKETS",
    "IMPLEMENT",
    "REVIEW",
    "DONE",
]

# ── 票 (tracer-bullet) ──────────────────────────────────────────────

TICKET_OPEN = "open"
TICKET_BLOCKED = "blocked"
TICKET_DONE = "done"


@dataclass
class Ticket:
    """一张 tracer-bullet 票。

    Attributes:
        id: 票 id。
        title: 票标题。
        blocked_by: 前置票 id 列表 (阻塞边; 全部 done 才可执行)。
        spec_ref: 关联 spec 段引用。
        status: open / blocked / done。
    """

    id: str
    title: str
    blocked_by: list[str] = field(default_factory=list)
    spec_ref: str = ""
    status: str = TICKET_OPEN


# ── 工作流状态 ──────────────────────────────────────────────────────


@dataclass
class WorkflowState:
    """工作流投影状态。

    Attributes:
        stage: 当前阶段。
        idea: 原始想法 (IDEA 阶段输入)。
        interview: 访谈状态 (grilling 阶段, 见 requirements_interview)。
        spec: spec 文本 (SPEC 阶段产出)。
        tickets: 票列表 (TICKETS 阶段产出)。
        current_ticket: 正在 implement 的票 id。
        review: 审查报告 (REVIEW 阶段产出, 见 review_double_axis)。
        meta: 自由元数据。
    """

    stage: Stage = "IDEA"
    idea: str = ""
    interview: Any = None
    spec: str = ""
    tickets: list[Ticket] = field(default_factory=list)
    current_ticket: str | None = None
    review: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineAction:
    """引擎给出的下一步动作 (供调用方/LLM 执行)。

    Attributes:
        stage: 当前阶段。
        action: 动作名。
        hint: 执行提示。
        payload: 附带数据 (如待访谈问题/可运行票)。
    """

    stage: Stage
    action: str
    hint: str = ""
    payload: Any = None


# ── 票操作 ──────────────────────────────────────────────────────────


def tickets_next_runnable(tickets: list[Ticket]) -> list[Ticket]:
    """解算阻塞边: 返回当前可执行的票 (blocked_by 全 done 且自身未 done)。

    顺序保持输入顺序。

    Args:
        tickets: 票列表。

    Returns:
        可执行票列表。

    Example:
        >>> a = Ticket("t1", "a"); b = Ticket("t2", "b", blocked_by=["t1"])
        >>> tickets_next_runnable([a, b])[0].id
        't1'
    """
    status = {t.id: t.status for t in tickets}
    return [
        t
        for t in tickets
        if t.status != TICKET_DONE and all(status.get(dep) == TICKET_DONE for dep in t.blocked_by)
    ]


def ticket_set_status(tickets: list[Ticket], ticket_id: str, status: str) -> list[Ticket]:
    """置某票状态; 依赖它的票自动重新计算 blocked/open。

    Args:
        tickets: 票列表。
        ticket_id: 目标票 id。
        status: TICKET_OPEN / TICKET_DONE。

    Returns:
        更新后的票列表 (新列表, 不改原对象)。

    Raises:
        ValueError: 票不存在。
    """
    by_id = {t.id: t for t in tickets}
    if ticket_id not in by_id:
        raise ValueError(f"unknown ticket: {ticket_id}")
    updated: list[Ticket] = []
    for t in tickets:
        if t.id == ticket_id:
            updated.append(Ticket(t.id, t.title, t.blocked_by, t.spec_ref, status))
        else:
            blocked = [d for d in t.blocked_by if d != ticket_id]
            still_blocked = any(d in by_id for d in blocked) and not all(
                by_id.get(d, t.status) == TICKET_DONE for d in blocked
            )
            new_status = TICKET_BLOCKED if (blocked and still_blocked) else TICKET_OPEN
            updated.append(Ticket(t.id, t.title, t.blocked_by, t.spec_ref, new_status))
    return updated


def tickets_check_cycles(tickets: list[Ticket]) -> list[list[str]]:
    """检测 blocked_by 依赖环 (死锁编排)。

    Args:
        tickets: 票列表。

    Returns:
        环路径列表 (空 = 无环)。
    """
    by_id = {t.id: t for t in tickets}
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []
    stack: list[str] = []

    def dfs(node: str) -> None:
        if node in visiting:
            start = stack.index(node)
            cycles.append(stack[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for dep in by_id.get(node, Ticket(node, "")).blocked_by:
            if dep in by_id:
                dfs(dep)
        stack.pop()
        visiting.discard(node)
        visited.add(node)

    for ticket in tickets:
        dfs(ticket.id)
    return cycles


# ── 序列化 (通用持久化, 不绑存储) ───────────────────────────────────


def workflow_to_dict(state: WorkflowState) -> dict[str, Any]:
    """将工作流状态序列化为可持久化 dict (JSON 友好)。

    Args:
        state: 工作流状态。

    Returns:
        dict (含 tickets 与 interview 的还原所需全部字段)。
    """
    tickets = [
        {
            "id": t.id,
            "title": t.title,
            "blocked_by": list(t.blocked_by),
            "spec_ref": t.spec_ref,
            "status": t.status,
        }
        for t in state.tickets
    ]
    interview = None
    if state.interview is not None:
        questions = [
            {
                "id": q.id,
                "title": q.title,
                "body": q.body,
                "options": q.options,
                "recommended": q.recommended,
                "depends_on": list(q.depends_on),
                "facts_needed": list(q.facts_needed),
            }
            for q in state.interview.questions.values()
        ]
        interview = {
            "questions": questions,
            "answers": dict(state.interview.answers),
            "facts": dict(state.interview.facts),
            "round": state.interview.round,
        }
    return {
        "stage": state.stage,
        "idea": state.idea,
        "interview": interview,
        "spec": state.spec,
        "tickets": tickets,
        "current_ticket": state.current_ticket,
        "meta": dict(state.meta),
    }


def workflow_from_dict(data: dict[str, Any]) -> WorkflowState:
    """从 workflow_to_dict 输出还原工作流状态。

    Args:
        data: 序列化 dict。

    Returns:
        WorkflowState。
    """
    tickets = [
        Ticket(
            id=t["id"],
            title=t["title"],
            blocked_by=list(t.get("blocked_by", [])),
            spec_ref=t.get("spec_ref", ""),
            status=t.get("status", TICKET_OPEN),
        )
        for t in data.get("tickets", [])
    ]
    interview = None
    iv = data.get("interview")
    if iv is not None:
        from oskill.requirements_interview import InterviewQuestion, InterviewState

        interview = InterviewState(round=iv.get("round", 0))
        for qd in iv.get("questions", []):
            interview.add_question(
                InterviewQuestion(
                    id=qd["id"],
                    title=qd["title"],
                    body=qd["body"],
                    options=qd.get("options"),
                    recommended=qd.get("recommended", ""),
                    depends_on=list(qd.get("depends_on", [])),
                    facts_needed=list(qd.get("facts_needed", [])),
                )
            )
        interview.answers.update(iv.get("answers", {}))
        interview.facts.update(iv.get("facts", {}))
    return WorkflowState(
        stage=data.get("stage", "IDEA"),
        idea=data.get("idea", ""),
        interview=interview,
        spec=data.get("spec", ""),
        tickets=tickets,
        current_ticket=data.get("current_ticket"),
        meta=dict(data.get("meta", {})),
    )


# ── 阶段机 ──────────────────────────────────────────────────────────


def pipeline_next_action(state: WorkflowState) -> PipelineAction:
    """根据当前阶段与子状态, 给出下一步动作。

    Args:
        state: 工作流状态。

    Returns:
        下一步动作。
    """
    if state.stage == "IDEA":
        return PipelineAction(
            "IDEA", "run_interview", "把 idea 交给 requirements_interview, 对齐设计树", state.idea
        )
    if state.stage == "GRILLING":
        if state.interview is None:
            return PipelineAction("GRILLING", "run_interview", "初始化访谈")
        from oskill.requirements_interview import interview_progress

        progress = interview_progress(state.interview)
        if progress["pending_facts"]:
            return PipelineAction(
                "GRILLING", "fetch_facts", "派 sub-agent 查环境事实", progress["pending_facts"]
            )
        if not progress["complete"]:
            return PipelineAction(
                "GRILLING", "ask_questions", "问当前前沿问题 (每题带推荐答案)", progress
            )
        return PipelineAction("GRILLING", "transition_to_spec", "访谈完成 → 进入 SPEC 阶段")
    if state.stage == "SPEC":
        return PipelineAction(
            "SPEC", "write_spec", "把访谈结论写成 spec 文本 (调用方/LLM)", state.idea
        )
    if state.stage == "TICKETS":
        return PipelineAction(
            "TICKETS", "split_tickets", "把 spec 拆成 tracer-bullet 票 (含 blocked_by)", state.spec
        )
    if state.stage == "IMPLEMENT":
        runnable = tickets_next_runnable(state.tickets)
        if runnable:
            return PipelineAction(
                "IMPLEMENT", "implement_ticket", "按票实现 (可接 tdd/代码可靠性闭环)", runnable[0]
            )
        if all(t.status == TICKET_DONE for t in state.tickets) and state.tickets:
            return PipelineAction(
                "IMPLEMENT", "transition_to_review", "全部票完成 → 进入 REVIEW 阶段"
            )
        return PipelineAction("IMPLEMENT", "wait", "票被阻塞, 检查依赖环", None)
    if state.stage == "REVIEW":
        return PipelineAction(
            "REVIEW", "run_review", "双轴审查 diff (standards + spec)", state.current_ticket
        )
    return PipelineAction("DONE", "done", "工作流完成")


def pipeline_transition(state: WorkflowState, event: str, **payload: Any) -> WorkflowState:
    """推进阶段。

    Args:
        state: 工作流状态。
        event: 迁移事件 (run_interview / interview_done / spec_written /
            tickets_split / ticket_done / review_done)。
        payload: 事件数据 (spec=, tickets=, interview=, review=, ticket_id=)。

    Returns:
        新 WorkflowState (不改原对象)。

    Raises:
        ValueError: 未知事件或非法迁移。
    """
    from dataclasses import replace

    if event == "run_interview":
        if state.stage != "IDEA":
            raise ValueError(f"cannot run_interview from {state.stage}")
        return replace(state, stage="GRILLING")
    if event == "interview_done":
        if state.stage != "GRILLING":
            raise ValueError(f"cannot interview_done from {state.stage}")
        return replace(state, stage="SPEC")
    if event == "spec_written":
        if state.stage != "SPEC":
            raise ValueError(f"cannot spec_written from {state.stage}")
        return replace(state, stage="TICKETS", spec=payload.get("spec", state.spec))
    if event == "tickets_split":
        if state.stage != "TICKETS":
            raise ValueError(f"cannot tickets_split from {state.stage}")
        tickets = payload.get("tickets", [])
        return replace(state, stage="IMPLEMENT", tickets=list(tickets))
    if event == "ticket_done":
        if state.stage != "IMPLEMENT":
            raise ValueError(f"cannot ticket_done from {state.stage}")
        ticket_id = payload["ticket_id"]
        tickets = ticket_set_status(state.tickets, ticket_id, TICKET_DONE)
        return replace(state, tickets=tickets, current_ticket=None)
    if event == "review_done":
        if state.stage != "REVIEW":
            raise ValueError(f"cannot review_done from {state.stage}")
        return replace(state, stage="DONE", review=payload.get("review"))
    raise ValueError(f"unknown event: {event}")
