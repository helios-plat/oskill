"""Tests for ingest_substrate pipeline."""

from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from oskill.ingest_substrate import ingest_substrate, IngestResult, _sha256, _chunk_text, _slugify


class TestHelpers:
    def test_sha256_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = _sha256(f)
        assert len(h) == 64
        assert h == _sha256(f)  # deterministic

    def test_sha256_different_files(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("aaa")
        f2.write_text("bbb")
        assert _sha256(f1) != _sha256(f2)

    def test_chunk_text_empty(self):
        assert _chunk_text("") == []

    def test_chunk_text_short(self):
        chunks = _chunk_text("Hello world")
        assert chunks == ["Hello world"]

    def test_chunk_text_long(self):
        text = "paragraph\n\n".join(["word " * 100] * 10)
        chunks = _chunk_text(text, size=512)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 520  # small tolerance

    def test_slugify(self):
        assert _slugify("Hello World! PDF") == "hello-world-pdf"
        assert _slugify("__test__") == "test"


class TestIngestSubstrate:
    async def test_unsupported_storage_raises(self, tmp_path, simple_txt):
        from oprim.errors import IngestError

        with pytest.raises(IngestError, match="not supported"):
            await ingest_substrate(simple_txt, source={"type": "test"}, target_storage="s3")

    async def test_file_not_found_raises(self, stratum_home):
        with pytest.raises(FileNotFoundError):
            await ingest_substrate(Path("/nonexistent/file.txt"), source={"type": "test"})

    async def test_duplicate_returns_duplicate_of(self, stratum_schema, simple_txt):
        """If file was already ingested, IngestResult.duplicate_of is set."""
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import meta_db_path
        from datetime import datetime, timezone

        file_hash = _sha256(simple_txt)
        db_p = meta_db_path()
        db = open_meta_db(db_p)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrates (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                "EXISTINGID012345678901234",
                "EXISTINGID012345678901234",
                "existing",
                "",
                "",
                file_hash,
                0,
                '{"medium":"markdown_note"}',
                now,
                now,
            ],
        )
        db.close()

        result = await ingest_substrate(simple_txt, source={"type": "test"})
        assert result.duplicate_of == "EXISTINGID012345678901234"

    async def test_successful_ingest_text_file(self, stratum_schema, simple_txt):
        """End-to-end ingest of a text file (mocking embedding)."""
        with patch("oskill.ingest_substrate.embed_text", return_value=[[0.1] * 1024]):
            with patch(
                "oskill.knowledge.classify_inbox_file.detect_mime", return_value="text/markdown"
            ):
                result = await ingest_substrate(simple_txt, source={"type": "inbox_local"})

        assert result.substrate_id
        assert result.medium in {"markdown_note", "other"}
        assert result.duplicate_of is None
        assert result.elapsed_seconds > 0

    async def test_ingest_creates_substrate_in_db(self, stratum_schema, simple_md):
        """After ingest, substrate should be in meta_db."""
        from oprim.meta_db import open_meta_db
        from oskill.knowledge._context import meta_db_path

        with patch("oskill.ingest_substrate.embed_text", return_value=[[0.1] * 1024]):
            with patch(
                "oskill.knowledge.classify_inbox_file.detect_mime", return_value="text/markdown"
            ):
                result = await ingest_substrate(simple_md, source={"type": "inbox_local"})

        db = open_meta_db(meta_db_path())
        rows = db.fetchall("SELECT id FROM substrates WHERE id = ?", [result.substrate_id])
        db.close()
        assert len(rows) == 1

    async def test_ingest_creates_fulltext_index_entry(self, stratum_schema, simple_md):
        """After ingest, substrate should be searchable via tantivy."""
        from oprim.fulltext import open_fulltext_index
        from oskill.knowledge._context import tantivy_path

        with patch("oskill.ingest_substrate.embed_text", return_value=[[0.1] * 1024]):
            with patch(
                "oskill.knowledge.classify_inbox_file.detect_mime", return_value="text/markdown"
            ):
                result = await ingest_substrate(simple_md, source={"type": "inbox_local"})

        ft_idx = open_fulltext_index(tantivy_path())
        hits = ft_idx.search("Test Note")
        assert any(h.id == result.substrate_id for h in hits)
