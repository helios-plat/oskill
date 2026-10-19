"""oskill.highlight_detection_algorithm — detect highlight segments in a transcript."""

from __future__ import annotations

from typing import Any


def highlight_detection_algorithm(
    *,
    segments: list[dict[str, Any]],
    keywords: list[str] | None = None,
    top_k: int = 5,
    min_duration: float = 3.0,
    max_duration: float = 60.0,
) -> list[dict[str, Any]]:
    """Score transcript segments and return top highlights.

    Each segment: {start, end, text}. Returns list of {start, end, text, score}.
    Scoring: keyword hits + length bonus + punctuation energy.
    """
    if not segments:
        return []
    keywords = [k.lower() for k in (keywords or [])]
    scored = []
    for seg in segments:
        text = str(seg.get("text", ""))
        low = text.lower()
        score = 0.0
        for kw in keywords:
            if kw and kw in low:
                score += 2.0
        # energy: exclamation/question
        score += text.count("!") * 1.5 + text.count("?") * 1.0
        dur = float(seg.get("end", 0)) - float(seg.get("start", 0))
        if dur < min_duration:
            score -= 1.0
        if dur > max_duration:
            score -= 0.5
        # length bonus (moderate)
        words = len(text.split())
        score += min(words, 30) * 0.05
        scored.append({
            "start": float(seg.get("start", 0)),
            "end": float(seg.get("end", 0)),
            "text": text,
            "score": round(score, 4),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
