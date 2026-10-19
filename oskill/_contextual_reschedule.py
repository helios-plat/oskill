"""oskill.contextual_reschedule — 情境化重排程.

根据上下文（新约束/优先级变化/中断）对任务计划重排：
- caller 注入时：LLM 重排（返回有序任务 + 理由）
- 无 caller：启发式重排（优先级降序 + 依赖保持）

stateless。

Example:
    >>> r = await contextual_reschedule([{"id": "a", "priority": 1}, {"id": "b", "priority": 5}],
    ...                                  context="b 更紧急")
    >>> r["order"][0] == "b"
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class ReschedCaller(Protocol):
    """LLM 调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def contextual_reschedule(
    tasks: list[dict[str, Any]],
    *,
    context: str,
    caller: ReschedCaller | None = None,
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    """情境化重排任务计划。

    Args:
        tasks: 任务列表，每项 {"id", "priority"(int), "depends"(list)?, ...}。
        context: 重排情境（新信息/紧急度/资源变化）。
        caller: LLM（可选，注入）；None 走启发式。
        constraints: 硬约束（可选）。

    Returns:
        {"order": [task_id], "reasons": {task_id: str},
         "method": "llm"|"heuristic", "context": str}

    Raises:
        OskillError: tasks 为空 / context 为空。
        LLMOskillError: LLM 调用失败。
    """
    if not tasks:
        raise OskillError("contextual_reschedule: tasks must not be empty")
    if not context.strip():
        raise OskillError("contextual_reschedule: context must not be empty")

    task_ids = [str(t.get("id", f"t{i}")) for i, t in enumerate(tasks)]
    if caller is not None:
        try:
            return await _llm_reschedule(tasks, task_ids, context, constraints, caller)
        except LLMOskillError:
            raise
        except Exception:  # noqa: BLE001 - LLM 输出异常回退启发式
            pass

    return _heuristic_reschedule(tasks, task_ids)


def _heuristic_reschedule(tasks: list[dict[str, Any]], task_ids: list[str]) -> dict[str, Any]:
    """启发式：priority 降序，依赖优先（稳定排序）。"""
    by_id = {str(t.get("id", f"t{i}")): t for i, t in enumerate(tasks)}
    priority = {tid: int(by_id[tid].get("priority", 0)) for tid in task_ids}
    order = sorted(task_ids, key=lambda tid: (-priority[tid], task_ids.index(tid)))
    reasons = {tid: f"priority={priority[tid]}" for tid in order}
    return {"order": order, "reasons": reasons, "method": "heuristic", "context": ""}


async def _llm_reschedule(
    tasks: list[dict[str, Any]],
    task_ids: list[str],
    context: str,
    constraints: list[str] | None,
    caller: ReschedCaller,
) -> dict[str, Any]:
    listing = "\n".join(
        f"- {t.get('id')}: priority={t.get('priority', 0)} "
        f"depends={t.get('depends', [])} desc={t.get('description', '')}"
        for t in tasks
    )
    prompt = (
        f"任务:\n{listing}\n\n情境: {context}\n"
        + (f"\n硬约束: {constraints}\n" if constraints else "")
        + "\n输出重排后的任务 ID 列表（每行一个，按执行顺序），"
        "以及每行末尾用 | 分隔一句理由。"
    )
    try:
        response = await caller(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            max_tokens=1024,
        )
    except Exception as exc:
        raise LLMOskillError("contextual_reschedule: LLM call failed", cause=exc) from exc

    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    order: list[str] = []
    reasons: dict[str, str] = {}
    for line in str(content).splitlines():
        line = line.strip().strip("-*1234567890. \t")
        if not line:
            continue
        tid, _, reason = line.partition("|")
        tid = tid.strip()
        if tid in task_ids and tid not in order:
            order.append(tid)
            reasons[tid] = reason.strip()
    for tid in task_ids:  # 未提及的补尾
        if tid not in order:
            order.append(tid)
            reasons[tid] = "未提及，保持原序"
    return {"order": order, "reasons": reasons, "method": "llm", "context": context}
