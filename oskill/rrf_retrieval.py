"""oskill.rrf_retrieval — RRF 混合检索 (TencentDB Agent Memory 机制 3O 内化)。

稀疏 (BM25) + 稠密 (向量, 调用方注入) 双路召回 → **Reciprocal Rank Fusion**
融合 → 预算截断。纯确定性算法 (源自 TencentDB search-utils, RRF_K=60):
  * bm25_score — BM25 打分 (纯 Python, 无第三方);
  * rrf_merge — Σ 1/(k + rank + 1), 多列表融合去重;
  * RetrievalBudget — 条目数/字符/超时上限, 防记忆淹没上下文窗口;
  * hybrid_search — 融合 + 预算截断一站式。

零 veya 反向依赖: 纯算法; 向量结果由调用方提供。
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from typing import Any

RRF_K = 60


def tokenize(text: str) -> list[str]:
    """简单 tokenize (英文词 + 中文 bigram, 无第三方分词)。"""
    tokens: list[str] = re.findall(r"[a-z][a-z0-9-]{1,}", text.lower())
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(seg) <= 2:
            tokens.append(seg)
        else:
            tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
    return tokens


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    *,
    df: dict[str, int],
    n_docs: int,
    avg_dl: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """BM25 打分 (Okapi)。

    Args:
        query_tokens: 查询 token。
        doc_tokens: 文档 token。
        df: 词 → 含该词的文档数。
        n_docs: 文档总数。
        avg_dl: 平均文档长度。
        k1 / b: BM25 超参。

    Returns:
        BM25 分数。

    Example:
        >>> s = bm25_score(["a"], ["a", "b"], df={"a": 1}, n_docs=10, avg_dl=2)
        >>> s > 0
        True
    """
    dl = len(doc_tokens)
    idf = lambda n: math.log((n_docs - n + 0.5) / (n + 0.5) + 1.0)  # noqa: E731
    score = 0.0
    freq: dict[str, int] = {}
    for tok in doc_tokens:
        freq[tok] = freq.get(tok, 0) + 1
    for tok in query_tokens:
        tf = freq.get(tok, 0)
        if tf == 0:
            continue
        n = df.get(tok, 0)
        if n == 0:
            continue
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
        score += idf(n) * tf_norm
    return score


@dataclass(frozen=True)
class RetrievalBudget:
    """检索预算 (防记忆淹没上下文窗口, 源自 TencentDB)。

    Attributes:
        max_items: 最大返回条目数。
        max_chars: 最大总字符数。
        timeout_s: 检索超时秒数 (None 不限制)。
    """

    max_items: int = 8
    max_chars: int = 4000
    timeout_s: float | None = None


def rrf_merge(
    lists: list[list[dict[str, Any]]],
    *,
    key: str = "id",
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion: Σ 1/(k + rank + 1)。

    Args:
        lists: 多路排序列表 (每项含 key 字段)。
        key: 去重键字段名。
        k: RRF 常数 (默认 60)。

    Returns:
        融合后按分数降序 (附 rrf_score)。

    Example:
        >>> r = rrf_merge([[{"id": "a"}, {"id": "b"}], [{"id": "b"}]])
        >>> r[0]["id"]
        'b'
    """
    scores: dict[str, dict[str, Any]] = {}
    for ranked in lists:
        for rank, item in enumerate(ranked):
            item_id = item.get(key)
            if item_id is None:
                continue
            score = 1.0 / (k + rank + 1)
            existing = scores.get(item_id)
            if existing is None:
                merged = dict(item)
                merged["rrf_score"] = score
                scores[item_id] = merged
            else:
                existing["rrf_score"] = existing.get("rrf_score", 0.0) + score
    return sorted(scores.values(), key=lambda x: -x.get("rrf_score", 0.0))


def _chars(item: dict[str, Any]) -> int:
    """条目字符数 (text/content/summary 字段优先)。"""
    for field_name in ("text", "content", "summary"):
        value = item.get(field_name)
        if isinstance(value, str):
            return len(value)
    return 0


def hybrid_search(
    fts_results: list[dict[str, Any]],
    vector_results: list[dict[str, Any]],
    *,
    budget: RetrievalBudget | None = None,
    key: str = "id",
) -> list[dict[str, Any]]:
    """稀疏 + 稠密双路 → RRF 融合 → 预算截断。

    Args:
        fts_results: 稀疏 (BM25/FTS) 排序结果。
        vector_results: 稠密 (向量) 排序结果 (调用方注入)。
        budget: 检索预算; None 用默认。
        key: 去重键。

    Returns:
        融合结果 (受 max_items/max_chars 截断)。
    """
    budget = budget or RetrievalBudget()
    start = time.monotonic()
    merged = rrf_merge([fts_results, vector_results], key=key)
    capped: list[dict[str, Any]] = []
    total_chars = 0
    for item in merged:
        if len(capped) >= budget.max_items:
            break
        total_chars += _chars(item)
        if total_chars > budget.max_chars:
            break
        capped.append(item)
        if budget.timeout_s is not None and time.monotonic() - start > budget.timeout_s:
            break
    return capped
