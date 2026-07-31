"""Tests for oskill.evaluate_tax_inclusive_pricing."""

from __future__ import annotations

import pytest

from oskill._evaluate_tax_inclusive_pricing import evaluate_tax_inclusive_pricing


class TestEvaluateTaxInclusivePricing:
    def test_clean_split(self):
        # 1130 gross at 13% -> net 1000, tax 130
        assert evaluate_tax_inclusive_pricing(1130, tax_rate=13.0) == {
            "gross_cents": 1130,
            "net_cents": 1000,
            "tax_cents": 130,
        }

    def test_rounding_down(self):
        # 100 / 1.13 = 88.4955... -> half-up 88, tax 12
        result = evaluate_tax_inclusive_pricing(100, tax_rate=13.0)
        assert result["net_cents"] == 88
        assert result["tax_cents"] == 12

    def test_half_up_not_bankers(self):
        # 5 / 2.0 = 2.5 -> half-up 3 (banker's rounding would give 2), tax 2
        result = evaluate_tax_inclusive_pricing(5, tax_rate=100.0)
        assert result["net_cents"] == 3
        assert result["tax_cents"] == 2

    def test_zero_rate_is_tax_free(self):
        assert evaluate_tax_inclusive_pricing(500, tax_rate=0.0) == {
            "gross_cents": 500,
            "net_cents": 500,
            "tax_cents": 0,
        }

    def test_zero_price(self):
        assert evaluate_tax_inclusive_pricing(0, tax_rate=13.0) == {
            "gross_cents": 0,
            "net_cents": 0,
            "tax_cents": 0,
        }

    def test_gross_equals_net_plus_tax_invariant(self):
        for gross in (999, 1, 7, 12345, 3):
            result = evaluate_tax_inclusive_pricing(gross, tax_rate=7.5)
            assert result["gross_cents"] == result["net_cents"] + result["tax_cents"]

    def test_integer_rate_accepted(self):
        result = evaluate_tax_inclusive_pricing(1130, tax_rate=13)
        assert result["net_cents"] == 1000
        assert result["tax_cents"] == 130

    def test_non_int_price_raises(self):
        with pytest.raises(ValueError, match="price must be int"):
            evaluate_tax_inclusive_pricing(10.5, tax_rate=13.0)

    def test_bool_price_raises(self):
        with pytest.raises(ValueError, match="price must be int"):
            evaluate_tax_inclusive_pricing(True, tax_rate=13.0)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="price must be >= 0"):
            evaluate_tax_inclusive_pricing(-1, tax_rate=13.0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="tax_rate must be >= 0"):
            evaluate_tax_inclusive_pricing(1000, tax_rate=-1.0)

    def test_non_number_rate_raises(self):
        with pytest.raises(ValueError, match="tax_rate must be a number"):
            evaluate_tax_inclusive_pricing(1000, tax_rate="13.0")
