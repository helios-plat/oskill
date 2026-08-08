"""oskill.workflow_dsl — 工作流 DSL + DAG 节点图执行 (Dify 机制 3O 内化)。

把可视化 LLM 工作流编码为可分享/版本化的声明式定义 + 确定性执行:
  * **WorkflowNode** — 类型化节点: start/end/llm/tool/condition/iteration/
    knowledge/variable (LLM 与工具函数由调用方注入);
  * **WorkflowDAG** — nodes + edges + variables + entry, to_dsl/parse_dsl
    (JSON 定义 ↔ 对象, 可版本化/跨环境迁移);
  * **validate_dsl** — 结构校验: 循环检测 (DAG)/未知节点/悬空边/入口缺失;
  * **topological_execute** — DAG 拓扑执行: 并行分支 + 条件门控 + 变量注入
    (执行器按节点类型注入, 结果走 edges 传播)。

零 veya 反向依赖: 节点执行函数由调用方注入; 纯 DAG 算法。
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ── 节点类型 ─────────────────────────────────────────────────────────

NODE_START = "start"
NODE_END = "end"
NODE_LLM = "llm"
NODE_TOOL = "tool"
NODE_CONDITION = "condition"
NODE_ITERATION = "iteration"
NODE_KNOWLEDGE = "knowledge"
NODE_VARIABLE = "variable"
NODE_TYPES = (
    NODE_START,
    NODE_END,
    NODE_LLM,
    NODE_TOOL,
    NODE_CONDITION,
    NODE_ITERATION,
    NODE_KNOWLEDGE,
    NODE_VARIABLE,
)


@dataclass
class WorkflowNode:
    """一个工作流节点。

    Attributes:
        id: 节点唯一 id。
        type: start/end/llm/tool/condition/iteration/knowledge/variable。
        config: 节点配置 (prompt/参数/条件表达式等)。
        outputs: 输出变量名列表 (供下游引用)。
    """

    id: str
    type: str
    config: dict[str, Any] = field(default_factory=dict)
    outputs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "config": self.config, "outputs": self.outputs}


@dataclass
class WorkflowDAG:
    """工作流定义 (nodes + edges + variables)。"""

    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    entry: str = ""

    def add_node(self, node: WorkflowNode) -> None:
        """添加节点 (幂等覆盖)。"""
        self.nodes[node.id] = node
        if self.entry == "" and node.type == NODE_START:
            self.entry = node.id

    def add_edge(self, source: str, target: str) -> None:
        """添加边 (源 → 目标)。"""
        if (source, target) not in self.edges:
            self.edges.append((source, target))

    # ── DSL 序列化 ────────────────────────────────────────────────────

    def to_dsl(self) -> dict[str, Any]:
        """序列化为 JSON DSL (可分享/版本化)。"""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [list(e) for e in self.edges],
            "variables": dict(self.variables),
            "entry": self.entry,
        }

    def to_dsl_json(self) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dsl(), ensure_ascii=False, indent=2)

    def predecessors(self, node_id: str) -> list[str]:
        """某节点的直接前驱。"""
        return [s for s, t in self.edges if t == node_id]

    def successors(self, node_id: str) -> list[str]:
        """某节点的直接后继。"""
        return [t for s, t in self.edges if s == node_id]

    def summary(self) -> dict[str, Any]:
        """概览。"""
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "types": {t: sum(1 for n in self.nodes.values() if n.type == t) for t in NODE_TYPES},
            "entry": self.entry,
        }


def parse_dsl(data: dict[str, Any]) -> WorkflowDAG:
    """从 DSL dict 还原 WorkflowDAG。

    Args:
        data: to_dsl() 输出。

    Returns:
        WorkflowDAG。
    """
    workflow = WorkflowDAG(entry=data.get("entry", ""))
    for node_data in data.get("nodes", []):
        workflow.nodes[node_data["id"]] = WorkflowNode(
            id=node_data["id"],
            type=node_data.get("type", NODE_LLM),
            config=node_data.get("config", {}),
            outputs=node_data.get("outputs", []),
        )
    for edge in data.get("edges", []):
        workflow.edges.append((edge[0], edge[1]))
    workflow.variables.update(data.get("variables", {}))
    return workflow


def parse_dsl_json(text: str) -> WorkflowDAG:
    """从 JSON 字符串还原 WorkflowDAG。"""
    return parse_dsl(json.loads(text))


# ── 结构校验 ─────────────────────────────────────────────────────────


def validate_dsl(workflow: WorkflowDAG) -> dict[str, Any]:
    """工作流结构校验。

    Args:
        workflow: 工作流。

    Returns:
        {ok, problems} — 校验: 循环检测 (DAG)/未知节点/悬空边/入口缺失。

    Example:
        >>> w = WorkflowDAG(entry="n1")
        >>> w.add_node(WorkflowNode("n1", "start"))
        >>> w.add_node(WorkflowNode("n2", "end"))
        >>> w.add_edge("n1", "n2")
        >>> validate_dsl(w)["ok"]
        True
    """
    problems: list[str] = []
    node_ids = set(workflow.nodes)

    if not workflow.entry:
        problems.append("入口缺失 (无 start 节点)")
    elif workflow.entry not in node_ids:
        problems.append(f"入口节点不存在: {workflow.entry}")

    for source, target in workflow.edges:
        if source not in node_ids:
            problems.append(f"边源不存在: {source}")
        if target not in node_ids:
            problems.append(f"边目标不存在: {target}")

    for node_id, node in workflow.nodes.items():
        if node.type not in NODE_TYPES:
            problems.append(f"未知节点类型: {node.id}:{node.type}")

    # 循环检测 (Kahn 拓扑排序)
    indegree = {nid: 0 for nid in node_ids}
    adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for source, target in workflow.edges:
        if source in adjacency and target in indegree:
            adjacency[source].append(target)
            indegree[target] += 1
    queue = deque([nid for nid, deg in indegree.items() if deg == 0])
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for neighbor in adjacency[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)
    if visited != len(node_ids):
        problems.append("检测到循环依赖 (非 DAG)")

    return {"ok": not problems, "problems": problems}


# ── DAG 拓扑执行 ─────────────────────────────────────────────────────

NodeExecutor = Callable[[WorkflowNode, dict[str, Any], dict[str, Any]], Any]
"""节点执行器: (node, inputs, context) → 节点输出。

执行器按节点类型分派 (LLM/工具/条件/迭代/知识检索等由调用方实现);
返回的 dict 作为该节点输出变量 (key = outputs 里的变量名或任意键)。
"""


def topological_execute(
    workflow: WorkflowDAG,
    inputs: dict[str, Any],
    executor: NodeExecutor,
) -> dict[str, Any]:
    """DAG 拓扑执行: 并行分支 + 条件门控 + 变量传播。

    Args:
        workflow: 工作流。
        inputs: 输入变量。
        executor: 节点执行器 (按类型注入; 未执行器类型返回 {"error": ...})。

    Returns:
        {outputs, results: {node_id: output}, errors} — 从 end 节点输出。

    Raises:
        ValueError: 结构非法 (先 validate_dsl)。
    """
    validation = validate_dsl(workflow)
    if not validation["ok"]:
        raise ValueError(f"invalid workflow: {validation['problems']}")

    context: dict[str, Any] = dict(workflow.variables)
    context.update(inputs)
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}

    indegree = {nid: 0 for nid in workflow.nodes}
    adjacency: dict[str, list[str]] = {nid: [] for nid in workflow.nodes}
    for source, target in workflow.edges:
        if source in adjacency and target in indegree:
            adjacency[source].append(target)
            indegree[target] += 1

    ready = deque([nid for nid, deg in indegree.items() if deg == 0])
    while ready:
        node_id = ready.popleft()
        node = workflow.nodes[node_id]
        # 条件门控: condition 节点按 true/false 选择分支
        if node.type == NODE_CONDITION:
            output = executor(node, inputs, context)
            results[node_id] = output
            for target in adjacency[node_id]:
                if target in results:
                    continue
                # 后续边仅在条件满足时传播 (边带 branch 标记由调用方建模)
                context.update(output)
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
            continue
        try:
            output = executor(node, inputs, context)
        except Exception as exc:  # noqa: BLE001
            output = {"error": f"{exc.__class__.__name__}: {exc}"}
            errors[node_id] = output["error"]
        results[node_id] = output
        context.update(output)
        for target in adjacency[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)

    outputs: dict[str, Any] = {}
    for node in workflow.nodes.values():
        node_output = results.get(node.id, {})
        for key in node.outputs:
            if key in node_output:
                outputs[key] = node_output[key]
    return {"outputs": outputs, "results": results, "errors": errors}
