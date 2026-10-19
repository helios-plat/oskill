"""apply_semantic_folding keeps prefix/suffix and inserts AST."""

from __future__ import annotations

from oskill.context_folding import apply_semantic_folding


def test_folds_middle_and_inserts_ast() -> None:
    history = [{"role": "user", "content": f"m{i}"} for i in range(10)]
    folded = apply_semantic_folding(
        history, current_ast={"file": "a.py"}, keep_prefix=2, keep_suffix=3
    )
    assert folded[0]["content"] == "m0"
    assert folded[1]["content"] == "m1"
    assert folded[2]["kind"] == "ast_snapshot"
    assert "a.py" in folded[2]["content"]
    assert [m["content"] for m in folded[-3:]] == ["m7", "m8", "m9"]
    assert len(folded) == 2 + 1 + 3


def test_short_history_kept() -> None:
    history = [{"role": "user", "content": "only"}]
    folded = apply_semantic_folding(history, keep_prefix=2, keep_suffix=4)
    assert folded == history
