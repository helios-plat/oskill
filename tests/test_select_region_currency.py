"""Tests for oskill.select_region_currency."""

from __future__ import annotations

import pytest

from oskill._select_region_currency import select_region_currency


class TestSelectRegionCurrency:
    REGIONS = [
        {"code": "east-asia", "currency": "CNY", "countries": ["CN", "HK"]},
        {"code": "north-america", "currency": "USD", "countries": ["US", "CA"]},
    ]

    def test_first_region_match(self):
        assert select_region_currency(self.REGIONS, user_country="CN") == "CNY"

    def test_second_region_match(self):
        assert select_region_currency(self.REGIONS, user_country="US") == "USD"

    def test_matches_within_countries_list(self):
        assert select_region_currency(self.REGIONS, user_country="CA") == "USD"

    def test_first_match_wins_on_overlap(self):
        regions = [
            {"currency": "AAA", "countries": ["CN"]},
            {"currency": "BBB", "countries": ["CN"]},
        ]
        assert select_region_currency(regions, user_country="CN") == "AAA"

    def test_no_match_raises(self):
        with pytest.raises(ValueError, match="no region matches"):
            select_region_currency(self.REGIONS, user_country="JP")

    def test_empty_regions_raises(self):
        with pytest.raises(ValueError, match="no region matches"):
            select_region_currency([], user_country="CN")

    def test_match_is_case_sensitive(self):
        with pytest.raises(ValueError, match="no region matches"):
            select_region_currency(self.REGIONS, user_country="cn")

    def test_empty_user_country_raises(self):
        with pytest.raises(ValueError, match="non-empty str"):
            select_region_currency(self.REGIONS, user_country="")

    def test_non_str_user_country_raises(self):
        with pytest.raises(ValueError, match="non-empty str"):
            select_region_currency(self.REGIONS, user_country=123)

    def test_region_missing_currency_raises(self):
        with pytest.raises(ValueError, match="currency"):
            select_region_currency([{"countries": ["CN"]}], user_country="CN")

    def test_region_missing_countries_raises(self):
        with pytest.raises(ValueError, match="countries"):
            select_region_currency([{"currency": "CNY"}], user_country="CN")
