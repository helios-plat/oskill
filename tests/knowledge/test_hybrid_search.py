"""Tests for hybrid_search."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from oskill.knowledge.hybrid_search import hybrid_search, _rrf_fuse, SearchResult


class TestRRFFuse:
    def test_rrf_combines_two_lists(self):
        list_a = [("a", 1.0), ("b", 0.8), ("c", 0.5)]
        list_b = [("b", 1.0), ("d", 0.7), ("a", 0.4)]
        result = _rrf_fuse(list_a, list_b)
        ids = [r[0] for r in result]
        # 'a' and 'b' appear in both lists → should rank high
        assert "a" in ids
        assert "b" in ids

    def test_rrf_empty_lists(self):
        assert _rrf_fuse([], []) == []

    def test_rrf_single_list(self):
        list_a = [("x", 1.0), ("y", 0.5)]
        result = _rrf_fuse(list_a, [])
        assert result[0][0] == "x"


class TestHybridSearch:
    async def test_returns_empty_when_no_indices(self, stratum_home):
        """Empty indices → empty results (no error)."""
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            result = await hybrid_search("test query")
        assert result == []

    async def test_bm25_hit(self, stratum_home):
        """Document in fulltext index → shows up in results."""
        from oprim.fulltext import open_fulltext_index
        from oprim.fulltext.tantivy import FulltextDoc
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import tantivy_path, meta_db_path
        import json
        from datetime import datetime, timezone

        # Populate tantivy
        ft_path = tantivy_path()
        ft_path.mkdir(parents=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([FulltextDoc(id="sub001", fields={"title": "kelly criterion finance", "content": "Kelly formula for optimal betting size"})])

        # Populate meta_db
        db_p = meta_db_path()
        db = open_meta_db(db_p)
        db.migrate(Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations"))
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
        """medium_filter should exclude non-matching results."""
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
        db.migrate(Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations"))
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
        """type_filter='substrate' should only return substrate results."""
        with patch("oskill.knowledge.hybrid_search.embed_text", return_value=[[0.1] * 1024]):
            results = await hybrid_search("query", type_filter=["substrate"])
        assert all(r.type == "substrate" for r in results)
