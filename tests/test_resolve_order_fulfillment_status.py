"""Tests for oskill.resolve_order_fulfillment_status."""

from __future__ import annotations

from oskill._resolve_order_fulfillment_status import resolve_order_fulfillment_status


class TestResolveOrderFulfillmentStatus:
    def test_no_fulfillments_is_not_fulfilled(self):
        assert resolve_order_fulfillment_status([], total_qty=5) == "not_fulfilled"

    def test_all_canceled_is_canceled(self):
        fulfillments = [{"status": "canceled", "qty": 5}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "canceled"

    def test_partial_fulfillment(self):
        fulfillments = [{"status": "fulfilled", "qty": 2}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "partially_fulfilled"

    def test_full_fulfillment(self):
        fulfillments = [{"status": "fulfilled", "qty": 5}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "fulfilled"

    def test_partial_shipped(self):
        fulfillments = [{"status": "shipped", "qty": 2}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "partially_shipped"

    def test_full_shipped(self):
        fulfillments = [{"status": "shipped", "qty": 5}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "shipped"

    def test_partial_delivered(self):
        fulfillments = [{"status": "delivered", "qty": 2}, {"status": "shipped", "qty": 3}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "partially_delivered"

    def test_full_delivered(self):
        fulfillments = [{"status": "delivered", "qty": 5}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "delivered"

    def test_mixed_fulfilled_and_canceled(self):
        fulfillments = [{"status": "fulfilled", "qty": 3}, {"status": "canceled", "qty": 2}]
        assert resolve_order_fulfillment_status(fulfillments, total_qty=5) == "partially_fulfilled"

    def test_shipped_counts_toward_fulfilled_tier_too(self):
        # A fully shipped fulfillment also satisfies the lower "fulfilled" tier,
        # but the higher "shipped" tier should win.
        fulfillments = [{"status": "shipped", "qty": 5}]
        result = resolve_order_fulfillment_status(fulfillments, total_qty=5)
        assert result == "shipped"
