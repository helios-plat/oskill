"""oskill.mcp_tool_route — 根据自然语言自动匹配最佳 MCP 工具路由算子.

组合 oprim.embedding_gen（查询 + 工具描述向量化）+ oskill.rag_rerank（语义重排），
从 MCP 工具清单中选出与自然语言请求最匹配的工具。stateless。

Example:
    >>> r = await mcp_tool_route(
    ...     "查一下今天的天气", tools=[{"name": "weather", "description": "查询天气"}],
    ...     embedder=emb, store=store,
    ... )
    >>> r["best_tool"]["name"]
    'weather'
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class RouteEmbedder(Protocol):
    """向量化协议。"""

    async def __call__(
        self, *, text: str, model: str = "text-embedding-3-small"
    ) -> list[float]: ...


@runtime_checkable
class RouteStore(Protocol):
    """检索存储协议（工具描述须已向量化入库）。"""

    async def search(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]: ...


async def mcp_tool_route(
    query: str,
    *,
    tools: list[dict[str, Any]],
    embedder: RouteEmbedder,
    store: RouteStore,
    top_k: int = 1,
    model: str = "text-embedding-3-small",
) -> dict[str, Any]:
    """自然语言 → 最佳 MCP 工具路由。

    Args:
        query: 自然语言请求。
        tools: 候选工具清单，每项 {"name": str, "description": str, ...}。
        embedder: 嵌入调用器（注入）。
        store: 检索存储（注入；工具描述向量须已 upsert，chunk_id=tool name）。
        top_k: 候选返回数。
        model: 嵌入模型名。

    Returns:
        {"best_tool": dict, "candidates": [dict], "scores": [float]}

    Raises:
        OskillError: query 为空 / tools 为空。
    """
    if not query or not query.strip():
        raise OskillError("mcp_tool_route: query must not be empty")
    if not tools:
        raise OskillError("mcp_tool_route: tools must not be empty")

    from oskill._rag_rerank import rag_rerank

    # 工具描述已向量化入库（chunk_id = 工具名）；兜底：直接文本匹配打分
    try:
        ranked = await rag_rerank(
            query,
            embedder=embedder,
            store=store,
            top_k=max(top_k, len(tools)),
            oversample=3,
            model=model,
        )
        by_id = {str(t.get("name")): t for t in tools}
        candidates: list[dict[str, Any]] = []
        for hit in ranked:
            tool = by_id.get(str(hit.get("chunk_id")))
            if tool is not None:
                candidates.append({**tool, "score": hit.get("score", 0.0)})
    except OskillError:
        # 无向量库场景：描述关键词命中兜底
        candidates = _keyword_fallback(query, tools)

    if not candidates:
        raise OskillError("mcp_tool_route: no tool matched the query")

    candidates.sort(key=lambda t: float(t.get("score", 0.0)), reverse=True)
    return {
        "best_tool": candidates[0],
        "candidates": candidates[:top_k],
        "scores": [float(c.get("score", 0.0)) for c in candidates[:top_k]],
    }


def _keyword_fallback(query: str, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """无向量库兜底：名称/描述关键词重合度打分。"""
    q = query.lower()
    words = [w for w in re_find_words(q) if len(w) > 1]
    scored: list[dict[str, Any]] = []
    for t in tools:
        hay = f"{t.get('name', '')} {t.get('description', '')}".lower()
        hits = sum(1 for w in words if w in hay)
        scored.append({**t, "score": round(hits / max(1, len(words)), 4)})
    scored.sort(key=lambda t: t["score"], reverse=True)
    return [s for s in scored if s["score"] > 0] or scored[:1]


import re as _re  # noqa: E402


def re_find_words(text: str) -> list[str]:
    return _re.findall(r"[a-z0-9\u4e00-\u9fff]+", text)
