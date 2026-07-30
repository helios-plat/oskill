"""Tests for oskill.evaluate_discount_eligibility."""

from __future__ import annotations

from oskill._evaluate_discount_eligibility import evaluate_discount_eligibility


class TestEvaluateDiscountEligibility:
    def test_no_constraints_always_eligible(self):
        assert evaluate_discount_eligibility({"subtotal_cents": 100}, rule={}) is True

    def test_min_subtotal_met(self):
        assert (
            evaluate_discount_eligibility(
                {"subtotal_cents": 1000}, rule={"min_subtotal_cents": 1000}
            )
            is True
        )

    def test_min_subtotal_not_met(self):
        assert (
            evaluate_discount_eligibility(
                {"subtotal_cents": 999}, rule={"min_subtotal_cents": 1000}
            )
            is False
        )

    def test_valid_time_window_inside(self):
        rule = {
            "valid_from": "2000-01-01T00:00:00+00:00",
            "valid_until": "2999-01-01T00:00:00+00:00",
        }
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is True

    def test_expired_window_rejected(self):
        rule = {"valid_until": "2000-01-01T00:00:00+00:00"}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is False

    def test_not_yet_started_rejected(self):
        rule = {"valid_from": "2999-01-01T00:00:00+00:00"}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is False

    def test_naive_iso_datetime_treated_as_utc(self):
        rule = {"valid_until": "2000-01-01T00:00:00"}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is False

    def test_region_allowed(self):
        rule = {"region_codes": ["cn-east", "cn-south"]}
        assert (
            evaluate_discount_eligibility(
                {"subtotal_cents": 0, "region_code": "cn-east"}, rule=rule
            )
            is True
        )

    def test_region_not_allowed(self):
        rule = {"region_codes": ["cn-east"]}
        assert (
            evaluate_discount_eligibility(
                {"subtotal_cents": 0, "region_code": "cn-south"}, rule=rule
            )
            is False
        )

    def test_region_missing_on_cart_rejected(self):
        rule = {"region_codes": ["cn-east"]}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is False

    def test_usage_limit_not_reached(self):
        rule = {"max_uses": 5, "uses_count": 4}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is True

    def test_usage_limit_reached_rejected(self):
        rule = {"max_uses": 5, "uses_count": 5}
        assert evaluate_discount_eligibility({"subtotal_cents": 0}, rule=rule) is False

    def test_all_constraints_combined(self):
        rule = {
            "min_subtotal_cents": 500,
            "region_codes": ["cn-east"],
            "max_uses": 10,
            "uses_count": 3,
        }
        cart = {"subtotal_cents": 600, "region_code": "cn-east"}
        assert evaluate_discount_eligibility(cart, rule=rule) is True
