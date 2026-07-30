"""Tests for oskill.verify_stock_threshold."""

from __future__ import annotations

import pytest

from oskill._verify_stock_threshold import verify_stock_threshold


class TestVerifyStockThreshold:
    def test_within_threshold_allowed(self):
        assert verify_stock_threshold(3, available=10, limit=2) is True

    def test_exactly_at_threshold_allowed(self):
        assert verify_stock_threshold(8, available=10, limit=2) is True

    def test_below_threshold_rejected(self):
        assert verify_stock_threshold(9, available=10, limit=2) is False

    def test_zero_limit_allows_full_depletion(self):
        assert verify_stock_threshold(10, available=10, limit=0) is True

    def test_negative_qty_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            verify_stock_threshold(-1, available=10, limit=0)
