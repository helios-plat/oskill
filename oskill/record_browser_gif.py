"""oskill.record_browser_gif — S5: real GUI recording; never fabricate a gif."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oprim._capture_gui_clip import capture_gui_clip as _capture_gui_clip
from oprim._write_artifact import write_artifact as _write_artifact


def record_browser_gif(
    project_root: str,
    *,
    url: str = "",
    steps: list[dict[str, Any]] | None = None,
    script: str = "",
    capture_fn: Callable[..., dict[str, Any]] | None = None,
    write_artifact_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Record a real interaction. If the recorder is unavailable, fail with a reason."""
    capture = capture_fn or _capture_gui_clip
    write_fn = write_artifact_fn or _write_artifact
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = Path(project_root) / ".veya-project" / "engineering" / "gui-clips"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{stamp}.gif"

    result = capture(output_path=str(dest), url=url, steps=steps or [], script=script)
    if not result.get("ok"):
        note = (
            "# GUI clip not recorded\n\n"
            f"- ok: false\n"
            f"- reason: {result.get('reason') or 'unknown'}\n"
            "- A placeholder gif was **not** written.\n"
        )
        written = write_fn(
            project_root=project_root,
            relpath=f"gui-clips/{stamp}-blocked.md",
            content=note,
            kind="gui-clip-blocked",
        )
        return {
            "ok": False,
            "path": "",
            "reason": result.get("reason") or "capture failed",
            "note_path": written.get("path") or "",
        }

    return {
        "ok": True,
        "path": result.get("path") or str(dest),
        "reason": "",
        "note_path": "",
    }
