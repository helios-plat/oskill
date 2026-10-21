"""compute_ast_diff ignores renames, keeps logic/constants."""

from __future__ import annotations

from oskill.ast_diffing import compute_ast_diff


def _fn(name: str, shape: str = "return", constants: list[str] | None = None) -> dict:
    return {
        "ok": True,
        "nodes": [
            {
                "kind": "function",
                "name": name,
                "arity": 1,
                "shape": shape,
                "constants": constants or [],
            }
        ],
    }


def test_rename_only_is_style_noise() -> None:
    rec = compute_ast_diff(_fn("old"), _fn("new"))
    assert rec["has_meaningful_change"] is False


def test_shape_change_is_logic() -> None:
    rec = compute_ast_diff(_fn("f", "return"), _fn("f", "if,return"))
    assert rec["has_meaningful_change"] is True
    assert rec["logic_change"] is True


def test_constant_change_is_knowledge() -> None:
    v0 = {"ok": True, "nodes": [{"kind": "constant", "name": "MAX", "constants": ["1"]}]}
    v1 = {"ok": True, "nodes": [{"kind": "constant", "name": "MAX", "constants": ["2"]}]}
    rec = compute_ast_diff(v0, v1)
    assert rec["knowledge_change"] is True
