"""oskill.archive_agent_notes — S4: archive by future value; suppress knowledge inflation."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from oprim._archive_note import archive_note as _archive_note

_PROMOTE_HINTS = (
    "never ",
    "不要",
    "禁止",
    "constraint",
    "gotcha",
    "decision",
    "red line",
    "红线",
    "must not",
    "hard constraint",
    "root cause",
    "根因",
)
_SUPPRESS_HINTS = (
    "today i",
    "wip",
    "scratch",
    "tmp",
    "just chatting",
    "hmm",
    "lol",
    "session log",
)


def archive_agent_notes(
    project_root: str,
    *,
    inbox_rel: str = "notes-inbox",
    archive_note_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Promote high-future-value notes; suppress the rest. No business source writes."""
    archive_fn = archive_note_fn or _archive_note
    root = Path(project_root).resolve()
    inbox = root / ".veya-project" / "engineering" / inbox_rel
    inbox.mkdir(parents=True, exist_ok=True)

    promoted: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        title = _title(path, body)
        decision, reason = _score(title, body)
        result = archive_fn(
            project_root=project_root,
            title=title,
            body=body,
            decision=decision,
            reason=reason,
            source_path=str(path),
        )
        rec = {
            "title": title,
            "source": str(path),
            "path": result.get("path") or "",
            "reason": reason,
            "ok": bool(result.get("ok")),
        }
        if decision == "promote":
            promoted.append(rec)
        else:
            suppressed.append(rec)

    return {
        "ok": True,
        "promoted": promoted,
        "suppressed": suppressed,
        "inbox": str(inbox),
        "written_business_source": [],
    }


def _title(path: Path, body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or path.stem
    return path.stem


def _score(title: str, body: str) -> tuple[str, str]:
    blob = f"{title}\n{body}".lower()
    if any(h in blob for h in _PROMOTE_HINTS):
        return "promote", "contains a durable constraint or decision"
    if any(h in blob for h in _SUPPRESS_HINTS):
        return "suppress", "ephemeral session noise"
    if len(body.strip()) < 40:
        return "suppress", "too short to have future value"
    if re.search(r"\b(always|never|must|禁止|必须)\b", blob):
        return "promote", "normative rule worth keeping"
    return "suppress", "no durable future-value signal"
