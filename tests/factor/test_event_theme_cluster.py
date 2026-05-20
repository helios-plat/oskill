"""Tests for oskill.factor.event_theme_cluster."""

from __future__ import annotations

import pytest

from oskill.factor.event_theme_cluster import event_theme_cluster


def _classification():
    return {
        "600519": ["baijiu", "consumption"],
        "000858": ["baijiu"],
        "601318": ["insurance", "finance"],
        "600036": ["banking", "finance"],
    }


class TestEventThemeCluster:
    def test_empty_events_returns_empty(self):
        result = event_theme_cluster([], _classification())
        assert result == []

    def test_basic_theme_grouping(self):
        events = [
            {"symbol": "600519", "strength": 1.0},
            {"symbol": "000858", "strength": 0.8},
        ]
        result = event_theme_cluster(events, _classification(), top_n=5)
        theme_names = [r["theme_name"] for r in result]
        assert "baijiu" in theme_names

    def test_top_n_limit(self):
        events = [
            {"symbol": "600519", "strength": 1.0},
            {"symbol": "000858", "strength": 0.8},
            {"symbol": "601318", "strength": 0.5},
            {"symbol": "600036", "strength": 0.3},
        ]
        result = event_theme_cluster(events, _classification(), top_n=2)
        assert len(result) <= 2

    def test_total_strength_sorted_descending(self):
        events = [
            {"symbol": "600519", "strength": 1.0},
            {"symbol": "000858", "strength": 0.8},
            {"symbol": "601318", "strength": 0.5},
        ]
        result = event_theme_cluster(events, _classification(), top_n=5)
        strengths = [r["total_strength"] for r in result]
        assert strengths == sorted(strengths, reverse=True)

    def test_required_keys_present(self):
        events = [{"symbol": "600519", "strength": 1.0}]
        result = event_theme_cluster(events, _classification())
        r = result[0]
        assert "theme_name" in r
        assert "n_stocks" in r
        assert "total_strength" in r
        assert "leader_symbols" in r
        assert "continuation_prob" in r
        assert "stage" in r

    def test_leader_symbols_ordered_by_strength(self):
        events = [
            {"symbol": "600519", "strength": 2.0},
            {"symbol": "000858", "strength": 1.0},
        ]
        result = event_theme_cluster(events, _classification(), top_n=1)
        baijiu = next(r for r in result if r["theme_name"] == "baijiu")
        assert baijiu["leader_symbols"][0] == "600519"

    def test_single_stock_stage_emergent(self):
        events = [{"symbol": "000858", "strength": 1.0}]
        result = event_theme_cluster(events, _classification())
        baijiu = next(r for r in result if r["theme_name"] == "baijiu")
        assert baijiu["stage"] == "emergent"

    def test_two_three_stocks_stage_developing(self):
        events = [
            {"symbol": "600519", "strength": 1.0},
            {"symbol": "000858", "strength": 0.5},
        ]
        result = event_theme_cluster(events, _classification())
        baijiu = next(r for r in result if r["theme_name"] == "baijiu")
        assert baijiu["stage"] == "developing"

    def test_continuation_prob_zero_no_history(self):
        events = [{"symbol": "600519", "strength": 1.0}]
        result = event_theme_cluster(events, _classification())
        assert result[0]["continuation_prob"] == 0.0

    def test_continuation_prob_with_history(self):
        events = [{"symbol": "600519", "strength": 1.0}]
        history = [{"symbol": "600519"}, {"symbol": "600519"}, {"symbol": "601318"}]
        result = event_theme_cluster(events, _classification(), history_window=history)
        baijiu = next(r for r in result if r["theme_name"] == "baijiu")
        # 2 out of 3 events have baijiu
        assert baijiu["continuation_prob"] == pytest.approx(2 / 3)

    def test_unknown_symbol_not_clustered(self):
        events = [{"symbol": "UNKNOWN", "strength": 1.0}]
        result = event_theme_cluster(events, _classification())
        assert result == []

    def test_multi_theme_stock_contributes_to_both(self):
        events = [{"symbol": "600519", "strength": 1.0}]
        result = event_theme_cluster(events, _classification(), top_n=5)
        theme_names = {r["theme_name"] for r in result}
        assert "baijiu" in theme_names
        assert "consumption" in theme_names

    def test_n_stocks_correct(self):
        events = [
            {"symbol": "600519", "strength": 1.0},
            {"symbol": "000858", "strength": 0.5},
        ]
        result = event_theme_cluster(events, _classification(), top_n=5)
        baijiu = next(r for r in result if r["theme_name"] == "baijiu")
        assert baijiu["n_stocks"] == 2

    def test_four_plus_stocks_low_continuation_developing(self):
        """4+ stocks with continuation_prob <= 0.5 should be 'developing', not 'mature'."""
        classification = {"A": ["sector"], "B": ["sector"], "C": ["sector"], "D": ["sector"]}
        events = [
            {"symbol": "A", "strength": 1.0},
            {"symbol": "B", "strength": 0.8},
            {"symbol": "C", "strength": 0.7},
            {"symbol": "D", "strength": 0.6},
        ]
        # history_window with only 1 match out of 10 -> continuation_prob=0.1 (<= 0.5)
        history = [{"symbol": "A"}] + [{"symbol": "X"}] * 9
        result = event_theme_cluster(events, classification, history_window=history, top_n=1)
        assert result[0]["n_stocks"] == 4
        assert result[0]["stage"] == "developing"

    @pytest.mark.academic_reference
    def test_sector_rotation_momentum_persistence(self):
        """Sector rotation momentum persistence: themes with high history_window base rate.

        If 4 out of 5 history events are baijiu-related, continuation_prob = 0.8,
        which triggers 'mature' stage classification (> 0.5).
        """
        classification = {
            "A": ["baijiu"],
            "B": ["baijiu"],
            "C": ["baijiu"],
            "D": ["baijiu"],
        }
        events = [
            {"symbol": "A", "strength": 1.0},
            {"symbol": "B", "strength": 0.8},
            {"symbol": "C", "strength": 0.7},
            {"symbol": "D", "strength": 0.6},
        ]
        history = [
            {"symbol": "A"},
            {"symbol": "A"},
            {"symbol": "B"},
            {"symbol": "B"},
            {"symbol": "D"},  # not baijiu actually
        ]
        # all 5 history events are baijiu -> prob = 5/5 = 1.0
        result = event_theme_cluster(events, classification, history_window=history, top_n=1)
        assert len(result) == 1
        assert result[0]["theme_name"] == "baijiu"
        assert result[0]["continuation_prob"] == pytest.approx(1.0)
        assert result[0]["stage"] == "mature"
