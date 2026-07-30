"""Tests for oskill.resolve_order_payment_status."""

from __future__ import annotations

from oskill._resolve_order_payment_status import resolve_order_payment_status


class TestResolveOrderPaymentStatus:
    def test_empty_list_is_not_paid(self):
        assert resolve_order_payment_status([]) == "not_paid"

    def test_requires_action_takes_priority(self):
        payments = [{"status": "captured"}, {"status": "requires_action"}]
        assert resolve_order_payment_status(payments) == "requires_action"

    def test_all_canceled_is_canceled(self):
        assert resolve_order_payment_status([{"status": "canceled"}]) == "canceled"

    def test_all_failed_is_not_paid(self):
        assert resolve_order_payment_status([{"status": "failed"}]) == "not_paid"

    def test_mixed_canceled_and_failed_prefers_canceled(self):
        # "canceled" is more informative than generic "failed", so it wins.
        payments = [{"status": "canceled"}, {"status": "failed"}]
        assert resolve_order_payment_status(payments) == "canceled"

    def test_authorized_only_is_awaiting(self):
        assert resolve_order_payment_status([{"status": "authorized"}]) == "awaiting"

    def test_captured_is_captured(self):
        assert resolve_order_payment_status([{"status": "captured"}]) == "captured"

    def test_all_refunded_is_refunded(self):
        assert resolve_order_payment_status([{"status": "refunded"}]) == "refunded"

    def test_captured_plus_refund_is_partially_refunded(self):
        payments = [{"status": "captured"}, {"status": "refunded"}]
        assert resolve_order_payment_status(payments) == "partially_refunded"

    def test_authorized_plus_partially_refunded_is_partially_refunded(self):
        payments = [{"status": "authorized"}, {"status": "partially_refunded"}]
        assert resolve_order_payment_status(payments) == "partially_refunded"

    def test_canceled_plus_authorized_is_awaiting(self):
        payments = [{"status": "canceled"}, {"status": "authorized"}]
        assert resolve_order_payment_status(payments) == "awaiting"
