"""oskill.pre_push_checks — S2: change-scoped checks before merge/push."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from oprim._diff_since import diff_since as _diff_since
from oprim._read_standards import read_standards as _read_standards
from oprim._run_targeted_checks import run_targeted_checks as _run_targeted_checks
from oprim._write_artifact import write_artifact as _write_artifact


def pre_push_checks(
    project_root: str,
    *,
    since_ref: str = "HEAD",
    force_full: bool = False,
    files: list[str] | None = None,
    diff_since_fn: Callable[..., dict[str, Any]] | None = None,
    read_standards_fn: Callable[..., dict[str, Any]] | None = None,
    run_checks_fn: Callable[..., dict[str, Any]] | None = None,
    write_artifact_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the smallest checks implied by the change. Never full-tests unless forced.

    Returns:
        ``{ok, skipped, since_ref, files, commands, report_path, reason}``
    """
    diff_fn = diff_since_fn or _diff_since
    std_fn = read_standards_fn or _read_standards
    check_fn = run_checks_fn or _run_targeted_checks
    write_fn = write_artifact_fn or _write_artifact

    if files is None:
        snapshot = diff_fn(repo=project_root, since_ref=since_ref)
        if not snapshot.get("ok"):
            return {
                "ok": False,
                "skipped": False,
                "since_ref": since_ref,
                "files": [],
                "commands": [],
                "report_path": "",
                "reason": snapshot.get("error") or "diff_since failed",
            }
        changed = list(snapshot.get("changed") or [])
    else:
        snapshot = {"ok": True, "changed": files, "files": [{"path": f} for f in files], "diff": ""}
        changed = list(files)

    standards = std_fn(project_root=project_root)
    check = check_fn(
        project_root=project_root,
        files=changed,
        force_full=force_full,
        check_map=standards.get("check_map"),
    )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    body = _render_report(since_ref, changed, check, force_full)
    written = write_fn(
        project_root=project_root,
        relpath=f"check-reports/{stamp}.md",
        content=body,
        kind="check-report",
    )
    return {
        "ok": bool(check.get("ok")),
        "skipped": bool(check.get("skipped")),
        "since_ref": since_ref,
        "files": changed,
        "commands": check.get("commands") or [],
        "report_path": written.get("path") or "",
        "reason": check.get("reason") or "",
        "standards_source": standards.get("standards_source"),
        "force_full": force_full,
    }


def _render_report(
    since_ref: str, files: list[str], check: dict[str, Any], force_full: bool
) -> str:
    lines = [
        "# Pre-push checks",
        "",
        f"- since_ref: `{since_ref}`",
        f"- ok: {check.get('ok')}",
        f"- skipped: {check.get('skipped')}",
        f"- force_full: {force_full}",
        f"- reason: {check.get('reason') or '-'}",
        "",
        "## Files",
    ]
    if files:
        lines.extend(f"- `{path}`" for path in files)
    else:
        lines.append("- (none)")
    lines.extend(["", "## Commands"])
    for rec in check.get("commands") or []:
        cmd = rec.get("cmd") or rec.get("name")
        lines.append(f"- `{cmd}` ran={rec.get('ran')} code={rec.get('code', '-')}")
        if rec.get("stderr"):
            lines.append("```")
            lines.append(str(rec["stderr"])[:1500])
            lines.append("```")
    return "\n".join(lines) + "\n"
