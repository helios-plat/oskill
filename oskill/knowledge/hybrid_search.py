"""Local hybrid search: BM25 (tantivy) + dense vector (lancedb) fused with RRF."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

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
    citation: dict | None = None


async def hybrid_search(
    query: str,
    top_k: int = 20,
    medium_filter: list[str] | None = None,
    type_filter: list[str] | None = None,
    mode: Literal["strict", "augmented"] = "augmented",
    view_id: str | None = None,
    pinned_boost: float = 1.5,
    return_citations: bool = True,
) -> list[SearchResult]:
    """Hybrid search: BM25 + dense vector + RRF fusion.

    Args:
        mode: "strict" — substrate hits only, no LLM.
              "augmented" — substrate + LLM general knowledge fallback on zero hits.
        view_id: View filter (Phase 13, reserved — not applied in Phase 1.5).
        pinned_boost: Multiply score of is_pinned substrates by this factor (re-sorts).
        return_citations: Populate citation field on each result.
    """
    if view_id is not None:
        log.info("oskill.hybrid_search.view_id_reserved", view_id=view_id)

    bm25_hits = _bm25_search(query, top_k * 2)
    dense_hits = await _dense_search(query, top_k * 2)

    fused = _rrf_fuse(bm25_hits, dense_hits, k=_RRF_K, top_k=top_k * 2)

    if pinned_boost != 1.0 and fused:
        fused = _boost_pinned(fused, pinned_boost)

    enriched = _enrich(fused, return_citations=return_citations)
    filtered = _apply_filters(enriched, medium_filter, type_filter)

    if mode == "augmented" and not filtered:
        filtered = await _llm_augmented(query)

    log.info("oskill.hybrid_search.done", query=query[:80], mode=mode, results=len(filtered[:top_k]))
    return filtered[:top_k]


# ── BM25 ──────────────────────────────────────────────────────────────────────

def _bm25_search(query: str, top_k: int) -> list[tuple[str, float]]:
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


# ── Dense vector ──────────────────────────────────────────────────────────────

async def _dense_search(query: str, top_k: int) -> list[tuple[str, float]]:
    db_path = lancedb_path()
    if not db_path.exists():
        return []
    try:
        vecs = embed_text([query], provider="qwen3_dashscope", dim=_VECTOR_DIM)
        vdb = open_vector_db(db_path, table_name=_TABLE_NAME, dim=_VECTOR_DIM)
        records = vdb.search(vecs[0], top_k=top_k)
        results = []
        for r in records:
            sub_id = r.id.split("#")[0]
            score = r.metadata.get("_distance", 0.0)
            results.append((sub_id, 1.0 / (1.0 + float(score))))
        return results
    except Exception as e:
        log.warning("oskill.hybrid_search.dense_error", error=str(e))
        return []


# ── RRF ───────────────────────────────────────────────────────────────────────

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
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]


# ── Pinned boost ──────────────────────────────────────────────────────────────

def _boost_pinned(
    fused: list[tuple[str, float]],
    boost: float,
) -> list[tuple[str, float]]:
    """Multiply score of is_pinned substrates, then re-sort."""
    pinned = _get_pinned_ids([sid for sid, _ in fused])
    boosted = [(sid, score * boost if sid in pinned else score) for sid, score in fused]
    return sorted(boosted, key=lambda x: x[1], reverse=True)


def _get_pinned_ids(substrate_ids: list[str]) -> set[str]:
    db_p = meta_db_path()
    if not db_p.exists() or not substrate_ids:
        return set()
    try:
        db = open_meta_db(db_p)
        ph = ",".join("?" * len(substrate_ids))
        rows = db.fetchall(
            f"SELECT id FROM substrate WHERE id IN ({ph}) AND is_pinned = true",
            substrate_ids,
        )
        db.close()
        return {r[0] for r in rows}
    except Exception as e:
        log.warning("oskill.hybrid_search.get_pinned_error", error=str(e))
        return set()


# ── Enrich ────────────────────────────────────────────────────────────────────

def _enrich(fused: list[tuple[str, float]], return_citations: bool = True) -> list[SearchResult]:
    """Fetch substrate metadata from DuckDB and build SearchResult list."""
    if not fused:
        return []
    db_p = meta_db_path()
    if not db_p.exists():
        return [
            SearchResult(
                type="substrate", id=sid, title=sid, score=sc, highlight=None,
                citation=_make_citation(sid, return_citations),
            )
            for sid, sc in fused
        ]
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
                citation=_make_citation(sid, return_citations),
            ))
        else:
            results.append(SearchResult(
                type="substrate", id=sid, title=sid, score=score, highlight=None,
                citation=_make_citation(sid, return_citations),
            ))
    return results


def _make_citation(substrate_id: str, return_citations: bool) -> dict | None:
    if not return_citations:
        return None
    fragment_id = f"{substrate_id}#0"
    return {
        "substrate_id": substrate_id,
        "fragment_id": fragment_id,
        "anchor": {"section": None, "char_start": 0, "char_end": 0},
        "deep_link": f"stratum://substrate/{substrate_id}/#{fragment_id}",
    }


# ── Filters ───────────────────────────────────────────────────────────────────

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


# ── LLM augmented fallback (mode=augmented, zero substrate hits) ──────────────

async def _llm_augmented(query: str) -> list[SearchResult]:
    try:
        from oprim.llm import llm_call
        response = await llm_call(
            prompt=f"Answer briefly based on your knowledge: {query}",
            provider="qwen3_dashscope",
        )
        return [SearchResult(
            type="llm_augmented",
            id="llm-augmented-0",
            title="General Knowledge",
            score=0.5,
            highlight=str(response)[:500],
            metadata={"source": "llm_augmented"},
            citation=None,
        )]
    except Exception as e:
        log.warning("oskill.hybrid_search.llm_augment_failed", error=str(e))
        return []
