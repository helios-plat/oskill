"""oskill.find_simplifications — S3: proposals only; never writes business source."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from oprim._diff_since import diff_since as _diff_since
from oprim._write_artifact import write_proposal as _write_proposal

_BUSINESS_WRITE_BLOCKLIST = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
)


def find_simplifications(
    project_root: str,
    *,
    since_ref: str = "HEAD",
    files: list[str] | None = None,
    llm_call: Callable[[str], str] | None = None,
    diff_since_fn: Callable[..., dict[str, Any]] | None = None,
    write_proposal_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Detect over-design / dead code / duplication and write formal proposals.

    Business source is never written. ``written_business_source`` is always empty.
    """
    diff_fn = diff_since_fn or _diff_since
    write_fn = write_proposal_fn or _write_proposal
    if files is None:
        snapshot = diff_fn(repo=project_root, since_ref=since_ref)
        if not snapshot.get("ok"):
            return {
                "ok": False,
                "proposals": [],
                "proposal_paths": [],
                "written_business_source": [],
                "reason": snapshot.get("error") or "diff_since failed",
            }
        changed = list(snapshot.get("changed") or [])
    else:
        changed = list(files)

    proposals = _heuristic_proposals(Path(project_root), changed)
    if llm_call is not None:
        proposals.extend(_llm_proposals(llm_call, changed))

    paths: list[str] = []
    for item in proposals:
        written = write_fn(
            project_root=project_root,
            title=item["title"],
            body=_proposal_body(item),
            slug=item.get("kind") or "simplification",
        )
        path = written.get("path") or ""
        if path:
            paths.append(path)
            item["path"] = path
        if _looks_like_business_source(path):
            # Contract: refuse to report a business write even if a stub misbehaves.
            return {
                "ok": False,
                "proposals": proposals,
                "proposal_paths": paths,
                "written_business_source": [path],
                "reason": "write_proposal escaped engineering/; aborted",
            }

    return {
        "ok": True,
        "proposals": proposals,
        "proposal_paths": paths,
        "written_business_source": [],
        "files": changed,
    }


def _heuristic_proposals(root: Path, files: list[str]) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    fn_index: dict[str, list[str]] = defaultdict(list)
    for rel in files:
        path = root / rel
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lines = text.splitlines()
        if len(lines) >= 400:
            proposals.append(
                {
                    "title": f"Split oversized module {rel}",
                    "files": [rel],
                    "kind": "over-design",
                    "rationale": (
                        f"{rel} is {len(lines)} lines; consider extracting a focused helper."
                    ),
                }
            )
        if text.count("class ") >= 6 and len(lines) >= 200:
            proposals.append(
                {
                    "title": f"Reduce type surface in {rel}",
                    "files": [rel],
                    "kind": "over-design",
                    "rationale": (
                        f"{rel} defines many classes in one change; "
                        "check for speculative abstraction."
                    ),
                }
            )
        if re_commented_block(text):
            proposals.append(
                {
                    "title": f"Delete commented-out code in {rel}",
                    "files": [rel],
                    "kind": "dead-code",
                    "rationale": (
                        f"{rel} contains commented-out blocks; git history already preserves them."
                    ),
                }
            )
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_index[node.name].append(rel)
    for name, locs in fn_index.items():
        if name.startswith("_") or len(set(locs)) < 2:
            continue
        proposals.append(
            {
                "title": f"Deduplicate function {name}()",
                "files": sorted(set(locs)),
                "kind": "duplication",
                "rationale": (
                    f"{name}() appears in {sorted(set(locs))}; extract one implementation."
                ),
            }
        )
    return proposals


def re_commented_block(text: str) -> bool:
    streak = 0
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("#")
            and not stripped.startswith("#!")
            and not stripped.startswith("# ")
        ):
            streak += 1
            if streak >= 4:
                return True
        elif stripped.startswith("#") and any(
            tok in stripped for tok in ("def ", "class ", "return ", "import ")
        ):
            streak += 1
            if streak >= 3:
                return True
        else:
            streak = 0
    return False


def _llm_proposals(llm_call: Callable[[str], str], files: list[str]) -> list[dict[str, Any]]:
    raw = llm_call(
        "List over-design, dead-code, or duplication in these files as JSON "
        "list of {title,files,kind,rationale}. kinds: over-design|dead-code|duplication. "
        f"FILES: {files}"
    )
    import json
    import re

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.S)
        data = json.loads(match.group(0)) if match else []
    out = []
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        kind = str(item.get("kind") or "over-design")
        if kind not in {"over-design", "dead-code", "duplication"}:
            kind = "over-design"
        out.append(
            {
                "title": str(item["title"]),
                "files": list(item.get("files") or files),
                "kind": kind,
                "rationale": str(item.get("rationale") or ""),
            }
        )
    return out


def _proposal_body(item: dict[str, Any]) -> str:
    files = ", ".join(f"`{f}`" for f in item.get("files") or [])
    return (
        f"# {item['title']}\n\n"
        f"- kind: `{item.get('kind')}`\n"
        f"- files: {files or '(none)'}\n\n"
        f"{item.get('rationale') or ''}\n\n"
        "This is a proposal only. No business source was modified.\n"
    )


def _looks_like_business_source(path: str) -> bool:
    if not path:
        return False
    posix = path.replace("\\", "/")
    if "/.veya-project/engineering/" in posix:
        return False
    return Path(path).suffix in _BUSINESS_WRITE_BLOCKLIST
