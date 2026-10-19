"""Tests for oskill.compute_tax_lines."""

from __future__ import annotations

import pytest

from oskill._compute_tax_lines import compute_tax_lines


class TestComputeTaxLines:
    def test_single_item_single_rate(self):
        items = [{"item_id": "a", "line_total_cents": 1000}]
        rates = [{"rate_id": "vat", "rate_percent": 13.0}]
        assert compute_tax_lines(items, rates=rates) == [
            {"item_id": "a", "rate_id": "vat", "rate_percent": 13.0, "tax_cents": 130}
        ]

    def test_stacked_rates_produce_one_line_each(self):
        items = [{"item_id": "a", "line_total_cents": 1000}]
        rates = [
            {"rate_id": "national", "rate_percent": 10.0},
            {"rate_id": "regional", "rate_percent": 3.0},
        ]
        assert compute_tax_lines(items, rates=rates) == [
            {"item_id": "a", "rate_id": "national", "rate_percent": 10.0, "tax_cents": 100},
            {"item_id": "a", "rate_id": "regional", "rate_percent": 3.0, "tax_cents": 30},
        ]

    def test_multiple_items_cartesian_product(self):
        items = [
            {"item_id": "a", "line_total_cents": 1000},
            {"item_id": "b", "line_total_cents": 2000},
        ]
        rates = [{"rate_id": "vat", "rate_percent": 10.0}]
        result = compute_tax_lines(items, rates=rates)
        assert [line["item_id"] for line in result] == ["a", "b"]
        assert [line["tax_cents"] for line in result] == [100, 200]

    def test_round_half_up_not_bankers(self):
        # 105 * 10% = 10.5 -> half-up 11 (banker's rounding would give 10)
        items = [{"item_id": "a", "line_total_cents": 105}]
        rates = [{"rate_percent": 10.0}]
        assert compute_tax_lines(items, rates=rates)[0]["tax_cents"] == 11

    def test_rate_id_defaults_to_none(self):
        items = [{"item_id": "a", "line_total_cents": 1000}]
        rates = [{"rate_percent": 13.0}]
        assert compute_tax_lines(items, rates=rates)[0]["rate_id"] is None

    def test_zero_rate_yields_zero_tax(self):
        items = [{"item_id": "a", "line_total_cents": 1000}]
        rates = [{"rate_percent": 0.0}]
        assert compute_tax_lines(items, rates=rates)[0]["tax_cents"] == 0

    def test_zero_subtotal_yields_zero_tax(self):
        items = [{"item_id": "a", "line_total_cents": 0}]
        rates = [{"rate_percent": 13.0}]
        assert compute_tax_lines(items, rates=rates)[0]["tax_cents"] == 0

    def test_empty_items_returns_empty(self):
        assert compute_tax_lines([], rates=[{"rate_percent": 13.0}]) == []

    def test_empty_rates_returns_empty(self):
        assert compute_tax_lines([{"item_id": "a", "line_total_cents": 1000}], rates=[]) == []

    def test_item_missing_item_id_raises(self):
        with pytest.raises(ValueError, match="item_id"):
            compute_tax_lines([{"line_total_cents": 1000}], rates=[{"rate_percent": 13.0}])

    def test_item_missing_line_total_raises(self):
        with pytest.raises(ValueError, match="line_total_cents"):
            compute_tax_lines([{"item_id": "a"}], rates=[{"rate_percent": 13.0}])

    def test_negative_subtotal_raises(self):
        with pytest.raises(ValueError, match="line_total_cents must be >= 0"):
            compute_tax_lines(
                [{"item_id": "a", "line_total_cents": -1}], rates=[{"rate_percent": 13.0}]
            )

    def test_non_int_subtotal_raises(self):
        with pytest.raises(ValueError, match="line_total_cents must be int"):
            compute_tax_lines(
                [{"item_id": "a", "line_total_cents": "1000"}], rates=[{"rate_percent": 13.0}]
            )

    def test_rate_missing_rate_percent_raises(self):
        with pytest.raises(ValueError, match="rate_percent"):
            compute_tax_lines([{"item_id": "a", "line_total_cents": 1000}], rates=[{}])

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate_percent must be >= 0"):
            compute_tax_lines(
                [{"item_id": "a", "line_total_cents": 1000}], rates=[{"rate_percent": -1.0}]
            )
