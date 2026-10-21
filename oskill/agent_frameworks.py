"""oskill.agent_frameworks — 多框架适配 (hello-agents 第5/6章 3O 内化)。

低代码平台/框架实践的统一机制:
  * **FrameworkSpec** — 框架声明 (id/语言/入口/能力: autogen/agentscope/
    langgraph/n8n 等);
  * **FrameworkRegistry** — 注册/查找/按能力选择;
  * **dsl_to_framework** — WorkflowDAG DSL → 框架代码骨架 (确定性模板,
    AutoGen/LangGraph 两种后端);
  * 适配函数注入 (真实框架执行由调用方提供)。
零 veya 反向依赖: 纯模板 + 注册。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FRAMEWORK_AUTOGEN = "autogen"
FRAMEWORK_AGENTSCOPE = "agentscope"
FRAMEWORK_LANGGRAPH = "langgraph"
FRAMEWORK_N8N = "n8n"
FRAMEWORKS = (FRAMEWORK_AUTOGEN, FRAMEWORK_AGENTSCOPE, FRAMEWORK_LANGGRAPH, FRAMEWORK_N8N)


@dataclass
class FrameworkSpec:
    """框架声明。"""

    id: str
    language: str = "python"
    capabilities: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language,
            "capabilities": self.capabilities,
            "description": self.description,
        }


class FrameworkRegistry:
    """框架注册表 (Discovery-First)。"""

    def __init__(self) -> None:
        self.frameworks: dict[str, FrameworkSpec] = {
            FRAMEWORK_AUTOGEN: FrameworkSpec(
                FRAMEWORK_AUTOGEN,
                capabilities=["multi_agent", "chat"],
                description="微软多 agent 对话框架",
            ),
            FRAMEWORK_AGENTSCOPE: FrameworkSpec(
                FRAMEWORK_AGENTSCOPE,
                capabilities=["multi_agent", "visual"],
                description="阿里多 agent 框架",
            ),
            FRAMEWORK_LANGGRAPH: FrameworkSpec(
                FRAMEWORK_LANGGRAPH,
                capabilities=["graph", "stateful"],
                description="LangChain 图状态框架",
            ),
            FRAMEWORK_N8N: FrameworkSpec(
                FRAMEWORK_N8N,
                language="javascript",
                capabilities=["lowcode", "nodes"],
                description="低代码工作流平台",
            ),
        }

    def register(self, spec: FrameworkSpec) -> None:
        self.frameworks[spec.id] = spec

    def get(self, framework_id: str) -> FrameworkSpec:
        if framework_id not in self.frameworks:
            raise ValueError(
                f"unknown framework: {framework_id!r}; available: {self.list_frameworks()}"
            )
        return self.frameworks[framework_id]

    def list_frameworks(self) -> list[str]:
        return sorted(self.frameworks)

    def find_by_capability(self, cap: str) -> list[str]:
        return sorted(fid for fid, spec in self.frameworks.items() if cap in spec.capabilities)


# ── DSL → 框架代码骨架 ──────────────────────────────────────────────

_NODE_MAP = {
    "start": "on_message",
    "llm": "llm_node",
    "tool": "tool_node",
    "end": "final_answer",
}


def dsl_to_framework(
    workflow_dsl: dict[str, Any],
    framework: str,
) -> str:
    """把 WorkflowDAG DSL 生成框架代码骨架 (确定性模板)。

    Args:
        workflow_dsl: oskill.workflow_dsl.WorkflowDAG.to_dsl() 输出。
        framework: autogen / langgraph (其他框架抛 ValueError)。

    Returns:
        框架代码文本。

    Example:
        >>> d = {"nodes": [{"id": "s", "type": "start", "config": {}, "outputs": []}],
        ...      "edges": [], "variables": {}, "entry": "s"}
        >>> "autogen" in dsl_to_framework(d, "autogen")
        True
    """
    if framework == FRAMEWORK_AUTOGEN:
        return _dsl_to_autogen(workflow_dsl)
    if framework == FRAMEWORK_LANGGRAPH:
        return _dsl_to_langgraph(workflow_dsl)
    raise ValueError(
        f"codegen not supported for {framework!r}; "
        f"supported: {FRAMEWORK_AUTOGEN}, {FRAMEWORK_LANGGRAPH}"
    )


def _dsl_to_autogen(workflow_dsl: dict[str, Any]) -> str:
    nodes = workflow_dsl.get("nodes", [])
    edges = workflow_dsl.get("edges", [])
    lines = [
        "from autogen import ConversableAgent",
        "",
        "# Generated from workflow DSL (hello-agents framework adapter)",
        "",
    ]
    for node in nodes:
        nid = node["id"]
        ntype = node.get("type", "llm")
        if ntype == "start":
            lines.append(f"# start node: {nid}")
        elif ntype == "end":
            lines.append(f"# end node: {nid}")
        else:
            lines.append(
                f'{_node_var(nid)} = ConversableAgent(name="{nid}", '
                f'system_message="{node.get("config", {}).get("prompt", "")}")'
            )
    for edge in edges:
        src, dst = edge
        lines.append(f"# edge: {src} -> {dst}")
    lines.append("")
    return "\n".join(lines)


def _dsl_to_langgraph(workflow_dsl: dict[str, Any]) -> str:
    nodes = workflow_dsl.get("nodes", [])
    edges = workflow_dsl.get("edges", [])
    lines = [
        "from langgraph.graph import StateGraph, END",
        "",
        "# Generated from workflow DSL (hello-agents framework adapter)",
        "",
        "def build_graph(state_cls):",
        "    graph = StateGraph(state_cls)",
    ]
    for node in nodes:
        nid = node["id"]
        ntype = node.get("type", "llm")
        if ntype == "start":
            lines.append(f"    # start node: {nid}")
        elif ntype == "end":
            lines.append(f'    graph.add_node("{nid}", lambda s: s)')
        else:
            lines.append(f'    graph.add_node("{nid}", {_node_var(nid)}_fn)')
    for edge in edges:
        src, dst = edge
        lines.append(f'    graph.add_edge("{src}", "{dst}")')
    lines.append("    return graph.compile()")
    lines.append("")
    return "\n".join(lines)


def _node_var(nid: str) -> str:
    return nid.replace("-", "_").replace(".", "_")


__all__ = [
    "FRAMEWORK_AGENTSCOPE",
    "FRAMEWORK_AUTOGEN",
    "FRAMEWORK_LANGGRAPH",
    "FRAMEWORK_N8N",
    "FRAMEWORKS",
    "FrameworkRegistry",
    "FrameworkSpec",
    "dsl_to_framework",
]
