"""Tests for oskill.allocate_gift_card_balance."""

from __future__ import annotations

import pytest

from oskill._allocate_gift_card_balance import allocate_gift_card_balance


class TestAllocateGiftCardBalance:
    def test_partial_balance_covers_part_of_total(self):
        result = allocate_gift_card_balance(1000, card_balance=400)
        assert result == {
            "applied_cents": 400,
            "remaining_card_balance_cents": 0,
            "remaining_cart_total_cents": 600,
        }

    def test_balance_exceeds_total_leaves_card_balance(self):
        result = allocate_gift_card_balance(300, card_balance=1000)
        assert result == {
            "applied_cents": 300,
            "remaining_card_balance_cents": 700,
            "remaining_cart_total_cents": 0,
        }

    def test_exact_match_zeroes_both(self):
        result = allocate_gift_card_balance(500, card_balance=500)
        assert result == {
            "applied_cents": 500,
            "remaining_card_balance_cents": 0,
            "remaining_cart_total_cents": 0,
        }

    def test_zero_total_applies_nothing(self):
        result = allocate_gift_card_balance(0, card_balance=500)
        assert result == {
            "applied_cents": 0,
            "remaining_card_balance_cents": 500,
            "remaining_cart_total_cents": 0,
        }

    def test_negative_cart_total_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            allocate_gift_card_balance(-1, card_balance=100)

    def test_negative_card_balance_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            allocate_gift_card_balance(100, card_balance=-1)
