"""edge_confidence — 唯一定义 EXTRACTED / 重名或未定义 INFERRED。"""

from __future__ import annotations

from oskill._edge_confidence import (
    EXTRACTED,
    INFERRED,
    annotate_edges,
    build_definition_index,
    edge_confidence,
    is_low_confidence,
)


def _index():
    return build_definition_index(
        {
            "a.py": ["unique_fn", "process"],
            "b.py": ["process"],  # process 重名 → 歧义
        }
    )


def test_build_index_collects_modules():
    idx = _index()
    assert idx["unique_fn"] == {"a.py"}
    assert idx["process"] == {"a.py", "b.py"}


def test_unique_definition_is_extracted():
    assert edge_confidence("unique_fn", _index()) == EXTRACTED
    assert is_low_confidence("unique_fn", _index()) is False


def test_ambiguous_name_is_inferred():
    assert edge_confidence("process", _index()) == INFERRED
    assert is_low_confidence("process", _index()) is True


def test_undefined_name_is_inferred():
    # 未在工作区定义 (外部/未解析) → 低置信
    assert edge_confidence("external_lib_call", _index()) == INFERRED


def test_annotate_edges_preserves_order_and_drops_blanks():
    out = annotate_edges(["unique_fn", "", "process"], _index())
    assert out == [("unique_fn", EXTRACTED), ("process", INFERRED)]


def test_empty_inputs():
    assert build_definition_index({}) == {}
    assert edge_confidence("x", {}) == INFERRED
    assert annotate_edges([], {}) == []
