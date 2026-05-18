"""Tests for detect_duplicate_substrate."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from oskill.knowledge.detect_duplicate_substrate import detect_duplicate_substrate


class TestDetectDuplicateSubstrate:
    async def test_no_db_returns_none(self, stratum_home):
        """No meta.duckdb → None (not an error)."""
        result = await detect_duplicate_substrate("abc123")
        assert result is None

    async def test_hash_match_returns_id(self, stratum_home):
        """SHA-256 match → return existing substrate_id."""
        from oprim.meta_db import open_meta_db
        from oprim.meta_db.duckdb import MetaDB
        from oskill.knowledge._context import meta_db_path
        db_p = meta_db_path()
        db = open_meta_db(db_p)
        db.migrate(Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations"))
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["EXISTING01234567890123456", "EXISTING01234567890123456", "test", "", "", "deadbeef" * 8, 0, '{"medium":"paper"}', now, now]
        )
        db.close()

        result = await detect_duplicate_substrate("deadbeef" * 8)
        assert result == "EXISTING01234567890123456"

    async def test_no_match_returns_none(self, stratum_home):
        """Non-matching hash → None."""
        from oprim.meta_db import open_meta_db
        from oprim.meta_db.duckdb import MetaDB
        from oskill.knowledge._context import meta_db_path
        db_p = meta_db_path()
        db = open_meta_db(db_p)
        db.migrate(Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations"))
        db.close()

        result = await detect_duplicate_substrate("nonexistenthashabc123456789012345678901234567890123456789012345")
        assert result is None

    async def test_embedding_param_ignored_phase1(self, stratum_home):
        """Phase 1: embedding param is accepted but not used."""
        result = await detect_duplicate_substrate("abc123", embedding=[0.1] * 1024)
        assert result is None
