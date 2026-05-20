"""Tests for oskill.signals.forward_returns.aggregate_signal_returns."""

from __future__ import annotations

import pytest

from oskill.signals.forward_returns import aggregate_signal_returns


def _make_event(fwd: dict) -> dict:
    return {"event_date": None, "entry_price": 10.0, "forward_returns": fwd}


class TestAggregateSignalReturnsBasic:
    def test_empty_events_returns_zero_n(self):
        result = aggregate_signal_returns([], [5, 10])
        assert result["n_events"] == 0

    def test_empty_events_per_period_zeros(self):
        result = aggregate_signal_returns([], [5])
        assert result["by_period"][5]["mean"] == 0.0
        assert result["by_period"][5]["win_rate"] == 0.0

    def test_empty_periods(self):
        events = [_make_event({5: 0.02})]
        result = aggregate_signal_returns(events, [])
        assert result["n_events"] == 1
        assert result["by_period"] == {}

    def test_n_events_count(self):
        events = [_make_event({5: 0.01}), _make_event({5: -0.02})]
        result = aggregate_signal_returns(events, [5])
        assert result["n_events"] == 2

    def test_single_positive_event(self):
        events = [_make_event({5: 0.05})]
        result = aggregate_signal_returns(events, [5])
        p = result["by_period"][5]
        assert abs(p["mean"] - 0.05) < 1e-9
        assert p["win_rate"] == 1.0
        assert p["std"] == 0.0

    def test_win_rate_half(self):
        events = [_make_event({10: 0.03}), _make_event({10: -0.02})]
        result = aggregate_signal_returns(events, [10])
        assert abs(result["by_period"][10]["win_rate"] - 0.5) < 1e-9

    def test_win_rate_zero(self):
        events = [_make_event({5: -0.01}), _make_event({5: -0.03})]
        result = aggregate_signal_returns(events, [5])
        assert result["by_period"][5]["win_rate"] == 0.0

    def test_mean_correct(self):
        events = [_make_event({5: 0.1}), _make_event({5: 0.3})]
        result = aggregate_signal_returns(events, [5])
        assert abs(result["by_period"][5]["mean"] - 0.2) < 1e-9

    def test_p25_p75_ordering(self):
        events = [_make_event({5: r}) for r in [0.01, 0.02, 0.03, 0.04]]
        result = aggregate_signal_returns(events, [5])
        p = result["by_period"][5]
        assert p["p25"] <= p["median"] <= p["p75"]

    def test_missing_period_for_event_skipped(self):
        events = [_make_event({5: 0.01}), _make_event({10: 0.02})]
        result = aggregate_signal_returns(events, [5])
        assert result["by_period"][5]["mean"] == pytest.approx(0.01)

    def test_no_events_for_period_returns_empty(self):
        events = [_make_event({10: 0.01})]
        result = aggregate_signal_returns(events, [20])
        p = result["by_period"][20]
        assert p["mean"] == 0.0
        assert p["max_drawdown"] == 0.0

    def test_max_drawdown_increasing_always_zero(self):
        events = [_make_event({5: 0.1}), _make_event({5: 0.2}), _make_event({5: 0.3})]
        result = aggregate_signal_returns(events, [5])
        assert result["by_period"][5]["max_drawdown"] == 0.0

    def test_max_drawdown_decreasing(self):
        events = [_make_event({5: 0.1}), _make_event({5: -0.5})]
        result = aggregate_signal_returns(events, [5])
        # cum = [0.1, -0.4], peak at 0.1, drawdown = 0.1 - (-0.4) = 0.5
        assert result["by_period"][5]["max_drawdown"] == pytest.approx(0.5)

    def test_multiple_periods_independent(self):
        events = [_make_event({5: 0.05, 10: -0.02})]
        result = aggregate_signal_returns(events, [5, 10])
        assert result["by_period"][5]["win_rate"] == 1.0
        assert result["by_period"][10]["win_rate"] == 0.0

    def test_std_single_event_zero(self):
        events = [_make_event({5: 0.03})]
        result = aggregate_signal_returns(events, [5])
        assert result["by_period"][5]["std"] == 0.0

    def test_std_positive_multiple_events(self):
        events = [_make_event({5: 0.01}), _make_event({5: 0.09})]
        result = aggregate_signal_returns(events, [5])
        assert result["by_period"][5]["std"] > 0.0


class TestAggregateSignalReturnsAcademic:
    @pytest.mark.academic_reference
    def test_lopezdeprado_ch4_event_forward_returns_pattern(self):
        """Lopez de Prado (2018) AFML Ch.4: event-study forward return aggregation.

        Given 4 events with known 5-day forward returns {+2%, +3%, -1%, +4%},
        mean = 2.0%, win_rate = 3/4 = 0.75, median = 2.5%, p25 = 1.25%, p75 = 3.25%.
        """
        events = [
            _make_event({5: 0.02}),
            _make_event({5: 0.03}),
            _make_event({5: -0.01}),
            _make_event({5: 0.04}),
        ]
        result = aggregate_signal_returns(events, [5])
        p = result["by_period"][5]
        assert result["n_events"] == 4
        assert abs(p["mean"] - 0.02) < 1e-9
        assert abs(p["win_rate"] - 0.75) < 1e-9
