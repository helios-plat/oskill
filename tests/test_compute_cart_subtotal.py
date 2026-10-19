"""Tests for oskill.compute_cart_subtotal."""

from __future__ import annotations

from oskill._compute_cart_subtotal import compute_cart_subtotal


class TestComputeCartSubtotal:
    def test_sums_line_totals(self):
        items = [{"line_total_cents": 1000}, {"line_total_cents": 2500}]
        assert compute_cart_subtotal(items) == 3500

    def test_empty_cart_is_zero(self):
        assert compute_cart_subtotal([]) == 0

    def test_missing_line_total_defaults_to_zero(self):
        items = [{"line_total_cents": 500}, {"other_field": 1}]
        assert compute_cart_subtotal(items) == 500

    def test_single_item(self):
        assert compute_cart_subtotal([{"line_total_cents": 999}]) == 999
