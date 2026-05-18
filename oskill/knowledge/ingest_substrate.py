"""End-to-end substrate ingestion pipeline."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ulid import ULID

import oprim.meta_db as _oprim_meta_db_mod

from oprim._logging import log
from oprim.embedding import embed_text
from oprim.errors import IngestError
from oprim.fulltext import open_fulltext_index
from oprim.fulltext.tantivy import FulltextDoc
from oprim.meta_db import open_meta_db
from oprim.vector_db import open_vector_db
from oprim.vector_db.lancedb import VectorRecord

_MIGRATIONS_DIR = Path(_oprim_meta_db_mod.__file__).parent / "migrations"

from oskill.knowledge._context import (
    lancedb_path, meta_db_path, substrate_data_path, tantivy_path,
)
from oskill.knowledge.classify_inbox_file import classify_inbox_file
from oskill.knowledge.detect_duplicate_substrate import detect_duplicate_substrate
from oskill.knowledge.generate_derivative import generate_derivative

_VECTOR_DIM = 1024
_VECTOR_TABLE = "vectors_text"
_CHUNK_SIZE = 512


@dataclass
class IngestResult:
    substrate_id: str
    medium: str
    derivatives: list[str] = field(default_factory=list)
    duplicate_of: str | None = None
    elapsed_seconds: float = 0.0
    cost_usd: float = 0.0


async def ingest_substrate(
    path: Path,
    source: dict,
    target_storage: str = "local",
    user_hint: dict | None = None,
) -> IngestResult:
    """End-to-end ingestion: classify → deduplicate → parse → embed → index."""
    if target_storage != "local":
        raise IngestError(f"target_storage '{target_storage}' not supported in Phase 1 (only 'local')")

    t0 = time.monotonic()
    if not path.exists():
        raise FileNotFoundError(str(path))

    # Step 1: sha256
    file_hash = _sha256(path)

    # Step 2: deduplicate
    existing = await detect_duplicate_substrate(file_hash)
    if existing:
        log.info("oskill.ingest.duplicate", path=str(path), existing=existing)
        return IngestResult(
            substrate_id=existing, medium="", duplicate_of=existing,
            elapsed_seconds=time.monotonic() - t0,
        )

    # Step 3: classify
    hint = user_hint or {}
    use_llm = hint.pop("use_llm", False)
    classify_result = classify_inbox_file(path, use_llm=use_llm)
    medium = classify_result.medium or "other"

    # Step 4: ULID
    substrate_id = str(ULID())

    # Step 5: copy to local storage
    dest_dir = substrate_data_path() / medium
    dest_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(path.stem)[:40]
    dest = dest_dir / f"{substrate_id}--{slug}{path.suffix}"
    shutil.copy2(path, dest)

    # Step 6: generate derivatives
    derivatives_dict = await generate_derivative(substrate_id, dest, medium)
    markdown_text = derivatives_dict.get("markdown", "")

    # Step 7: chunk + embed
    chunks = _chunk_text(markdown_text)
    vector_ids: list[str] = []
    if chunks:
        try:
            embeddings = embed_text(
                [c for c in chunks],
                provider="qwen3_dashscope",
                dim=_VECTOR_DIM,
            )
            vdb_path = lancedb_path()
            vdb_path.mkdir(parents=True, exist_ok=True)
            vdb = open_vector_db(vdb_path, table_name=_VECTOR_TABLE, dim=_VECTOR_DIM)
            records = [
                VectorRecord(
                    id=f"{substrate_id}#{i}",
                    embedding=emb,
                    metadata={"substrate_id": substrate_id, "chunk_idx": i},
                )
                for i, emb in enumerate(embeddings)
            ]
            vdb.upsert(records)
            vector_ids = [r.id for r in records]
        except Exception as e:
            log.warning("oskill.ingest.embed_failed", error=str(e))

    # Step 8: write fulltext index
    try:
        ft_path = tantivy_path()
        ft_path.mkdir(parents=True, exist_ok=True)
        ft_idx = open_fulltext_index(ft_path)
        ft_idx.add([FulltextDoc(
            id=substrate_id,
            fields={
                "title": path.stem,
                "content": (markdown_text or "")[:10_000],
            },
        )])
    except Exception as e:
        log.warning("oskill.ingest.fulltext_failed", error=str(e))

    # Step 9: write meta_db
    db_p = meta_db_path()
    db_p.parent.mkdir(parents=True, exist_ok=True)
    try:
        db = open_meta_db(db_p)
        db.migrate(_MIGRATIONS_DIR)
        now = datetime.now(timezone.utc).isoformat()
        meta = json.dumps({
            "medium": medium,
            "source_type": source.get("type", "inbox_local"),
            "source": source,
        })
        db.execute(
            """INSERT INTO substrate
               (id, ulid, title, mime, source_path, file_hash, byte_size, meta_json,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [
                substrate_id, substrate_id, path.stem, "",
                str(dest), file_hash, path.stat().st_size, meta,
                now, now,
            ],
        )
        for deriv_kind in derivatives_dict:
            deriv_id = str(ULID())
            db.execute(
                "INSERT INTO derivative (id, substrate_id, kind) VALUES (?,?,?)",
                [deriv_id, substrate_id, deriv_kind],
            )
        # Step 10: changefeed_local
        db.execute(
            """INSERT INTO changefeed_local (seq, table_name, row_id, op, payload)
               VALUES (nextval('changefeed_seq'),?,?,?,?)""",
            ["substrate", substrate_id, "insert", json.dumps({"substrate_id": substrate_id})],
        )
        db.close()
    except Exception as e:
        log.warning("oskill.ingest.meta_db_failed", error=str(e))

    elapsed = time.monotonic() - t0
    log.info("oskill.ingest.done", substrate_id=substrate_id, medium=medium, elapsed=elapsed)
    return IngestResult(
        substrate_id=substrate_id,
        medium=medium,
        derivatives=list(derivatives_dict.keys()),
        elapsed_seconds=elapsed,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _chunk_text(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """Simple paragraph-based chunker."""
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            current = para[:size]
    if current:
        chunks.append(current)
    return chunks
