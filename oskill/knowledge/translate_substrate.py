"""Translate a substrate's markdown content and store as a derivative."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import oprim.meta_db as _oprim_meta_db_mod
from ulid import ULID

from oprim._logging import log
from oprim.errors import StratumError
from oprim.meta_db import open_meta_db
from oprim.translate import TerminologyGlossary, TranslationResult, translate_document

from oskill.knowledge._context import meta_db_path

_MIGRATIONS_DIR = Path(_oprim_meta_db_mod.__file__).parent / "migrations"


@dataclass
class TranslateResult:
    derivative_id: str
    substrate_id: str
    target_lang: str
    provider: str
    chunks_translated: int
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    cost_usd: float = 0.0
    chunk_results: list[TranslationResult] = field(default_factory=list)


def translate_substrate(
    substrate_id: str,
    target_lang: str,
    source_lang: str = "auto",
    provider: str = "deepseek",
    *,
    model: str | None = None,
    domain: str | None = None,
    max_chars: int = 2000,
    checkpoint_dir: Path | None = None,
    glossary: TerminologyGlossary | None = None,
    overwrite: bool = False,
) -> TranslateResult:
    """Translate a substrate's markdown content into target_lang.

    Reads the substrate's markdown derivative (falling back to source_path for
    plain-text files), translates via the chosen provider, and writes a new
    derivative row with ``kind = "translation_<target_lang>"``.

    Args:
        substrate_id: ID of the substrate to translate.
        target_lang: ISO language code for the translation target (e.g. "zh", "en").
        source_lang: ISO language code for the source, or "auto" to let the provider detect.
        provider: Translation provider name ("deepseek", "claude", "qwen3", "gemini").
        model: Optional model override for the provider.
        domain: Optional domain hint ("academic", "literary", "technical").
        max_chars: Max characters per translation chunk.
        checkpoint_dir: Directory for checkpoint files (enables resumable translation).
        glossary: Optional TerminologyGlossary for domain-specific terms.
        overwrite: If True, replace an existing translation derivative.

    Returns:
        TranslateResult with derivative_id and cost summary.

    Raises:
        StratumError: Substrate not found, no translatable content, or DB error.
    """
    db_path = meta_db_path()
    if not db_path.exists():
        raise StratumError(f"MetaDB not found at {db_path}")

    db = open_meta_db(db_path)
    db.migrate(_MIGRATIONS_DIR)

    # Load substrate record
    rows = db.execute(
        "SELECT id, source_path, meta_json FROM substrate WHERE id = ?",
        [substrate_id],
    ).fetchall()
    if not rows:
        db.close()
        raise StratumError(f"Substrate not found: {substrate_id}")

    _id, source_path, meta_json_str = rows[0]

    derivative_kind = f"translation_{target_lang}"
    if not overwrite:
        existing = db.execute(
            "SELECT id FROM derivative WHERE substrate_id = ? AND kind = ?",
            [substrate_id, derivative_kind],
        ).fetchall()
        if existing:
            db.close()
            existing_id = existing[0][0]
            log.info(
                "translate_substrate.already_exists",
                derivative_id=existing_id,
                substrate_id=substrate_id,
                kind=derivative_kind,
            )
            return TranslateResult(
                derivative_id=existing_id,
                substrate_id=substrate_id,
                target_lang=target_lang,
                provider=provider,
                chunks_translated=0,
            )

    # Get translatable content: prefer markdown derivative, fall back to source file
    markdown_rows = db.execute(
        "SELECT content FROM derivative WHERE substrate_id = ? AND kind = 'markdown' LIMIT 1",
        [substrate_id],
    ).fetchall()

    if markdown_rows and markdown_rows[0][0]:
        source_text: str = markdown_rows[0][0]
    elif source_path and Path(source_path).exists():
        source_text = Path(source_path).read_text(encoding="utf-8", errors="replace")
    else:
        db.close()
        raise StratumError(
            f"No translatable content for substrate {substrate_id}: "
            "no markdown derivative and source_path not accessible"
        )

    effective_source = "auto" if source_lang == "auto" else source_lang

    checkpoint_path: Path | None = None
    if checkpoint_dir:
        checkpoint_dir = Path(checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{substrate_id}_{target_lang}.json"

    log.info(
        "translate_substrate.start",
        substrate_id=substrate_id,
        target_lang=target_lang,
        provider=provider,
        chars=len(source_text),
    )

    translated_text, chunk_results = translate_document(
        source_text,
        source_lang=effective_source,
        target_lang=target_lang,
        provider=provider,
        checkpoint_path=checkpoint_path,
        max_chars=max_chars,
        domain=domain,
        model=model,
        glossary=glossary,
    )

    total_in = sum(r.input_tokens for r in chunk_results)
    total_out = sum(r.output_tokens for r in chunk_results)
    total_cost = sum(r.cost_usd for r in chunk_results)

    derivative_id = str(ULID())
    now = datetime.now(timezone.utc).isoformat()
    meta = json.dumps({
        "source_lang": effective_source,
        "target_lang": target_lang,
        "provider": provider,
        "chunks": len(chunk_results),
        "cost_usd": round(total_cost, 6),
    })

    if overwrite:
        db.execute(
            "DELETE FROM derivative WHERE substrate_id = ? AND kind = ?",
            [substrate_id, derivative_kind],
        )

    db.execute(
        """INSERT INTO derivative (id, substrate_id, kind, content, meta_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [derivative_id, substrate_id, derivative_kind, translated_text, meta, now],
    )
    db.execute(
        """INSERT INTO changefeed_local (seq, table_name, row_id, op, payload)
           VALUES (nextval('changefeed_seq'), ?, ?, ?, ?)""",
        [
            "derivative",
            derivative_id,
            "insert",
            json.dumps({
                "substrate_id": substrate_id,
                "kind": derivative_kind,
                "derivative_id": derivative_id,
            }),
        ],
    )
    db.close()

    log.info(
        "translate_substrate.done",
        derivative_id=derivative_id,
        substrate_id=substrate_id,
        target_lang=target_lang,
        provider=provider,
        chunks=len(chunk_results),
        cost_usd=round(total_cost, 6),
    )

    return TranslateResult(
        derivative_id=derivative_id,
        substrate_id=substrate_id,
        target_lang=target_lang,
        provider=provider,
        chunks_translated=len(chunk_results),
        total_tokens_in=total_in,
        total_tokens_out=total_out,
        cost_usd=total_cost,
        chunk_results=chunk_results,
    )
