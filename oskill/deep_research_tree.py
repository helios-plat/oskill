"""Deep research tree.

The legacy synchronous research pipeline remains available through
``llm_caller``/``context``. Supplying ``caller`` returns the async Veya tree.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError
from oskill._types import LLMOskillError


@runtime_checkable
class ResearchCaller(Protocol):
    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


def deep_research_tree(
    topic: str,
    llm_caller: Callable | None = None,
    context: dict[str, Any] | None = None,
    *,
    caller: ResearchCaller | None = None,
    max_depth: int = 3,
    max_branches: int = 5,
    max_nodes: int = 50,
    query: str | None = None,
    **kwargs: Any,
) -> Any:
    """Run the legacy research pipeline or return the async tree coroutine."""
    if caller is not None:
        return _deep_research_tree_async(
            topic,
            caller=caller,
            max_depth=max_depth,
            max_branches=max_branches,
            max_nodes=max_nodes,
        )
    return _legacy_deep_research_tree(query or topic, llm_caller, context)


def _legacy_deep_research_tree(
    query: str,
    llm_caller: Callable | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    ctx = context or {}
    max_depth = int(ctx.get("max_depth", 3))
    max_branches = int(ctx.get("max_branches", 5))
    visited: set[str] = set()

    def branch(question: str, depth: int) -> list[dict[str, Any]]:
        if depth > max_depth or question in visited:
            return []
        visited.add(question)
        results: list[dict[str, Any]] = []

        if llm_caller is not None:
            try:
                out = llm_caller(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a deep research agent. For the given question, "
                                'output JSON: {"answer": "...", "citations": ["source1"], '
                                '"confidence": 0.0-1.0, "sub_questions": ["q1"]}'
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                    tools=None,
                    config=ctx,
                )
                raw = out.get("content", "") if isinstance(out, dict) else str(out)
                match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
                parsed = json.loads(match.group(1)) if match else _parse_research(raw)
            except Exception:
                parsed = {"answer": "", "citations": [], "confidence": 0.0, "sub_questions": []}
        else:
            parsed = _deterministic_research(question)

        results.append(
            {
                "hypothesis": question,
                "evidence": parsed.get("answer", ""),
                "citations": parsed.get("citations", [])[
                    : max(int(ctx.get("max_citations", 10)), 1)
                ],
                "confidence": float(parsed.get("confidence", 0.5)),
                "depth": depth,
            }
        )
        for sub_question in parsed.get("sub_questions", [])[:max_branches]:
            results.extend(branch(str(sub_question), depth + 1))
        return results

    findings = branch(query, 1)
    report_lines = [f"# Deep Research: {query}", f"Depth: {max_depth}, Findings: {len(findings)}"]
    for finding in findings:
        report_lines.append(
            f"\n## {finding['hypothesis']} (confidence: {finding['confidence']:.2f})"
        )
        report_lines.append(finding["evidence"][:500])
        if finding["citations"]:
            report_lines.append("Citations: " + "; ".join(finding["citations"][:5]))

    return {
        "status": "completed",
        "findings": findings,
        "report": "\n\n".join(report_lines),
        "tree_depth": max_depth,
        "total_steps": len(findings),
        "unique_questions": len(visited),
    }


def _parse_research(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception:
        return {"answer": raw[:500], "citations": [], "confidence": 0.3, "sub_questions": []}


def _deterministic_research(question: str) -> dict[str, Any]:
    subs = []
    for keyword in ["定义", "实现", "对比", "未来", "风险"]:
        if keyword in question or len(question) > 30:
            subs.append(f"{question} 的{keyword}")
    return {
        "answer": f"关于 '{question}' 的研究",
        "citations": [],
        "confidence": 0.5,
        "sub_questions": subs[:3],
    }


async def _deep_research_tree_async(
    topic: str,
    *,
    caller: ResearchCaller,
    max_depth: int,
    max_branches: int,
    max_nodes: int,
) -> dict[str, Any]:
    if not topic or not topic.strip():
        raise OskillError("deep_research_tree: topic must not be empty")

    nodes: list[dict[str, Any]] = []
    counter = [0]

    def add_node(title: str, depth: int, parent: str | None) -> str:
        counter[0] += 1
        node_id = f"n{counter[0]}"
        nodes.append(
            {"id": node_id, "title": title, "depth": depth, "parent": parent, "children": []}
        )
        if parent is not None:
            for node in nodes:
                if node["id"] == parent:
                    node["children"].append(node_id)
                    break
        return node_id

    async def expand(title: str, depth: int, parent: str | None) -> None:
        if len(nodes) >= max_nodes or depth > max_depth:
            return
        node_id = add_node(title, depth, parent)
        if depth == max_depth:
            return
        subtopics = await _subtopics(title, caller=caller, max_branches=max_branches)
        for subtopic in subtopics[:max_branches]:
            if len(nodes) >= max_nodes:
                break
            await expand(subtopic, depth + 1, node_id)

    await expand(topic, 1, None)
    return {
        "root": topic,
        "node_count": len(nodes),
        "depth": max((node["depth"] for node in nodes), default=1),
        "nodes": nodes,
    }


async def _subtopics(
    title: str,
    *,
    caller: ResearchCaller,
    max_branches: int,
) -> list[str]:
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
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    lines = [
        line.strip(" -1234567890.\t")
        for line in str(content).splitlines()
        if line.strip()
    ]
    return [line for line in lines if len(line) > 2][:max_branches] or [f"{title} 综述"]
