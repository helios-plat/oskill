"""oskill.multi_speaker_tts_merge — merge per-speaker TTS audio files."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any


def multi_speaker_tts_merge(
    *,
    audio_paths: list[str | Path],
    output_path: str | Path,
    gap_ms: int = 300,
    ffmpeg: str = "ffmpeg",
) -> Path:
    """Merge audio files into one (ffmpeg concat). Sync function."""
    if not audio_paths:
        raise ValueError("audio_paths must not be empty")
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which(ffmpeg) is None:
        # fallback: concatenate bytes
        data = b""
        for p in audio_paths:
            data += Path(p).read_bytes()
        out.write_bytes(data)
        return out
    # build concat list
    list_file = out.with_suffix(".txt")
    lines = []
    for p in audio_paths:
        lines.append(f"file '{Path(p).resolve()}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")
    import subprocess
    cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        list_file.unlink(missing_ok=True)
    except Exception:
        pass
    return out
