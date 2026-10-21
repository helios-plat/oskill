"""oskill.code_review — S1: correctness / security / lifecycle review of a change."""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oprim._diff_since import diff_since as _diff_since
from oprim._read_standards import read_standards as _read_standards
from oprim._write_artifact import write_artifact as _write_artifact

_SEC_PATTERNS = (
    (re.compile(r"\beval\s*\("), "eval() on possibly untrusted input"),
    (re.compile(r"\bexec\s*\("), "exec() on possibly untrusted input"),
    (re.compile(r"pickle\.loads\s*\("), "pickle.loads is an RCE footgun"),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True interpolates the host shell"),
    (re.compile(r"yaml\.load\s*\("), "yaml.load without Loader is unsafe"),
    (re.compile(r"verify\s*=\s*False"), "TLS verification disabled"),
)
_LIFE_PATTERNS = (
    (re.compile(r"\bTODO\b|\bFIXME\b|\bXXX\b"), "unresolved lifecycle marker"),
    (re.compile(r"except\s*:"), "bare except swallows all errors"),
    (re.compile(r"except\s+Exception\s*:\s*(pass|return)\b"), "swallowed exception"),
)


def code_review(
    project_root: str,
    *,
    since_ref: str = "HEAD",
    files: list[str] | None = None,
    diff: str | None = None,
    llm_call: Callable[[str], str] | None = None,
    diff_since_fn: Callable[..., dict[str, Any]] | None = None,
    read_standards_fn: Callable[..., dict[str, Any]] | None = None,
    write_artifact_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Review the change for correctness, security, and lifecycle.

    ``llm_call(prompt) -> str`` is optional; heuristics always run so the skill
    is unit-testable without a model.
    """
    diff_fn = diff_since_fn or _diff_since
    std_fn = read_standards_fn or _read_standards
    write_fn = write_artifact_fn or _write_artifact

    snapshot = {"ok": True, "changed": files or [], "diff": diff or "", "files": []}
    if files is None or diff is None:
        snapshot = diff_fn(repo=project_root, since_ref=since_ref)
        if not snapshot.get("ok"):
            return {
                "ok": False,
                "verdict": "fail",
                "findings": [],
                "report_path": "",
                "reason": snapshot.get("error") or "diff_since failed",
            }
    changed = list(files if files is not None else snapshot.get("changed") or [])
    unified = diff if diff is not None else str(snapshot.get("diff") or "")
    standards = std_fn(project_root=project_root)

    findings = _heuristic_findings(Path(project_root), changed, unified)
    if llm_call is not None:
        findings.extend(_llm_findings(llm_call, changed, unified, str(standards.get("text") or "")))

    verdict = _verdict(findings)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    body = _render(verdict, findings, standards.get("standards_source"), since_ref, changed)
    written = write_fn(
        project_root=project_root,
        relpath=f"reviews/{stamp}.md",
        content=body,
        kind="review",
    )
    return {
        "ok": verdict != "fail",
        "verdict": verdict,
        "findings": findings,
        "report_path": written.get("path") or "",
        "standards_source": standards.get("standards_source"),
        "files": changed,
    }


def _heuristic_findings(root: Path, files: list[str], unified: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rel in files:
        path = root / rel
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for rx, msg in _SEC_PATTERNS:
            for m in rx.finditer(text):
                findings.append(_finding(rel, _lineno(text, m.start()), "high", "security", msg))
        for rx, msg in _LIFE_PATTERNS:
            for m in rx.finditer(text):
                findings.append(_finding(rel, _lineno(text, m.start()), "medium", "lifecycle", msg))
        findings.extend(_ast_correctness(rel, text))
    if "password" in unified.lower() and "os.environ" not in unified:
        findings.append(
            _finding("", 0, "high", "security", "diff mentions password without env lookup")
        )
    return findings


def _ast_correctness(rel: str, text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [_finding(rel, exc.lineno or 1, "high", "correctness", f"syntax error: {exc.msg}")]
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.defaults:
                if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                    out.append(
                        _finding(
                            rel,
                            getattr(node, "lineno", 1),
                            "medium",
                            "correctness",
                            f"{node.name}: mutable default argument",
                        )
                    )
    return out


def _llm_findings(
    llm_call: Callable[[str], str],
    files: list[str],
    unified: str,
    standards: str,
) -> list[dict[str, Any]]:
    prompt = (
        "Review this diff for correctness, security, and lifecycle. "
        "Return JSON list of {file,line,severity,category,message}. "
        "Categories: correctness|security|lifecycle. Severity: high|medium|low.\n\n"
        f"STANDARDS:\n{standards[:4000]}\n\nFILES: {files}\n\nDIFF:\n{unified[:12000]}"
    )
    raw = llm_call(prompt)
    data = _parse_json_list(raw)
    findings = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cat = str(item.get("category") or "correctness")
        if cat not in {"correctness", "security", "lifecycle"}:
            cat = "correctness"
        findings.append(
            _finding(
                str(item.get("file") or ""),
                int(item.get("line") or 0),
                str(item.get("severity") or "medium"),
                cat,
                str(item.get("message") or "").strip(),
            )
        )
    return [f for f in findings if f["message"]]


def _parse_json_list(raw: str) -> list[Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _finding(file: str, line: int, severity: str, category: str, message: str) -> dict[str, Any]:
    return {
        "file": file,
        "line": line,
        "severity": severity,
        "category": category,
        "message": message,
    }


def _lineno(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _verdict(findings: list[dict[str, Any]]) -> str:
    if any(f.get("severity") == "high" for f in findings):
        return "fail"
    if findings:
        return "warn"
    return "pass"


def _render(
    verdict: str,
    findings: list[dict[str, Any]],
    standards_source: Any,
    since_ref: str,
    files: list[str],
) -> str:
    lines = [
        "# Code review",
        "",
        f"- verdict: **{verdict}**",
        f"- since_ref: `{since_ref}`",
        f"- standards_source: {standards_source}",
        f"- files: {', '.join(f'`{f}`' for f in files) or '(none)'}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- none")
    for item in findings:
        loc = f"{item['file']}:{item['line']}" if item.get("file") else "(diff)"
        lines.append(
            f"- [{item['severity']}/{item['category']}] {loc} — {item['message']}"
        )
    return "\n".join(lines) + "\n"
