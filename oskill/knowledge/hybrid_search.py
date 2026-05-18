"""Local hybrid search: BM25 (tantivy) + dense vector (lancedb) fused with RRF."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from oprim._logging import log
from oprim.embedding import embed_text
from oprim.fulltext import open_fulltext_index
from oprim.meta_db import open_meta_db
from oprim.vector_db import open_vector_db

from oskill.knowledge._context import lancedb_path, meta_db_path, tantivy_path

_VECTOR_DIM = 1024
_TABLE_NAME = "vectors_text"
_RRF_K = 60


@dataclass
class SearchResult:
    type: str
    id: str
    title: str
    score: float
    highlight: str | None
    metadata: dict = field(default_factory=dict)


async def hybrid_search(
    query: str,
    top_k: int = 20,
    medium_filter: list[str] | None = None,
    type_filter: list[str] | None = None,
) -> list[SearchResult]:
    """Local hybrid search (Phase 1: substrate only, no concept/note cross-search).

    Steps: BM25 → dense vector → RRF fusion → metadata enrich → filter → return top_k.
    """
    bm25_hits = _bm25_search(query, top_k * 2)
    dense_hits = await _dense_search(query, top_k * 2)

    fused = _rrf_fuse(bm25_hits, dense_hits, k=_RRF_K, top_k=top_k * 2)
    enriched = _enrich(fused)
    filtered = _apply_filters(enriched, medium_filter, type_filter)

    log.info("oskill.hybrid_search.done", query=query[:80], results=len(filtered[:top_k]))
    return filtered[:top_k]


def _bm25_search(query: str, top_k: int) -> list[tuple[str, float]]:
    """Return list of (id, score) from tantivy."""
    idx_path = tantivy_path()
    if not idx_path.exists():
        return []
    try:
        idx = open_fulltext_index(idx_path)
        hits = idx.search(query, top_k=top_k)
        return [(h.id, h.score) for h in hits]
    except Exception as e:
        log.warning("oskill.hybrid_search.bm25_error", error=str(e))
        return []


async def _dense_search(query: str, top_k: int) -> list[tuple[str, float]]:
    """Return list of (id, score) from lancedb."""
    db_path = lancedb_path()
    if not db_path.exists():
        return []
    try:
        vecs = embed_text([query], provider="qwen3_dashscope", dim=_VECTOR_DIM)
        vdb = open_vector_db(db_path, table_name=_TABLE_NAME, dim=_VECTOR_DIM)
        records = vdb.search(vecs[0], top_k=top_k)
        # Parse substrate_id from composite id "{substrate_id}#{chunk_idx}"
        results = []
        for r in records:
            sub_id = r.id.split("#")[0]
            score = r.metadata.get("_distance", 0.0)
            results.append((sub_id, 1.0 / (1.0 + float(score))))
        return results
    except Exception as e:
        log.warning("oskill.hybrid_search.dense_error", error=str(e))
        return []


def _rrf_fuse(
    list_a: list[tuple[str, float]],
    list_b: list[tuple[str, float]],
    k: int = 60,
    top_k: int = 20,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion of two ranked lists."""
    scores: dict[str, float] = {}
    for rank, (item_id, _) in enumerate(list_a):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, (item_id, _) in enumerate(list_b):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


def _enrich(fused: list[tuple[str, float]]) -> list[SearchResult]:
    """Fetch substrate metadata from DuckDB."""
    if not fused:
        return []
    db_p = meta_db_path()
    if not db_p.exists():
        return [SearchResult(type="substrate", id=sid, title=sid, score=sc, highlight=None)
                for sid, sc in fused]
    try:
        db = open_meta_db(db_p)
        id_list = [sid for sid, _ in fused]
        placeholders = ",".join("?" * len(id_list))
        rows = db.fetchall(
            f"SELECT id, title, meta_json FROM substrate WHERE id IN ({placeholders})",
            id_list,
        )
        db.close()
        meta_map = {r[0]: r for r in rows}
    except Exception as e:
        log.warning("oskill.hybrid_search.enrich_error", error=str(e))
        meta_map = {}

    results = []
    for sid, score in fused:
        row = meta_map.get(sid)
        if row:
            try:
                meta = json.loads(row[2]) if row[2] else {}
            except Exception:
                meta = {}
            results.append(SearchResult(
                type="substrate", id=sid,
                title=row[1] or sid,
                score=score,
                highlight=None,
                metadata={"medium": meta.get("medium"), "source_type": meta.get("source_type")},
            ))
        else:
            results.append(SearchResult(type="substrate", id=sid, title=sid, score=score, highlight=None))
    return results


def _apply_filters(
    results: list[SearchResult],
    medium_filter: list[str] | None,
    type_filter: list[str] | None,
) -> list[SearchResult]:
    if type_filter:
        results = [r for r in results if r.type in type_filter]
    if medium_filter:
        results = [r for r in results if r.metadata.get("medium") in medium_filter]
    return results
