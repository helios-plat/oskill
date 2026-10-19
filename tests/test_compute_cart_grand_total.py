"""Tests for oskill.compute_cart_grand_total."""

from __future__ import annotations

import pytest

from oskill._compute_cart_grand_total import compute_cart_grand_total


class TestComputeCartGrandTotal:
    def test_subtotal_only(self):
        assert compute_cart_grand_total(1000) == 1000

    def test_discount_reduces_total(self):
        assert compute_cart_grand_total(1000, discount=300) == 700

    def test_discount_floors_at_zero_not_negative(self):
        assert compute_cart_grand_total(500, discount=900) == 0

    def test_tax_and_shipping_add_on_top(self):
        assert compute_cart_grand_total(1000, discount=100, tax=90, shipping=500) == 1490

    def test_negative_subtotal_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            compute_cart_grand_total(-1)

    def test_negative_discount_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            compute_cart_grand_total(1000, discount=-1)

    def test_negative_tax_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            compute_cart_grand_total(1000, tax=-1)

    def test_negative_shipping_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            compute_cart_grand_total(1000, shipping=-1)
