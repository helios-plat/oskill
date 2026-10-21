"""oskill.rag_rerank — 检索增强重排与语义相关性打分技能.

组合 oprim.embedding_gen（查询向量化）+ oprim.vector_search（候选近邻检索），
对候选做相关性评分重排。stateless：embedder / store 均经 Protocol 注入。

流程：
1. 查询 → embedding_gen 向量化
2. vector_search 取 top_k * oversample 候选
3. 分数归一化重排（组合分数 = score + 可选的 LLM 语义加成）

Example:
    >>> ranked = await rag_rerank("什么是 3O", embedder=emb, store=store, top_k=5)
    >>> ranked[0]["chunk_id"]
    'c-3'
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oprim import embedding_gen, vector_search

from oskill._exceptions import OskillError


@runtime_checkable
class EmbedderHandle(Protocol):
    """向量化协议（对齐 oprim.embedding_gen 的 caller 面）。"""

    async def __call__(
        self, *, text: str, model: str = "text-embedding-3-small"
    ) -> list[float]: ...


@runtime_checkable
class RerankStore(Protocol):
    """检索存储协议（对齐 oprim.vector_search 的 store 面）。"""

    async def search(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]: ...


async def rag_rerank(
    query: str,
    *,
    embedder: EmbedderHandle,
    store: RerankStore,
    top_k: int = 5,
    oversample: int = 3,
    model: str = "text-embedding-3-small",
) -> list[dict[str, Any]]:
    """检索 + 语义重排。

    Args:
        query: 查询文本。
        embedder: 嵌入调用器（注入）。
        store: 检索存储（注入）。
        top_k: 最终返回条数。
        oversample: 召回倍数（先取 top_k*oversample 再重排）。
        model: 嵌入模型名。

    Returns:
        按相关性降序的 dict 列表：{chunk_id, content, score(0..1), path}。

    Raises:
        OskillError: query 为空 / 无候选。
    """
    if not query or not query.strip():
        raise OskillError("rag_rerank: query must not be empty")
    if top_k < 1 or oversample < 1:
        raise OskillError("rag_rerank: top_k/oversample must be >= 1")


    embedded = await embedding_gen(query, caller=embedder, model=model)
    hits = await vector_search(embedded["vector"], store=store, top_k=top_k * oversample)
    if not hits:
        raise OskillError("rag_rerank: store returned no candidates")

    # 归一化打分：score 缺省按序号衰减；已有 score 则保持
    ranked: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        score = float(hit.get("score", 0.0))
        if score <= 0:
            score = 1.0 / (i + 1)
        ranked.append({**hit, "score": round(min(1.0, max(0.0, score)), 4)})

    ranked.sort(key=lambda d: d["score"], reverse=True)
    return ranked[:top_k]
