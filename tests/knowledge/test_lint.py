"""Tests for lint."""
from __future__ import annotations
from pathlib import Path
import pytest
import json
from datetime import datetime, timezone

from oprim.meta_db import open_meta_db
from oskill.knowledge._context import meta_db_path
from oskill.knowledge.lint import lint, LintIssue

_MIGRATIONS = Path("/home/soffy/projects/platform/oprim/oprim/meta_db/migrations")


async def _setup_db(stratum_home):
    db_p = meta_db_path()
    db = open_meta_db(db_p)
    db.migrate(_MIGRATIONS)
    return db


class TestLint:
    async def test_empty_db_is_clean(self, stratum_home):
        db = await _setup_db(stratum_home)
        db.close()
        issues = await lint()
        assert issues == []

    async def test_no_db_returns_empty(self, stratum_home):
        """No DB file → no issues (not an error)."""
        issues = await lint()
        assert issues == []

    async def test_invalid_medium_is_error(self, stratum_home):
        db = await _setup_db(stratum_home)
        now = datetime.now(timezone.utc).isoformat()
        # Use a valid-looking ULID: 26 chars, Crockford base32
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["01ARZ3NDEKTSV4RRFFQ69G5FAV", "01ARZ3NDEKTSV4RRFFQ69G5FAV", "test", "", "", "h001", 0, '{"medium":"invalid_medium"}', now, now]
        )
        db.close()
        issues = await lint(scope="substrate")
        assert any(i.rule == "schema_consistency" for i in issues)

    async def test_orphan_derivative_is_error(self, stratum_home):
        db = await _setup_db(stratum_home)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO derivative (id, substrate_id, kind) VALUES (?,?,?)",
            ["01ARZ3NDEKTSV4RRFFQ69G5FAX", "NONEXISTENT_SUBSTRATE_ID_00", "markdown"]
        )
        db.close()
        issues = await lint(scope="derivative")
        assert any(i.rule == "reference_integrity" for i in issues)

    async def test_valid_substrate_no_issues(self, stratum_home):
        db = await _setup_db(stratum_home)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO substrate (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            ["01ARZ3NDEKTSV4RRFFQ69G5FAV", "01ARZ3NDEKTSV4RRFFQ69G5FAV", "test", "", "/data/01ARZ3NDEKTSV4RRFFQ69G5FAV--test-paper.pdf", "h001", 0, '{"medium":"paper"}', now, now]
        )
        db.close()
        issues = await lint(scope="substrate")
        assert not any(i.severity == "error" for i in issues)

    async def test_scope_substrate_only(self, stratum_home):
        db = await _setup_db(stratum_home)
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO derivative (id, substrate_id, kind) VALUES (?,?,?)",
            ["01ARZ3NDEKTSV4RRFFQ69G5FAX", "NONEXISTENT00000000000000A", "markdown"]
        )
        db.close()
        issues = await lint(scope="substrate")  # Should not check derivatives
        assert not any(i.rule == "reference_integrity" for i in issues)

    async def test_lint_issue_dataclass(self, stratum_home):
        issue = LintIssue(severity="error", rule="test_rule", target_id="id1", message="test")
        assert issue.severity == "error"
        assert issue.rule == "test_rule"
