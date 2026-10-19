"""Tests for oskill.apply_discount_amount."""

from __future__ import annotations

import pytest

from oskill._apply_discount_amount import apply_discount_amount


class TestApplyDiscountAmount:
    def test_splits_proportionally_with_remainder_to_largest_share(self):
        items = [
            {"id": "a", "line_total_cents": 100},
            {"id": "b", "line_total_cents": 200},
        ]
        result = apply_discount_amount(items, amount=100)
        assert result["allocations"] == {"a": 33, "b": 67}
        assert result["total_discount_cents"] == 100

    def test_allocation_sum_always_equals_total_discount(self):
        items = [
            {"id": "a", "line_total_cents": 333},
            {"id": "b", "line_total_cents": 333},
            {"id": "c", "line_total_cents": 334},
        ]
        result = apply_discount_amount(items, amount=250)
        assert sum(result["allocations"].values()) == result["total_discount_cents"]
        assert result["total_discount_cents"] == 250

    def test_amount_exceeding_line_total_caps_at_line_total(self):
        items = [{"id": "a", "line_total_cents": 100}, {"id": "b", "line_total_cents": 200}]
        result = apply_discount_amount(items, amount=10_000)
        assert result["total_discount_cents"] == 300
        assert result["allocations"] == {"a": 100, "b": 200}

    def test_zero_amount_returns_empty(self):
        items = [{"id": "a", "line_total_cents": 100}]
        result = apply_discount_amount(items, amount=0)
        assert result == {"allocations": {}, "total_discount_cents": 0}

    def test_empty_items_returns_empty(self):
        result = apply_discount_amount([], amount=100)
        assert result == {"allocations": {}, "total_discount_cents": 0}

    def test_negative_amount_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            apply_discount_amount([{"id": "a", "line_total_cents": 100}], amount=-1)

    def test_single_item_gets_full_capped_amount(self):
        result = apply_discount_amount([{"id": "a", "line_total_cents": 500}], amount=200)
        assert result == {"allocations": {"a": 200}, "total_discount_cents": 200}
