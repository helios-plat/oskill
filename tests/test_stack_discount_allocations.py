"""Tests for oskill.stack_discount_allocations."""

from __future__ import annotations

from oskill._stack_discount_allocations import stack_discount_allocations


class TestStackDiscountAllocations:
    def test_merges_disjoint_line_allocations(self):
        allocs = [
            {"allocations": {"a": 100}, "total_discount_cents": 100},
            {"allocations": {"b": 50}, "total_discount_cents": 50},
        ]
        result = stack_discount_allocations(allocs)
        assert result == {"allocations": {"a": 100, "b": 50}, "total_discount_cents": 150}

    def test_sums_overlapping_line_allocations(self):
        allocs = [
            {"allocations": {"a": 100, "b": 50}, "total_discount_cents": 150},
            {"allocations": {"a": 20}, "total_discount_cents": 20},
        ]
        result = stack_discount_allocations(allocs)
        assert result["allocations"] == {"a": 120, "b": 50}
        assert result["total_discount_cents"] == 170

    def test_empty_list_returns_empty(self):
        assert stack_discount_allocations([]) == {"allocations": {}, "total_discount_cents": 0}

    def test_single_allocation_passthrough(self):
        allocs = [{"allocations": {"a": 10}, "total_discount_cents": 10}]
        assert stack_discount_allocations(allocs) == {
            "allocations": {"a": 10},
            "total_discount_cents": 10,
        }
