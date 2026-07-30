"""Tests for oskill.resolve_display_batch."""

from __future__ import annotations

from oskill._resolve_display_batch import resolve_display_batch


def _batch(**overrides) -> dict:
    base = {
        "id": "b1",
        "status": "active",
        "inspection_status": "passed",
        "stock_qty": 10,
        "reserved_qty": 0,
        "location_region": "cn-east",
        "location_lat": 31.23,
        "location_lng": 121.47,
    }
    base.update(overrides)
    return base


class TestResolveDisplayBatch:
    def test_home_region_batch_always_included_without_coords(self):
        result = resolve_display_batch([_batch()], user_region="cn-east")
        assert len(result) == 1
        assert result[0]["is_home_location"] is True
        assert result[0]["distance_km"] is None

    def test_non_home_batch_excluded_when_no_user_coords(self):
        result = resolve_display_batch([_batch(location_region="cn-south")], user_region="cn-east")
        assert result == []

    def test_non_home_batch_included_within_radius(self):
        # Beijing (~1067km from Shanghai) vs a nearby point (~a few km).
        near = _batch(location_region="cn-north", location_lat=31.25, location_lng=121.50)
        result = resolve_display_batch(
            [near], user_region="cn-east", user_lat=31.23, user_lng=121.47, max_distance_km=50.0
        )
        assert len(result) == 1
        assert result[0]["is_home_location"] is False
        assert result[0]["distance_km"] < 50.0

    def test_non_home_batch_excluded_beyond_radius(self):
        far = _batch(location_region="cn-north", location_lat=39.90, location_lng=116.40)  # Beijing
        result = resolve_display_batch(
            [far], user_region="cn-east", user_lat=31.23, user_lng=121.47, max_distance_km=50.0
        )
        assert result == []

    def test_sold_out_batch_excluded(self):
        result = resolve_display_batch([_batch(stock_qty=5, reserved_qty=5)], user_region="cn-east")
        assert result == []

    def test_inactive_status_excluded(self):
        result = resolve_display_batch([_batch(status="inactive")], user_region="cn-east")
        assert result == []

    def test_uninspected_batch_excluded(self):
        result = resolve_display_batch([_batch(inspection_status="pending")], user_region="cn-east")
        assert result == []

    def test_available_qty_computed_as_stock_minus_reserved(self):
        result = resolve_display_batch(
            [_batch(stock_qty=10, reserved_qty=3)], user_region="cn-east"
        )
        assert result[0]["available_qty"] == 7

    def test_home_batches_sorted_before_non_home(self):
        home = _batch(id="home", location_region="cn-east")
        near_other = _batch(
            id="near", location_region="cn-south", location_lat=31.25, location_lng=121.50
        )
        result = resolve_display_batch(
            [near_other, home],
            user_region="cn-east",
            user_lat=31.23,
            user_lng=121.47,
            max_distance_km=100.0,
        )
        assert [b["id"] for b in result] == ["home", "near"]

    def test_non_home_batches_sorted_by_distance_ascending(self):
        far = _batch(id="far", location_region="x", location_lat=31.50, location_lng=121.80)
        near = _batch(id="near", location_region="x", location_lat=31.24, location_lng=121.48)
        result = resolve_display_batch(
            [far, near],
            user_region="cn-east",
            user_lat=31.23,
            user_lng=121.47,
            max_distance_km=200.0,
        )
        assert [b["id"] for b in result] == ["near", "far"]

    def test_limit_truncates_results(self):
        batches = [_batch(id=str(i)) for i in range(5)]
        result = resolve_display_batch(batches, user_region="cn-east", limit=2)
        assert len(result) == 2

    def test_no_user_region_excludes_all_non_matching(self):
        # user_region=None means nothing can be "home", and coords are also absent
        # here so nothing is includable.
        result = resolve_display_batch([_batch()], user_region=None)
        assert result == []
