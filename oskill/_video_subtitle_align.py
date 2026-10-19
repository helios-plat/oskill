"""oskill.video_subtitle_align — align subtitles to audio/video timestamps."""

from __future__ import annotations

from typing import Any


def video_subtitle_align(
    *,
    subtitles: list[dict[str, Any]],
    audio_duration: float | None = None,
    max_chars_per_line: int = 42,
) -> list[dict[str, Any]]:
    """Normalize/align subtitle entries.

    Each subtitle: {start, end, text}. Returns cleaned list with clamped times
    and wrapped text.
    """
    out = []
    for s in subtitles or []:
        start = float(s.get("start", 0.0))
        end = float(s.get("end", start + 1.0))
        if end <= start:
            end = start + 1.0
        if audio_duration is not None:
            end = min(end, audio_duration)
            start = min(start, audio_duration)
        text = str(s.get("text", "")).strip()
        # wrap long lines
        if len(text) > max_chars_per_line:
            words = text.split()
            lines = []
            cur = ""
            for w in words:
                if len(cur) + len(w) + 1 > max_chars_per_line:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                lines.append(cur)
            text = "\n".join(lines)
        out.append({"start": start, "end": end, "text": text})
    out.sort(key=lambda x: x["start"])
    return out
