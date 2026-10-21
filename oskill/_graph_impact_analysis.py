"""oskill.graph_impact_analysis — 基于 Code Graph 的修改影响面与依赖链分析技能.

Stateless 纯算法。依赖 LLMCallerProtocol 注入.

组合: code_graph (dict 输入) + LLM caller (依赖注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol — 不 import oprim，由调用方注入."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def graph_impact_analysis(
    code_graph: dict[str, Any],
    target_node_id: str,
    *,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """基于 Code Graph 的图拓扑结构分析修改目标节点带来的全局影响面算法.

    分析维度:
    1. 直接上游依赖（谁调用了 target_node）
    2. 下游依赖（target_node 调用了谁）
    3. LLM 评估破坏风险与缓解计划

    Args:
        code_graph: 代码图，含 "nodes" 和 "edges" 列表
        target_node_id: 目标节点 ID（如 "main.py::process"）
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "impacted_nodes": list[str],
            "downstream_deps": list[str],
            "risk_level": "high" | "medium" | "low",
            "plan": str,
        }
    """
    nodes = code_graph.get("nodes", [])
    edges = code_graph.get("edges", [])

    # 找出直接上游：谁调用了 target_node
    impacted_nodes = list(
        set(
            e["source"]
            for e in edges
            if e.get("target") == target_node_id and e.get("relation") in ("calls", "contains")
        )
    )

    # 找出下游依赖：target_node 调用了谁
    downstream_deps = list(
        set(
            e["target"]
            for e in edges
            if e.get("source") == target_node_id and e.get("relation") == "calls"
        )
    )

    # 节点名称（用于 LLM 上下文）
    node_names = {n["id"]: n.get("name", n["id"]) for n in nodes if "id" in n}

    impacted_names = [node_names.get(n, n) for n in impacted_nodes]
    downstream_names = [node_names.get(n, n) for n in downstream_deps]
    target_name = node_names.get(target_node_id, target_node_id)

    if not impacted_nodes and not downstream_deps:
        return {
            "impacted_nodes": [],
            "downstream_deps": [],
            "risk_level": "low",
            "plan": f"No direct dependents or dependencies found for '{target_name}'. Safe to modify.",
        }

    prompt = (
        f"Target Node to Modify: {target_name} ({target_node_id})\n"
        f"Direct Upstream Dependents (callers): {impacted_names}\n"
        f"Downstream Dependencies (called by target): {downstream_names}\n\n"
        f"Analyze the potential breakage risk of modifying this node. "
        f"Reply with a JSON object ONLY:\n"
        f"{{\n"
        f'  "risk_level": "high" or "medium" or "low",\n'
        f'  "mitigation_plan": "2-3 sentence plan"\n'
        f"}}"
    )

    try:
        raw = llm_caller(prompt, temperature=0.0)
        raw = raw.strip()
        # Extract JSON
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("{") or part.startswith("json"):
                    raw = part.replace("json\n", "").replace("json", "").strip()
                    break
        parsed = json.loads(raw)
        return {
            "impacted_nodes": impacted_names,
            "downstream_deps": downstream_names,
            "risk_level": parsed.get("risk_level", "medium"),
            "plan": parsed.get("mitigation_plan", ""),
        }
    except (json.JSONDecodeError, Exception):
        # 回退：基于图结构启发式判断
        risk = "low"
        if len(impacted_nodes) >= 3:
            risk = "high"
        elif len(impacted_nodes) >= 1:
            risk = "medium"

        return {
            "impacted_nodes": impacted_names,
            "downstream_deps": downstream_names,
            "risk_level": risk,
            "plan": (
                f"Review {len(impacted_nodes)} upstream callers before modifying "
                f"'{target_name}'. Run full test suite after changes."
            ),
        }
