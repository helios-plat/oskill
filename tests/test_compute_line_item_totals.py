"""Tests for oskill.compute_line_item_totals."""

from __future__ import annotations

import pytest

from oskill._compute_line_item_totals import compute_line_item_totals


class TestComputeLineItemTotals:
    def test_subtotal_plus_single_tax(self):
        item = {"line_total_cents": 1000}
        taxes = [{"tax_cents": 130}]
        assert compute_line_item_totals(item, taxes=taxes) == {
            "subtotal_cents": 1000,
            "tax_cents": 130,
            "total_cents": 1130,
        }

    def test_multiple_tax_lines_summed(self):
        item = {"line_total_cents": 1000}
        taxes = [{"tax_cents": 100}, {"tax_cents": 30}]
        result = compute_line_item_totals(item, taxes=taxes)
        assert result["tax_cents"] == 130
        assert result["total_cents"] == 1130

    def test_empty_taxes_zero_tax(self):
        item = {"line_total_cents": 500}
        assert compute_line_item_totals(item, taxes=[]) == {
            "subtotal_cents": 500,
            "tax_cents": 0,
            "total_cents": 500,
        }

    def test_fallback_unit_price_times_quantity(self):
        item = {"unit_price_cents": 250, "quantity": 4}
        result = compute_line_item_totals(item, taxes=[{"tax_cents": 130}])
        assert result["subtotal_cents"] == 1000
        assert result["total_cents"] == 1130

    def test_line_total_takes_precedence(self):
        item = {"line_total_cents": 999, "unit_price_cents": 250, "quantity": 4}
        assert compute_line_item_totals(item, taxes=[])["subtotal_cents"] == 999

    def test_zero_quantity_zero_subtotal(self):
        item = {"unit_price_cents": 250, "quantity": 0}
        assert compute_line_item_totals(item, taxes=[])["subtotal_cents"] == 0

    def test_total_invariant_holds(self):
        item = {"line_total_cents": 1234}
        taxes = [{"tax_cents": 11}, {"tax_cents": 22}]
        result = compute_line_item_totals(item, taxes=taxes)
        assert result["total_cents"] == result["subtotal_cents"] + result["tax_cents"]

    def test_missing_subtotal_info_raises(self):
        with pytest.raises(ValueError, match="line_total_cents"):
            compute_line_item_totals({}, taxes=[])

    def test_unit_price_without_quantity_raises(self):
        with pytest.raises(ValueError, match="line_total_cents"):
            compute_line_item_totals({"unit_price_cents": 250}, taxes=[])

    def test_negative_subtotal_raises(self):
        with pytest.raises(ValueError, match="line_total_cents must be >= 0"):
            compute_line_item_totals({"line_total_cents": -1}, taxes=[])

    def test_non_int_subtotal_raises(self):
        with pytest.raises(ValueError, match="line_total_cents must be int"):
            compute_line_item_totals({"line_total_cents": 10.5}, taxes=[])

    def test_negative_unit_price_raises(self):
        with pytest.raises(ValueError, match="unit_price_cents must be >= 0"):
            compute_line_item_totals({"unit_price_cents": -1, "quantity": 2}, taxes=[])

    def test_tax_line_missing_tax_cents_raises(self):
        with pytest.raises(ValueError, match="tax_cents"):
            compute_line_item_totals({"line_total_cents": 1000}, taxes=[{}])

    def test_non_int_tax_cents_raises(self):
        with pytest.raises(ValueError, match="tax_cents must be int"):
            compute_line_item_totals({"line_total_cents": 1000}, taxes=[{"tax_cents": "130"}])
