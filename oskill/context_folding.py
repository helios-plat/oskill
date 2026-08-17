"""oskill.context_folding — keep goal prefix + recent tail, insert AST fact."""

from __future__ import annotations

import json
from typing import Any


def apply_semantic_folding(
    history: list[dict[str, Any]],
    *,
    current_ast: dict[str, Any] | None = None,
    keep_prefix: int = 2,
    keep_suffix: int = 4,
) -> list[dict[str, Any]]:
    """Fold trial-and-error middle turns. Pure. Does not call an LLM."""
    prefix_n = max(0, int(keep_prefix))
    suffix_n = max(0, int(keep_suffix))
    snapshot = _ast_message(current_ast)

    if not history:
        return [snapshot] if snapshot else []

    if len(history) <= prefix_n + suffix_n:
        folded = list(history)
        if snapshot:
            insert_at = min(prefix_n, len(folded))
            folded.insert(insert_at, snapshot)
        return folded

    folded = list(history[:prefix_n])
    if snapshot:
        folded.append(snapshot)
    if suffix_n:
        folded.extend(history[-suffix_n:])
    return folded


def _ast_message(current_ast: dict[str, Any] | None) -> dict[str, Any] | None:
    if current_ast is None:
        return None
    body = json.dumps(current_ast, ensure_ascii=False, sort_keys=True)
    if len(body) > 4000:
        body = body[:4000] + "…"
    return {
        "role": "system",
        "content": f"[SYSTEM FACT] AST snapshot: {body}",
        "kind": "ast_snapshot",
    }
