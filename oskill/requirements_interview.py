"""oskill.requirements_interview — 需求对齐访谈原语 (mattpocock grilling SKILL 3O 内化)。

机制: 设计树访谈状态机。每个决策问题可声明前置依赖 (depends_on) 与需要的
环境事实 (facts_needed); 引擎按"前沿 (frontier)"分轮推进 —— 每轮只问前置
条件已解决的问题, 事实查询派给 sub-agent (调用方注入), 用户只做决策。
全部问题答完 (frontier 空) 即达成共享理解。

零 veya 反向依赖: 纯状态机, 事实查询与 LLM 生成问题均由调用方注入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InterviewQuestion:
    """一个待访谈的决策问题。

    Attributes:
        id: 问题唯一 id (答案 dict 的键)。
        title: 问题标题。
        body: 问题正文 (可含选项说明)。
        options: 候选答案; None 表示开放题。
        recommended: 推荐答案 (供用户一键接受)。
        depends_on: 前置问题 id 列表 —— 全部已答才进入前沿。
        facts_needed: 需要环境事实的问题点 (由 sub-agent 查, 不问用户)。
    """

    id: str
    title: str
    body: str
    options: list[str] | None = None
    recommended: str = ""
    depends_on: list[str] = field(default_factory=list)
    facts_needed: list[str] = field(default_factory=list)


@dataclass
class InterviewState:
    """设计树访谈状态。

    Attributes:
        questions: 全部问题 (id → 定义)。
        answers: 已答 (id → 用户答案)。
        facts: 已查回的事实 (事实点 → 结果)。
        round: 当前轮次 (1 起)。
    """

    questions: dict[str, InterviewQuestion] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    round: int = 0

    def add_question(self, q: InterviewQuestion) -> None:
        """注册一个问题。"""
        self.questions[q.id] = q


def interview_frontier(state: InterviewState) -> list[InterviewQuestion]:
    """计算当前前沿: 前置条件已解决且未答的问题 (本轮可以问的)。

    Args:
        state: 访谈状态。

    Returns:
        本轮问题列表 (按注册顺序)。
    """
    frontier: list[InterviewQuestion] = []
    for q in state.questions.values():
        if q.id in state.answers:
            continue
        if all(dep in state.answers for dep in q.depends_on):
            frontier.append(q)
    return frontier


def interview_pending_facts(state: InterviewState) -> list[str]:
    """收集前沿问题中尚未查回的环境事实 (派 sub-agent 查, 不问用户)。

    Args:
        state: 访谈状态。

    Returns:
        待查事实点列表。
    """
    pending: list[str] = []
    for q in interview_frontier(state):
        for fact in q.facts_needed:
            if fact not in state.facts:
                pending.append(fact)
    return pending


def is_interview_complete(state: InterviewState) -> bool:
    """访谈是否完成: 所有问题已答 (前沿为空)。

    Args:
        state: 访谈状态。

    Returns:
        True 表示设计树全部走完, 无静默假设。
    """
    return not interview_frontier(state)


def interview_progress(state: InterviewState) -> dict[str, Any]:
    """进度视图: 已答/总数/前沿/待查事实/是否完成。

    Args:
        state: 访谈状态。

    Returns:
        {answered, total, frontier_ids, pending_facts, complete, round}
    """
    frontier = interview_frontier(state)
    return {
        "answered": len(state.answers),
        "total": len(state.questions),
        "frontier_ids": [q.id for q in frontier],
        "pending_facts": interview_pending_facts(state),
        "complete": not frontier,
        "round": state.round,
    }


def record_interview_facts(state: InterviewState, facts: dict[str, Any]) -> None:
    """记录 sub-agent 查回的环境事实。

    Args:
        state: 访谈状态。
        facts: 事实点 → 结果。
    """
    state.facts.update(facts)


def record_interview_answers(
    state: InterviewState,
    answers: dict[str, str],
) -> dict[str, Any]:
    """记录用户对本轮问题的答案, 推进到下一轮。

    只接受**当前前沿**问题的答案 (防乱序); 依赖未解决或未知 id 报错。

    Args:
        state: 访谈状态。
        answers: 问题 id → 用户答案。

    Returns:
        interview_progress(state) 更新后的视图。

    Raises:
        ValueError: 答案含未知问题 id, 或某问题依赖未答。
    """
    frontier_ids = {q.id for q in interview_frontier(state)}
    for qid in answers:
        if qid not in state.questions:
            raise ValueError(f"unknown question id: {qid}")
        if qid not in frontier_ids:
            raise ValueError(
                f"question {qid!r} not in current frontier "
                f"(dependencies unresolved or already answered)"
            )
    state.answers.update(answers)
    state.round += 1
    return interview_progress(state)


def resolve_interview_answer(
    state: InterviewState,
    question_id: str,
    *,
    prefer: str | None = None,
) -> str:
    """确定性地给出某问题的推荐答案 (供 LLM 呈现给用户一键接受)。

    优先级: prefer 参数 (显式覆盖) > options 首项 > recommended 字段。

    Args:
        state: 访谈状态。
        question_id: 问题 id。
        prefer: 显式推荐覆盖。

    Returns:
        推荐答案文本。
    """
    q = state.questions[question_id]
    if prefer is not None:
        return prefer
    if q.options:
        return q.options[0]
    return q.recommended
