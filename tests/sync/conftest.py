"""Shared fixtures for oskill.sync tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from oprim.meta_db.duckdb import open_meta_db
from oprim.storage.protocol import StorageFile, UploadResult

_MIGRATIONS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "oprim" / "oprim" / "meta_db" / "migrations"
)


@pytest.fixture()
def db(tmp_path: Path):
    m = open_meta_db(tmp_path / "meta.duckdb")
    m.migrate(_MIGRATIONS_DIR)
    yield m
    m.close()


def _make_storage_mock() -> MagicMock:
    """Return a mock StorageAdapter with sensible async defaults."""
    storage = MagicMock()
    storage.upload = AsyncMock(
        return_value=UploadResult(file_id="remote_id_1", size=100, md5="abc")
    )
    storage.download = AsyncMock()

    async def _empty_list(*args, **kwargs):
        return
        yield  # make it an async generator

    storage.list_files = _empty_list
    return storage


@pytest.fixture()
def storage():
    return _make_storage_mock()


def seed_substrate(db, sub_id: str = "sub_1", ulid: str = "01HX") -> None:
    db.execute(
        "INSERT INTO substrate (id, ulid, title, mime, meta_json) VALUES (?, ?, ?, ?, ?)",
        [sub_id, ulid, "Test Doc", "application/pdf", "{}"],
    )


def seed_note(db, note_id: str = "note_1", title: str = "My Note") -> None:
    db.execute(
        "INSERT INTO note (id, title, content, wikilinks, meta_json) VALUES (?, ?, ?, ?, ?)",
        [note_id, title, "content", "[]", "{}"],
    )


def seed_concept(db, concept_id: str = "c_1", name: str = "Alpha") -> None:
    db.execute(
        "INSERT INTO concept (id, name, aliases, wikilink, source_ids, meta_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [concept_id, name, None, name.lower(), "[]", "{}"],
    )


def make_event_dict(
    event_type: str,
    aggregate_id: str | None,
    payload: dict,
    device_id: str = "device_B",
    user_id: str = "u1",
    seq: int = 1,
) -> dict:
    return {
        "id": seq,
        "device_id": device_id,
        "user_id": user_id,
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "payload": payload,
        "created_at": "2026-05-20T10:00:00",
        "seq": seq,
    }


def jsonl_content(*event_dicts: dict) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in event_dicts)
