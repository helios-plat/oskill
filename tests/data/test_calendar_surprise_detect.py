"""Tests for oskill.data.calendar_surprise_detect (B6)."""

from oskill.data.calendar_surprise_detect import calendar_surprise_detect


class TestCalendarSurpriseDetect:
    def test_major_surprise(self) -> None:
        events = [{"name": "Export", "actual": 78.5, "forecast": 15, "importance": 3}]
        result = calendar_surprise_detect(events=events)
        assert len(result) == 1
        assert result[0]["severity"] == "major"
        assert result[0]["surprise_pct"] > 50

    def test_forecast_zero_uses_absolute(self) -> None:
        events = [{"name": "CPI", "actual": 0.5, "forecast": 0, "importance": 2}]
        result = calendar_surprise_detect(events=events)
        assert len(result) == 1

    def test_actual_missing_skip(self) -> None:
        events = [{"name": "PMI", "actual": None, "forecast": 50, "importance": 2}]
        result = calendar_surprise_detect(events=events)
        assert len(result) == 0

    def test_importance_filter(self) -> None:
        events = [
            {"name": "A", "actual": 100, "forecast": 10, "importance": 1},
            {"name": "B", "actual": 100, "forecast": 10, "importance": 3},
        ]
        result = calendar_surprise_detect(events=events, importance_filter=3)
        assert len(result) == 1
        assert result[0]["name"] == "B"

    def test_minor_surprise(self) -> None:
        events = [{"name": "GDP", "actual": 5.2, "forecast": 5.0, "importance": 3}]
        result = calendar_surprise_detect(events=events)
        # 4% surprise < 5% threshold → no surprise
        assert len(result) == 0

    def test_zero_surprises(self) -> None:
        events = [{"name": "X", "actual": 50, "forecast": 50, "importance": 2}]
        result = calendar_surprise_detect(events=events)
        assert len(result) == 0

    def test_all_surprises(self) -> None:
        events = [
            {"name": "A", "actual": 100, "forecast": 10, "importance": 3},
            {"name": "B", "actual": 200, "forecast": 50, "importance": 2},
        ]
        result = calendar_surprise_detect(events=events)
        assert len(result) == 2
