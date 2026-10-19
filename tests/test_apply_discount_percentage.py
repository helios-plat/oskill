"""Tests for oskill.apply_discount_percentage."""

from __future__ import annotations

import pytest

from oskill._apply_discount_percentage import apply_discount_percentage


class TestApplyDiscountPercentage:
    def test_applies_percent_per_line_independently(self):
        items = [{"id": "a", "line_total_cents": 1000}, {"id": "b", "line_total_cents": 2000}]
        result = apply_discount_percentage(items, percent=10)
        assert result["allocations"] == {"a": 100, "b": 200}
        assert result["total_discount_cents"] == 300

    def test_rounds_to_nearest_cent(self):
        result = apply_discount_percentage([{"id": "a", "line_total_cents": 333}], percent=10)
        assert result["allocations"]["a"] == round(33.3)

    def test_zero_percent_is_no_discount(self):
        result = apply_discount_percentage([{"id": "a", "line_total_cents": 1000}], percent=0)
        assert result == {"allocations": {"a": 0}, "total_discount_cents": 0}

    def test_hundred_percent_discounts_fully(self):
        result = apply_discount_percentage([{"id": "a", "line_total_cents": 1000}], percent=100)
        assert result == {"allocations": {"a": 1000}, "total_discount_cents": 1000}

    def test_negative_percent_raises(self):
        with pytest.raises(ValueError, match="within \\[0, 100\\]"):
            apply_discount_percentage([{"id": "a", "line_total_cents": 100}], percent=-1)

    def test_over_hundred_percent_raises(self):
        with pytest.raises(ValueError, match="within \\[0, 100\\]"):
            apply_discount_percentage([{"id": "a", "line_total_cents": 100}], percent=101)

    def test_empty_items_returns_empty(self):
        result = apply_discount_percentage([], percent=10)
        assert result == {"allocations": {}, "total_discount_cents": 0}
