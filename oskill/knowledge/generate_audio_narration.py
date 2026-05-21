"""Generate audio narration for a substrate via F5-TTS."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from oprim._logging import log
from oprim.external.clients.tts_client import TtsClient
from oprim.external.gpu_lock import GpuLock
from oprim.meta_db import open_meta_db

from oskill.knowledge._context import meta_db_path, stratum_home

_CHUNK_WORDS = 120


@dataclass
class AudioNarrationResult:
    substrate_id: str
    audio_asset_id: str
    audio_path: str
    duration_seconds: float
    chunk_count: int
    cost_usd: float = 0.0


async def generate_audio_narration(
    substrate_id: str,
    voice: str = "default",
    speed: float = 1.0,
    chunk_words: int = _CHUNK_WORDS,
) -> AudioNarrationResult:
    """Generate audio narration for a substrate, stored as audio_asset derivative.

    Acquires GpuLock; TTS is local so cost is 0.
    Splits long text into chunks to stay within F5-TTS VRAM budget.

    Args:
        substrate_id: Target substrate ULID.
        voice: TTS voice name ("default" or a voice ID from F5-TTS).
        speed: Speech speed multiplier.
        chunk_words: Max words per TTS chunk (controls VRAM usage).

    Returns:
        AudioNarrationResult with path to concatenated audio file.
    """
    text = _fetch_substrate_text(substrate_id)
    if not text:
        raise ValueError(f"substrate {substrate_id} has no text content")

    chunks = _chunk_text(text, chunk_words)
    log.info(
        "generate_audio_narration.start",
        substrate_id=substrate_id,
        chunks=len(chunks),
        voice=voice,
    )

    audio_dir = stratum_home() / "data" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_parts: list[bytes] = []
    gpu_lock = GpuLock()
    tts = TtsClient()
    try:
        async with gpu_lock.acquire(requester=f"audio_narration:{substrate_id}"):
            for i, chunk in enumerate(chunks):
                part = await tts.synthesize(chunk, voice=voice, speed=speed)
                audio_parts.append(part)
                log.info(
                    "generate_audio_narration.chunk_done",
                    substrate_id=substrate_id,
                    chunk=i + 1,
                    total=len(chunks),
                    bytes=len(part),
                )
    finally:
        await tts.close()
        await gpu_lock.close()

    from python_ulid import ULID

    asset_id = str(ULID())
    out_path = audio_dir / f"{asset_id}.wav"
    final_audio = _concat_audio_parts(audio_parts)
    out_path.write_bytes(final_audio)

    duration = _estimate_duration(final_audio)

    _save_audio_asset(
        asset_id=asset_id,
        substrate_id=substrate_id,
        file_path=str(out_path),
        duration_seconds=duration,
        voice=voice,
        speed=speed,
        byte_size=len(final_audio),
    )

    log.info(
        "generate_audio_narration.done",
        substrate_id=substrate_id,
        asset_id=asset_id,
        duration_seconds=duration,
    )
    return AudioNarrationResult(
        substrate_id=substrate_id,
        audio_asset_id=asset_id,
        audio_path=str(out_path),
        duration_seconds=duration,
        chunk_count=len(chunks),
        cost_usd=0.0,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fetch_substrate_text(substrate_id: str) -> str:
    """Fetch plaintext content from substrate derivative or source file."""
    db_path = meta_db_path()
    if not db_path.exists():
        return ""
    try:
        db = open_meta_db(db_path)
        # Prefer plaintext derivative
        rows = db.fetchall(
            "SELECT content FROM derivative WHERE substrate_id = ? AND kind = 'plaintext' LIMIT 1",
            [substrate_id],
        )
        if rows and rows[0][0]:
            db.close()
            return rows[0][0]
        # Fall back to markdown derivative
        rows = db.fetchall(
            "SELECT content FROM derivative WHERE substrate_id = ? AND kind = 'markdown' LIMIT 1",
            [substrate_id],
        )
        if rows and rows[0][0]:
            import re
            db.close()
            return re.sub(r"[#*`\[\]_]", "", rows[0][0]).strip()
        # Fall back to source_path
        rows = db.fetchall("SELECT source_path FROM substrate WHERE id = ?", [substrate_id])
        db.close()
        if rows and rows[0][0]:
            p = Path(rows[0][0])
            if p.exists() and p.suffix in {".txt", ".md"}:
                return p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        log.warning("generate_audio_narration.fetch_text_failed", error=str(exc))
    return ""


def _chunk_text(text: str, max_words: int) -> list[str]:
    """Split text into word-count-bounded chunks at sentence boundaries."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        words = len(sentence.split())
        if current_words + words > max_words and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = words
        else:
            current.append(sentence)
            current_words += words

    if current:
        chunks.append(" ".join(current))
    return [c for c in chunks if c.strip()]


def _concat_audio_parts(parts: list[bytes]) -> bytes:
    """Concatenate WAV parts. Simple raw concatenation — caller should use ffmpeg for production."""
    if len(parts) == 1:
        return parts[0]
    return b"".join(parts)


def _estimate_duration(audio_bytes: bytes) -> float:
    """Estimate audio duration from WAV byte size (rough: 16kHz mono 16-bit = 32000 B/s)."""
    return round(len(audio_bytes) / 32000.0, 2)


def _save_audio_asset(
    asset_id: str,
    substrate_id: str,
    file_path: str,
    duration_seconds: float,
    voice: str,
    speed: float,
    byte_size: int,
) -> None:
    db_path = meta_db_path()
    if not db_path.exists():
        return
    try:
        db = open_meta_db(db_path)
        meta = json.dumps({"voice": voice, "speed": speed})
        db.execute(
            """
            INSERT INTO audio_assets
                (id, substrate_id, file_path, duration_seconds, voice, speed, byte_size, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [asset_id, substrate_id, file_path, duration_seconds, voice, speed, byte_size, meta],
        )
        db.close()
    except Exception as exc:
        log.warning("generate_audio_narration.save_asset_failed", error=str(exc))
