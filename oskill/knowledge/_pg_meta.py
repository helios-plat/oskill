"""PostgreSQL-backed substrate metadata store.

Bridge for the DuckDB→PostgreSQL migration: the local DuckDB meta_db
(``oprim.meta_db``) is being retired. When the ``STRATUM_PG_*`` env vars are
present (as in the stratum runtime), substrate / derivative / changefeed rows
are written to PostgreSQL (``stratum`` schema) instead of DuckDB. When they are
absent, callers fall back to the legacy DuckDB path, so other consumers of
``oprim.meta_db`` are unaffected.

Uses psycopg (v3). All rows land in the ``stratum`` schema (search_path).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any


def pg_enabled() -> bool:
    """True when the PostgreSQL substrate store is configured (STRATUM_PG_HOST set)."""
    return bool(os.getenv("STRATUM_PG_HOST"))


def _conn():
    import psycopg

    return psycopg.connect(
        host=os.environ["STRATUM_PG_HOST"],
        port=os.getenv("STRATUM_PG_PORT", "5432"),
        user=os.environ["STRATUM_PG_USER"],
        password=os.getenv("STRATUM_PG_PASSWORD", ""),
        dbname=os.environ["STRATUM_PG_DB"],
        options="-c search_path=stratum",
    )


def detect_duplicate_pg(file_hash: str) -> str | None:
    """Return an existing substrate id with the same file_hash, or None."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM substrates WHERE file_hash = %s LIMIT 1", (file_hash,))
        row = cur.fetchone()
    return row[0] if row else None


def detect_bundle_duplicate_pg(bundle_file_hash: str, user_id_hash: str) -> int:
    """Count substrates already ingested from the same bundle (D-assert)."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM substrates "
            "WHERE user_id = %s AND meta_json ->> 'bundle_file_hash' = %s",
            (user_id_hash, bundle_file_hash),
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0


def write_substrate_pg(
    *,
    substrate_id: str,
    user_id_hash: str,
    title: str,
    mime: str | None,
    source_path: str,
    file_hash: str | None,
    byte_size: int,
    meta_json: dict[str, Any],
    derivatives: dict[str, str | None],
) -> None:
    """Insert one substrate + its derivatives + a changefeed event, in one transaction."""
    from ulid import ULID

    now = datetime.now(timezone.utc)
    meta = json.dumps(meta_json, ensure_ascii=False)
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO substrates
                   (id, user_id, title, mime, source_path, file_hash, byte_size,
                    meta_json, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)""",
                (
                    substrate_id,
                    user_id_hash,
                    title,
                    mime,
                    source_path,
                    file_hash,
                    byte_size,
                    meta,
                    now,
                    now,
                ),
            )
            for kind, content in derivatives.items():
                cur.execute(
                    "INSERT INTO derivative (id, substrate_id, kind, content, created_at) "
                    "VALUES (%s,%s,%s,%s,%s)",
                    (str(ULID()), substrate_id, kind, content, now),
                )
            cur.execute(
                """INSERT INTO changefeed_local (seq, table_name, row_id, op, payload)
                   VALUES ((SELECT COALESCE(MAX(seq),0)+1 FROM changefeed_local),
                           %s,%s,%s,%s::jsonb)""",
                ("substrate", substrate_id, "insert", json.dumps({"substrate_id": substrate_id})),
            )
        conn.commit()
