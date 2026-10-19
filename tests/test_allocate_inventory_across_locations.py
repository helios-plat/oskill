"""Tests for oskill.allocate_inventory_across_locations."""

from __future__ import annotations

import pytest

from oskill._allocate_inventory_across_locations import allocate_inventory_across_locations


class TestAllocateInventoryAcrossLocations:
    def test_single_location_covers_demand(self):
        result = allocate_inventory_across_locations(5, stock_map={"loc1": 10})
        assert result == {"allocations": {"loc1": 5}, "fully_allocated": True, "unallocated_qty": 0}

    def test_spills_over_to_second_location(self):
        result = allocate_inventory_across_locations(15, stock_map={"loc1": 10, "loc2": 10})
        assert result == {
            "allocations": {"loc1": 10, "loc2": 5},
            "fully_allocated": True,
            "unallocated_qty": 0,
        }

    def test_insufficient_total_stock(self):
        result = allocate_inventory_across_locations(30, stock_map={"loc1": 10, "loc2": 10})
        assert result == {
            "allocations": {"loc1": 10, "loc2": 10},
            "fully_allocated": False,
            "unallocated_qty": 10,
        }

    def test_zero_qty_allocates_nothing(self):
        result = allocate_inventory_across_locations(0, stock_map={"loc1": 10})
        assert result == {"allocations": {}, "fully_allocated": True, "unallocated_qty": 0}

    def test_skips_locations_with_zero_stock(self):
        result = allocate_inventory_across_locations(5, stock_map={"loc1": 0, "loc2": 10})
        assert result == {"allocations": {"loc2": 5}, "fully_allocated": True, "unallocated_qty": 0}

    def test_empty_stock_map(self):
        result = allocate_inventory_across_locations(5, stock_map={})
        assert result == {"allocations": {}, "fully_allocated": False, "unallocated_qty": 5}

    def test_negative_qty_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            allocate_inventory_across_locations(-1, stock_map={"loc1": 10})
