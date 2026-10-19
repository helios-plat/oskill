"""WAVE H gates: progressive context disclosure (pure functions)."""

from __future__ import annotations

from oskill.context_compact import (
    ContextItem,
    compact_context,
    expand_item,
    rank_context_items,
    select_context_window,
)


def _items():
    return [
        ContextItem(
            item_id="a",
            headline="A",
            summary="sum A",
            detail="det A",
            source_text="full A",
            layer="L3",
            token_cost=400,
            relevance=0.9,
            recency=0.9,
            source="s1",
        ),
        ContextItem(
            item_id="b",
            headline="B",
            summary="sum B",
            detail="det B",
            source_text="full B",
            layer="L3",
            token_cost=400,
            relevance=0.2,
            recency=0.1,
            source="s2",
        ),
        ContextItem(
            item_id="c",
            headline="C",
            layer="L0",
            token_cost=10,
            relevance=0.5,
            recency=0.5,
            source="s3",
            pinned=True,
        ),
    ]


def test_progressive_disclosure_layers():
    item = _items()[0]
    l0 = expand_item(item, "L0")
    assert l0.layer == "L0" and l0.token_cost < item.token_cost
    l1 = expand_item(item, "L1")
    assert l1.extra["expanded_text"] == "sum A"
    try:
        expand_item(item, "L9")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_token_budget_enforced():
    selected = select_context_window(_items(), token_budget=50)
    total = sum(i.token_cost for i in selected)
    assert total <= 50
    assert any(i.item_id == "c" for i in selected)  # pinned 保留


def test_high_priority_not_dropped():
    compacted = compact_context(_items(), token_budget=5)
    assert any(i.item_id == "c" for i in compacted)


def test_expansion_deterministic():
    first = compact_context(_items(), token_budget=300)
    second = compact_context(_items(), token_budget=300)
    assert [(i.item_id, i.layer) for i in first] == [(i.item_id, i.layer) for i in second]
    assert rank_context_items(_items())[0].item_id == "c"  # pinned 优先
    assert [i.item_id for i in rank_context_items(_items())][1:] == ["a", "b"]


def test_low_cost_coverage_first():
    items = [
        ContextItem(
            item_id="cheap", headline="c", layer="L0", token_cost=5, relevance=0.4, recency=0.4
        ),
        ContextItem(
            item_id="pricey",
            headline="p",
            layer="L3",
            token_cost=5000,
            relevance=0.41,
            recency=0.41,
        ),
    ]
    ranked = rank_context_items(items)
    assert ranked[0].item_id == "cheap"


def test_no_persistence_or_memory_runtime():
    import pathlib

    src = pathlib.Path(__file__).parent.parent.joinpath("oskill/context_compact.py").read_text()
    for forbidden in ("sqlite", "MemoryStore", "memory_bank", "VectorStore", "open(", "write_text"):
        assert forbidden not in src
