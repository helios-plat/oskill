"""Tests for oskill.evaluate_discount_conditions."""

from __future__ import annotations

import pytest

from oskill._evaluate_discount_conditions import evaluate_discount_conditions


class TestEvaluateDiscountConditions:
    def test_default_type_all_returns_everything(self):
        items = [{"product_id": "p1"}, {"product_id": "p2"}]
        assert evaluate_discount_conditions(items, condition={}) == items

    def test_explicit_all_returns_everything(self):
        items = [{"product_id": "p1"}]
        assert evaluate_discount_conditions(items, condition={"type": "all"}) == items

    def test_products_filter(self):
        items = [{"product_id": "p1"}, {"product_id": "p2"}, {"product_id": "p3"}]
        result = evaluate_discount_conditions(
            items, condition={"type": "products", "target_ids": ["p1", "p3"]}
        )
        assert result == [{"product_id": "p1"}, {"product_id": "p3"}]

    def test_categories_filter(self):
        items = [{"category_id": "c1"}, {"category_id": "c2"}]
        result = evaluate_discount_conditions(
            items, condition={"type": "categories", "target_ids": ["c1"]}
        )
        assert result == [{"category_id": "c1"}]

    def test_products_filter_no_match_returns_empty(self):
        items = [{"product_id": "p1"}]
        result = evaluate_discount_conditions(
            items, condition={"type": "products", "target_ids": ["ghost"]}
        )
        assert result == []

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown condition type"):
            evaluate_discount_conditions([], condition={"type": "bogus"})

    def test_empty_items_returns_empty(self):
        assert evaluate_discount_conditions([], condition={"type": "all"}) == []
