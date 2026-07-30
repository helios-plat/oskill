"""Tests for oskill.apply_free_shipping."""

from __future__ import annotations

from oskill._apply_free_shipping import apply_free_shipping


class TestApplyFreeShipping:
    def test_zeroes_out_price(self):
        methods = [{"id": "m1", "name": "Standard", "price_cents": 1000}]
        result = apply_free_shipping(methods)
        assert result == [{"id": "m1", "name": "Standard", "price_cents": 0}]

    def test_does_not_mutate_input(self):
        methods = [{"id": "m1", "price_cents": 1000}]
        apply_free_shipping(methods)
        assert methods[0]["price_cents"] == 1000

    def test_multiple_methods_all_zeroed(self):
        methods = [{"id": "m1", "price_cents": 500}, {"id": "m2", "price_cents": 800}]
        result = apply_free_shipping(methods)
        assert all(m["price_cents"] == 0 for m in result)

    def test_empty_list_returns_empty(self):
        assert apply_free_shipping([]) == []
