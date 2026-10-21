"""oskill.deep_research_tree — 深度研究树.

递归研究：LLM（注入）把主题展开为子问题树，逐层深入，输出带深度/来源
的研究树。stateless。

Example:
    >>> r = await deep_research_tree("量子计算", caller=llm, max_depth=2)
    >>> r["node_count"] >= 1
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class ResearchCaller(Protocol):
    """LLM 调用协议。"""

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


async def deep_research_tree(
    topic: str,
    *,
    caller: ResearchCaller,
    max_depth: int = 3,
    max_branches: int = 5,
    max_nodes: int = 50,
) -> dict[str, Any]:
    """递归生成研究树。

    Args:
        topic: 研究主题。
        caller: LLM 调用器（注入）。
        max_depth: 最大深度。
        max_branches: 每节点子问题上限。
        max_nodes: 总节点上限。

    Returns:
        {"root": str, "node_count": int, "depth": int,
         "nodes": [{"id", "title", "depth", "parent", "children"}]}

    Raises:
        OskillError: topic 为空 / caller 未注入。
        LLMOskillError: LLM 调用失败。
    """
    if not topic or not topic.strip():
        raise OskillError("deep_research_tree: topic must not be empty")
    if caller is None:
        raise OskillError("deep_research_tree: caller must be injected")

    nodes: list[dict[str, Any]] = []
    counter = [0]

    def add_node(title: str, depth: int, parent: str | None) -> str:
        counter[0] += 1
        node_id = f"n{counter[0]}"
        nodes.append(
            {"id": node_id, "title": title, "depth": depth, "parent": parent, "children": []}
        )
        if parent is not None:
            for n in nodes:
                if n["id"] == parent:
                    n["children"].append(node_id)
                    break
        return node_id

    async def expand(title: str, depth: int, parent: str | None) -> None:
        if len(nodes) >= max_nodes or depth > max_depth:
            return
        node_id = add_node(title, depth, parent)
        if depth == max_depth:
            return
        sub = await _subtopics(title, caller=caller, max_branches=max_branches)
        for s in sub[:max_branches]:
            if len(nodes) >= max_nodes:
                break
            await expand(s, depth + 1, node_id)

    await expand(topic, 1, None)
    return {
        "root": topic,
        "node_count": len(nodes),
        "depth": max((n["depth"] for n in nodes), default=1),
        "nodes": nodes,
    }


async def _subtopics(title: str, *, caller: ResearchCaller, max_branches: int) -> list[str]:
    prompt = (
        f"研究主题「{title}」的子问题拆解：给出不超过 {max_branches} 个"
        "需要继续调研的子问题，每行一个，不要编号以外的任何修饰。"
    )
    try:
        response = await caller(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            max_tokens=512,
        )
    except Exception as exc:
        raise LLMOskillError("deep_research_tree: LLM call failed", cause=exc) from exc
    content = response.get("content", "")
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    lines = [ln.strip(" -1234567890.\t") for ln in str(content).splitlines() if ln.strip()]
    return [ln for ln in lines if len(ln) > 2][:max_branches] or [f"{title} 综述"]
