"""Tests for hybrid_search."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from oskill.knowledge.hybrid_search import (
    hybrid_search, _rrf_fuse, _boost_pinned, _make_citation, SearchResult,
)

_MIGRATIONS = Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations")


class TestRRFFuse:
    def test_rrf_combines_two_lists(self):
        list_a = [("a", 1.0), ("b", 0.8), ("c", 0.5)]
        list_b = [("b", 1.0), ("d", 0.7), ("a", 0.4)]
        result = _rrf_fuse(list_a, list_b)
        ids = [r[0] for r in result]
        assert "a" in ids
        assert "b" in ids

    def test_rrf_empty_lists(self):
        assert _rrf_fuse([], []) == []

    def test_rrf_single_list(self):
        list_a = [("x", 1.0), ("y", 0.5)]
        result = _rrf_fuse(list_a, [])
        assert result[0][0] == "x"


class TestBoostPinned:
    def test_boost_pinned_substrate(self, stratum_home):
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import meta_db_path
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db = open_meta_db(meta_db_path())
        db.migrate(_MIGRATIONS)
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, is_pinned, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["PINNED01", "PINNED01", "Pinned", "", "", "h001", 0, "{}", True, now, now],
        )
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, is_pinned, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["NORMAL01", "NORMAL01", "Normal", "", "", "h002", 0, "{}", False, now, now],
        )
        db.close()

        fused = [("NORMAL01", 0.02), ("PINNED01", 0.015)]  # normal ranks first before boost
        boosted = _boost_pinned(fused, boost=1.5)
        ids = [x[0] for x in boosted]
        assert ids[0] == "PINNED01"  # pinned promoted to top

    def test_boost_no_pinned(self, stratum_home):
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import meta_db_path
        db = open_meta_db(meta_db_path())
        db.migrate(_MIGRATIONS)
        db.close()

        fused = [("A", 0.5), ("B", 0.3)]
        boosted = _boost_pinned(fused, boost=1.5)
        assert [x[0] for x in boosted] == ["A", "B"]


class TestMakeCitation:
    def test_citation_structure(self):
        c = _make_citation("SUBID001", return_citations=True)
        assert c is not None
        assert c["substrate_id"] == "SUBID001"
        assert c["fragment_id"] == "SUBID001#0"
        assert "deep_link" in c
        assert c["deep_link"].startswith("stratum://substrate/")
        assert "anchor" in c

    def test_no_citation_when_disabled(self):
        assert _make_citation("SUBID001", return_citations=False) is None


class TestHybridSearch:
    async def test_returns_empty_when_no_indices(self, stratum_home):
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            result = await hybrid_search("test query")
        assert result == []

    async def test_bm25_hit(self, stratum_home):
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        from datetime import datetime, timezone

        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([FulltextDoc(id="sub001", fields={"title": "kelly criterion finance", "content": "Kelly formula for optimal betting size"})])

        db_p = meta_db_path()
        db = open_meta_db(db_p)
        db.migrate(_MIGRATIONS)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["sub001", "sub001", "kelly criterion finance", "", "", "hash001", 0, '{"medium":"paper"}', now, now]
        )
        db.close()

        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search.open_vector_db") as mock_vdb:
                mock_vdb.return_value.search.return_value = []
                results = await hybrid_search("kelly criterion")

        assert any(r.id == "sub001" for r in results)

    async def test_medium_filter(self, stratum_home):
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        from datetime import datetime, timezone

        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([
            FulltextDoc(id="paper001", fields={"title": "finance paper", "content": "finance content"}),
            FulltextDoc(id="book001", fields={"title": "finance book", "content": "finance content"}),
        ])

        db_p = meta_db_path()
        db = open_meta_db(db_p)
        db.migrate(_MIGRATIONS)
        now = datetime.now(timezone.utc).isoformat()
        db.execute("INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   ["paper001", "paper001", "finance paper", "", "", "h001", 0, '{"medium":"paper"}', now, now])
        db.execute("INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   ["book001", "book001", "finance book", "", "", "h002", 0, '{"medium":"book"}', now, now])
        db.close()

        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search.open_vector_db") as mock_vdb:
                mock_vdb.return_value.search.return_value = []
                results = await hybrid_search("finance", medium_filter=["paper"])

        assert all(r.metadata.get("medium") == "paper" for r in results)

    async def test_type_filter(self, stratum_home):
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            results = await hybrid_search("query", type_filter=["substrate"])
        assert all(r.type == "substrate" for r in results)

    async def test_mode_strict_does_not_call_llm(self, stratum_home):
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search._llm_augmented", new=AsyncMock()) as mock_llm:
                results = await hybrid_search("no hits query", mode="strict")
        mock_llm.assert_not_called()
        assert results == []

    async def test_mode_augmented_calls_llm_on_zero_hits(self, stratum_home):
        llm_result = SearchResult(
            type="llm_augmented", id="llm-0", title="LLM Answer",
            score=0.5, highlight="answer text", citation=None,
        )
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search._llm_augmented",
                       new=AsyncMock(return_value=[llm_result])):
                results = await hybrid_search("no substrate hits", mode="augmented")
        assert len(results) == 1
        assert results[0].type == "llm_augmented"

    async def test_return_citations_true(self, stratum_home):
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        from datetime import datetime, timezone

        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([FulltextDoc(id="cite001", fields={"title": "citation test", "content": "test content"})])

        db = open_meta_db(meta_db_path())
        db.migrate(_MIGRATIONS)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["cite001", "cite001", "citation test", "", "", "h001", 0, "{}", now, now],
        )
        db.close()

        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search.open_vector_db") as mv:
                mv.return_value.search.return_value = []
                results = await hybrid_search("citation", return_citations=True)

        assert results
        assert results[0].citation is not None
        assert "substrate_id" in results[0].citation
        assert "deep_link" in results[0].citation

    async def test_return_citations_false(self, stratum_home):
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        from datetime import datetime, timezone

        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([FulltextDoc(id="nocite001", fields={"title": "no citation", "content": "content"})])

        db = open_meta_db(meta_db_path())
        db.migrate(_MIGRATIONS)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["nocite001", "nocite001", "no citation", "", "", "h001", 0, "{}", now, now],
        )
        db.close()

        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search.open_vector_db") as mv:
                mv.return_value.search.return_value = []
                results = await hybrid_search("citation", return_citations=False)

        assert results
        assert results[0].citation is None

    async def test_pinned_boost_promotes_pinned(self, stratum_home):
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        from datetime import datetime, timezone

        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([
            FulltextDoc(id="normal_a", fields={"title": "finance content", "content": "finance normal text"}),
            FulltextDoc(id="pinned_b", fields={"title": "finance content", "content": "finance pinned text"}),
        ])

        db = open_meta_db(meta_db_path())
        db.migrate(_MIGRATIONS)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, is_pinned, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["normal_a", "normal_a", "Finance Normal", "", "", "h001", 0, "{}", False, now, now],
        )
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, is_pinned, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["pinned_b", "pinned_b", "Finance Pinned", "", "", "h002", 0, "{}", True, now, now],
        )
        db.close()

        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            with patch("oskill.knowledge.hybrid_search.open_vector_db") as mv:
                mv.return_value.search.return_value = []
                results = await hybrid_search("finance", pinned_boost=2.0)

        pinned_idx = next((i for i, r in enumerate(results) if r.id == "pinned_b"), None)
        normal_idx = next((i for i, r in enumerate(results) if r.id == "normal_a"), None)
        assert pinned_idx is not None and normal_idx is not None
        assert pinned_idx < normal_idx  # pinned ranked higher

    async def test_view_id_accepted_without_error(self, stratum_home):
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            result = await hybrid_search("test", view_id="some-view-id")
        assert isinstance(result, list)
