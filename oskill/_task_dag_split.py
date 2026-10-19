"""oskill.task_dag_split — 复杂自然语言任务分解为 DAG 依赖图算法.

组合 oprim.llm_chat_call（LLM 分解）+ 纯解析（JSON → DAG 校验），
输出节点 + 依赖边 + 拓扑排序。stateless。

Example:
    >>> r = await task_dag_split("开发一个登录功能", caller=my_caller)
    >>> r["nodes"][0]["id"]
    't1'
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from oprim import llm_chat_call

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class DagCaller(Protocol):
    """LLM 分解调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def task_dag_split(
    task: str,
    *,
    caller: DagCaller,
    max_nodes: int = 12,
    max_tokens: int = 2048,
    context: str = "",
) -> dict[str, Any]:
    """把自然语言任务分解为 DAG 任务图。

    Args:
        task: 任务描述。
        caller: LLM 调用器（注入）。
        max_nodes: 节点数上限（LLM 提示中约束）。
        max_tokens: 分解输出上限。
        context: 附加上下文（约束/资源），可选。

    Returns:
        {
            "nodes": [{"id", "title", "description"}],
            "edges": [{"from", "to"}],
            "topological_order": [str],
            "cycle_detected": bool,
        }

    Raises:
        OskillError: task 为空 / 分解结果无法解析。
        LLMOskillError: LLM 调用失败。
    """
    if not task or not task.strip():
        raise OskillError("task_dag_split: task must not be empty")


    prompt = (
        f"把以下任务分解为不超过 {max_nodes} 个可并行/串行的子任务 DAG。"
        '只输出 JSON：{"nodes": [{"id": "t1", "title": "...", "description": "..."}],'
        ' "edges": [{"from": "t1", "to": "t2"}]}。'
        "id 必须为 t1..tN；边表示依赖（from 先于 to）。\n\n"
        f"任务: {task}\n" + (f"\n约束/上下文: {context}\n" if context else "")
    )
    try:
        resp = await llm_chat_call(
            [{"role": "user", "content": prompt}],
            caller=caller,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        raise LLMOskillError("task_dag_split: LLM call failed", cause=exc) from exc

    parsed = _extract_json(resp["text"])
    nodes = parsed.get("nodes") or []
    edges = parsed.get("edges") or []

    if not nodes:
        raise OskillError("task_dag_split: LLM returned no nodes")
    node_ids = [str(n.get("id")) for n in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise OskillError("task_dag_split: duplicate node ids")

    valid_edges: list[dict[str, str]] = []
    for e in edges:
        frm, to = str(e.get("from", "")), str(e.get("to", ""))
        if frm in node_ids and to in node_ids and frm != to:
            valid_edges.append({"from": frm, "to": to})

    order, cycle = _toposort(node_ids, valid_edges)
    return {
        "nodes": nodes,
        "edges": valid_edges,
        "topological_order": order,
        "cycle_detected": cycle,
    }


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise OskillError("task_dag_split: LLM output is not valid JSON") from exc
    raise OskillError("task_dag_split: LLM output is not valid JSON")


def _toposort(node_ids: list[str], edges: list[dict[str, str]]) -> tuple[list[str], bool]:
    """Kahn 拓扑排序；返回 (顺序, 是否检测到环)。"""
    indeg = {n: 0 for n in node_ids}
    adj: dict[str, list[str]] = {n: [] for n in node_ids}
    for e in edges:
        adj[e["from"]].append(e["to"])
        indeg[e["to"]] += 1

    ready = [n for n in node_ids if indeg[n] == 0]
    ready.sort()
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in adj[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
                ready.sort()
    cycle = len(order) != len(node_ids)
    if cycle:
        order = node_ids  # 有环时退回原始顺序，cycle_detected 置真
    return order, cycle
