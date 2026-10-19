"""Tests for oskill.calculate_inventory_availability."""

from __future__ import annotations

import pytest

from oskill._calculate_inventory_availability import calculate_inventory_availability


class TestCalculateInventoryAvailability:
    def test_basic_subtraction(self):
        assert calculate_inventory_availability(10, reserved=3) == 7

    def test_zero_reserved(self):
        assert calculate_inventory_availability(10, reserved=0) == 10

    def test_fully_reserved(self):
        assert calculate_inventory_availability(10, reserved=10) == 0

    def test_overbooked_clips_to_zero(self):
        assert calculate_inventory_availability(5, reserved=8) == 0

    def test_negative_stock_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_inventory_availability(-1, reserved=0)

    def test_negative_reserved_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_inventory_availability(10, reserved=-1)
