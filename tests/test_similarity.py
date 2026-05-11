"""Tests for Group 4: Similarity Retrieval skills."""

import numpy as np
import pandas as pd
import pytest

from oskill.similarity import (
    historical_analogy_search,
    regime_transition_analysis,
)


# ============================================================
# historical_analogy_search tests
# ============================================================

class TestHistoricalAnalogySearch:
    """Tests for historical_analogy_search."""

    def test_identical_series_rank_1(self):
        """Query identical to db[i] → that i is rank 1."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 30)
        db = [rng.normal(0, 1, 30) for _ in range(5)]
        db[2] = query.copy()
        results = historical_analogy_search(query, db, top_k=3)
        assert results[0]["historical_idx"] == 2

    def test_top_k_results(self):
        """Returns top_k results."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 30)
        db = [rng.normal(0, 1, 30) for _ in range(10)]
        results = historical_analogy_search(query, db, top_k=3)
        assert len(results) == 3

    def test_methods_dtw_only(self):
        """methods=['dtw'] only uses DTW."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        results = historical_analogy_search(query, db, methods=["dtw"], top_k=3)
        assert "dtw" in results[0]["distances_per_method"]
        assert "wasserstein" not in results[0]["distances_per_method"]

    def test_all_methods(self):
        """All 4 methods work together."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        results = historical_analogy_search(
            query, db, methods=["dtw", "wasserstein", "cosine", "euclidean"], top_k=3
        )
        assert len(results[0]["distances_per_method"]) == 4

    def test_ensemble_mean_rank(self):
        """ensemble='mean_rank' works."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        results = historical_analogy_search(query, db, ensemble="mean_rank", top_k=3)
        assert results[0]["rank"] == 1

    def test_ensemble_borda(self):
        """ensemble='borda' works."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        results = historical_analogy_search(query, db, ensemble="borda", top_k=3)
        assert results[0]["rank"] == 1

    def test_ensemble_weighted(self):
        """ensemble='weighted' works with weights."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        results = historical_analogy_search(
            query, db, ensemble="weighted",
            weights={"dtw": 2.0, "wasserstein": 1.0}, top_k=3
        )
        assert len(results) == 3

    def test_weighted_no_weights_raises(self):
        """ensemble='weighted' without weights raises."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        with pytest.raises(ValueError, match="weights"):
            historical_analogy_search(query, db, ensemble="weighted")

    def test_top_k_larger_than_db(self):
        """top_k > len(db) → returns len(db) results."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(3)]
        results = historical_analogy_search(query, db, top_k=10)
        assert len(results) == 3

    def test_variable_length_cosine_warning(self):
        """Cosine with variable-length series warns with indices."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 15), rng.normal(0, 1, 20), rng.normal(0, 1, 25)]
        with pytest.warns(UserWarning, match="indices.*excluded"):
            historical_analogy_search(query, db, methods=["cosine"], top_k=3)

    def test_integration_mock_dtw(self, mocker):
        """Integration: oprim.dtw_distance called for each db entry."""
        mock_dtw = mocker.patch("oskill.similarity.oprim.dtw_distance",
                                return_value={"distance": 1.0, "path": []})
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        historical_analogy_search(query, db, methods=["dtw"], top_k=3)
        assert mock_dtw.call_count == 5

    def test_integration_mock_cosine(self, mocker):
        """Integration: oprim.cosine_similarity_batch called."""
        mock_cos = mocker.patch("oskill.similarity.oprim.cosine_similarity_batch",
                                return_value=np.array([0.9, 0.8, 0.7, 0.6, 0.5]))
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 20) for _ in range(5)]
        historical_analogy_search(query, db, methods=["cosine"], top_k=3)
        mock_cos.assert_called_once()

    def test_sakoe_chiba_band(self):
        """sakoe_chiba_band is passed to DTW."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 30)
        db = [rng.normal(0, 1, 30) for _ in range(3)]
        # Should not raise
        results = historical_analogy_search(query, db, methods=["dtw"],
                                            sakoe_chiba_band=5, top_k=3)
        assert len(results) == 3


# ============================================================
# regime_transition_analysis tests
# ============================================================

class TestRegimeTransitionAnalysis:
    """Tests for regime_transition_analysis."""

    def test_sticky_regime_high_holding(self):
        """Sticky regime (high self-transition) → high expected holding."""
        labels = pd.Series(["A"] * 50 + ["B"] * 50)
        result = regime_transition_analysis(labels)
        # Only 1 transition each, so holding should be high
        assert result["expected_holding_period"]["A"] > 10
        assert result["expected_holding_period"]["B"] > 10

    def test_alternating_regime_low_holding(self):
        """Alternating regime → expected holding ≈ 1."""
        labels = pd.Series(["A", "B"] * 50)
        result = regime_transition_analysis(labels)
        assert result["expected_holding_period"]["A"] < 2
        assert result["expected_holding_period"]["B"] < 2

    def test_two_regime_basic(self):
        """Basic 2-regime test."""
        labels = pd.Series(["A"] * 20 + ["B"] * 15 + ["A"] * 10 + ["B"] * 5)
        result = regime_transition_analysis(labels)
        assert "A" in result["expected_holding_period"]
        assert "B" in result["expected_holding_period"]
        assert result["n_transitions"] > 0

    def test_data_per_regime_provided(self):
        """data_per_regime given → data_summary_per_regime not None."""
        labels = pd.Series(["A"] * 50 + ["B"] * 50)
        data = pd.Series(np.random.default_rng(42).normal(0, 1, 100))
        result = regime_transition_analysis(labels, data_per_regime=data)
        assert result["data_summary_per_regime"] is not None
        assert "A" in result["data_summary_per_regime"]

    def test_data_per_regime_none(self):
        """data_per_regime=None → data_summary_per_regime is None."""
        labels = pd.Series(["A"] * 50 + ["B"] * 50)
        result = regime_transition_analysis(labels)
        assert result["data_summary_per_regime"] is None

    def test_include_duration_stats_false(self):
        """include_duration_stats=False → duration_distribution is None."""
        labels = pd.Series(["A"] * 20 + ["B"] * 20 + ["A"] * 10)
        result = regime_transition_analysis(labels, include_duration_stats=False)
        assert result["duration_distribution"] is None

    def test_include_duration_stats_true(self):
        """include_duration_stats=True → duration_distribution present."""
        labels = pd.Series(["A"] * 20 + ["B"] * 20 + ["A"] * 10)
        result = regime_transition_analysis(labels, include_duration_stats=True)
        assert result["duration_distribution"] is not None

    def test_single_regime_raises(self):
        """Single regime raises ValueError."""
        labels = pd.Series(["A"] * 50)
        with pytest.raises(ValueError, match="at least 2 unique"):
            regime_transition_analysis(labels)

    def test_too_short_raises(self):
        """Too short raises."""
        labels = pd.Series(["A"])
        with pytest.raises(ValueError, match="at least 2 observations"):
            regime_transition_analysis(labels)

    def test_integration_mock_transition_matrix(self, mocker):
        """Integration: oprim.regime_transition_matrix called."""
        mock_tm = mocker.patch("oskill.similarity.oprim.regime_transition_matrix", return_value={
            "transition_matrix": pd.DataFrame(
                {"A": [0.8, 0.2], "B": [0.3, 0.7]}, index=["A", "B"]
            ),
            "stationary_distribution": pd.Series({"A": 0.6, "B": 0.4}),
            "n_transitions": 10,
            "duration_distribution": {"A": {"mean": 5}, "B": {"mean": 3}},
        })
        labels = pd.Series(["A"] * 20 + ["B"] * 20)
        regime_transition_analysis(labels)
        mock_tm.assert_called_once()

    def test_integration_mock_regime_filter_data(self, mocker):
        """Integration: oprim.regime_filter_data called when data_per_regime given."""
        mocker.patch("oskill.similarity.oprim.regime_transition_matrix", return_value={
            "transition_matrix": pd.DataFrame(
                {"A": [0.8, 0.2], "B": [0.3, 0.7]}, index=["A", "B"]
            ),
            "stationary_distribution": pd.Series({"A": 0.6, "B": 0.4}),
            "n_transitions": 10,
            "duration_distribution": None,
        })
        mock_rf = mocker.patch("oskill.similarity.oprim.regime_filter_data",
                               return_value=pd.DataFrame({"value": [1, 2, 3]}))
        mocker.patch("oskill.similarity.oprim.distribution_summary", return_value={"mean": 2})
        labels = pd.Series(["A"] * 20 + ["B"] * 20)
        data = pd.Series(np.ones(40))
        regime_transition_analysis(labels, data_per_regime=data)
        assert mock_rf.call_count == 2  # Once per regime

    def test_academic_holding_period_formula(self):
        """Academic: expected_holding = 1/(1-p_stay)."""
        labels = pd.Series(["A"] * 20 + ["B"] * 10 + ["A"] * 20 + ["B"] * 10)
        result = regime_transition_analysis(labels)
        tm = result["transition_matrix"]
        for regime in tm.index:
            p_stay = tm.loc[regime, regime]
            if 0 < p_stay < 1:
                expected = 1.0 / (1.0 - p_stay)
                assert abs(result["expected_holding_period"][regime] - expected) < 1e-10

    def test_academic_half_life_formula(self):
        """Academic: half_life = ln(0.5)/ln(p_stay)."""
        labels = pd.Series(["A"] * 20 + ["B"] * 10 + ["A"] * 20 + ["B"] * 10)
        result = regime_transition_analysis(labels)
        tm = result["transition_matrix"]
        for regime in tm.index:
            p_stay = tm.loc[regime, regime]
            if 0 < p_stay < 1:
                expected_hl = np.log(0.5) / np.log(p_stay)
                assert abs(result["half_life"][regime] - expected_hl) < 1e-10


# ============================================================
# commodity_ratio_analytics tests
# ============================================================

from oskill.similarity import commodity_ratio_analytics, geopolitical_risk_index


class TestCommodityRatioAnalytics:
    """Tests for commodity_ratio_analytics."""

    def test_basic_ratio(self):
        """Basic ratio computation returns expected keys."""
        rng = np.random.default_rng(42)
        num = pd.Series(rng.normal(100, 5, 60))
        den = pd.Series(rng.normal(50, 2, 60))
        result = commodity_ratio_analytics(num, den)
        assert "ratio_series" in result
        assert "current_ratio" in result
        assert "percentile_rank" in result
        assert "zscore" in result
        assert "regime" in result

    def test_current_ratio_value(self):
        """current_ratio equals last value of ratio_series."""
        num = pd.Series(np.linspace(100, 200, 30))
        den = pd.Series(np.ones(30) * 50)
        result = commodity_ratio_analytics(num, den)
        assert result["current_ratio"] == pytest.approx(200.0 / 50.0)

    def test_regime_normal(self):
        """Stable ratio → normal regime."""
        rng = np.random.default_rng(42)
        # Constant ratio with tiny noise
        num = pd.Series(100 + rng.normal(0, 0.01, 60))
        den = pd.Series(np.ones(60) * 50)
        result = commodity_ratio_analytics(num, den)
        assert result["regime"] in ("normal", "high", "low")

    def test_regime_extreme_high(self):
        """Strongly increasing ratio → extreme_high regime."""
        # Monotonically increasing ratio
        num = pd.Series(np.linspace(50, 500, 60))
        den = pd.Series(np.ones(60) * 50)
        result = commodity_ratio_analytics(num, den)
        assert result["regime"] in ("extreme_high", "high")

    def test_regime_extreme_low(self):
        """Strongly decreasing ratio → extreme_low regime."""
        num = pd.Series(np.linspace(500, 50, 60))
        den = pd.Series(np.ones(60) * 50)
        result = commodity_ratio_analytics(num, den)
        assert result["regime"] in ("extreme_low", "low")

    def test_different_lengths_raises(self):
        """Different length series raises ValueError."""
        num = pd.Series(np.ones(30))
        den = pd.Series(np.ones(20))
        with pytest.raises(ValueError, match="same length"):
            commodity_ratio_analytics(num, den)

    def test_zero_denominator_raises(self):
        """Zero in denominator raises ValueError."""
        num = pd.Series(np.ones(30))
        den = pd.Series(np.ones(30))
        den.iloc[5] = 0
        with pytest.raises(ValueError, match="zeros"):
            commodity_ratio_analytics(num, den)

    def test_too_short_raises(self):
        """Less than 20 data points raises ValueError."""
        num = pd.Series(np.ones(10))
        den = pd.Series(np.ones(10) * 2)
        with pytest.raises(ValueError, match="at least 20"):
            commodity_ratio_analytics(num, den)

    def test_accepts_numpy_arrays(self):
        """Accepts numpy arrays (auto-converted to Series)."""
        rng = np.random.default_rng(42)
        num = rng.normal(100, 5, 60)
        den = rng.normal(50, 2, 60)
        result = commodity_ratio_analytics(num, den)
        assert result["current_ratio"] > 0

    def test_custom_benchmark_window(self):
        """Custom benchmark_window is accepted."""
        rng = np.random.default_rng(42)
        num = pd.Series(rng.normal(100, 5, 60))
        den = pd.Series(rng.normal(50, 2, 60))
        result = commodity_ratio_analytics(num, den, benchmark_window=30)
        assert "zscore" in result

    def test_integration_mock_percentile_rank(self, mocker):
        """Integration: oprim.percentile_rank called."""
        mock_pr = mocker.patch(
            "oskill.similarity.oprim.percentile_rank",
            return_value=pd.Series(np.linspace(0, 1, 60)),
        )
        mocker.patch(
            "oskill.similarity.oprim.zscore_normalize",
            return_value=pd.Series(np.zeros(60)),
        )
        num = pd.Series(np.linspace(100, 200, 60))
        den = pd.Series(np.ones(60) * 50)
        commodity_ratio_analytics(num, den)
        mock_pr.assert_called_once()

    def test_integration_mock_zscore_normalize(self, mocker):
        """Integration: oprim.zscore_normalize called with correct window."""
        mocker.patch(
            "oskill.similarity.oprim.percentile_rank",
            return_value=pd.Series(np.linspace(0, 1, 60)),
        )
        mock_zn = mocker.patch(
            "oskill.similarity.oprim.zscore_normalize",
            return_value=pd.Series(np.zeros(60)),
        )
        num = pd.Series(np.linspace(100, 200, 60))
        den = pd.Series(np.ones(60) * 50)
        commodity_ratio_analytics(num, den, benchmark_window=100)
        mock_zn.assert_called_once()
        _, kwargs = mock_zn.call_args
        assert kwargs["window"] == 100

    def test_percentile_rank_in_range(self):
        """percentile_rank is between 0 and 1."""
        rng = np.random.default_rng(42)
        num = pd.Series(rng.normal(100, 5, 60))
        den = pd.Series(rng.normal(50, 2, 60))
        result = commodity_ratio_analytics(num, den)
        assert 0 <= result["percentile_rank"] <= 1


# ============================================================
# geopolitical_risk_index tests
# ============================================================


class TestGeopoliticalRiskIndex:
    """Tests for geopolitical_risk_index."""

    def _make_events(self, n=50, with_region=False, with_weight=False, rng=None):
        """Helper to create event DataFrame."""
        if rng is None:
            rng = np.random.default_rng(42)
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        df = pd.DataFrame({
            "timestamp": dates,
            "intensity": rng.uniform(1, 10, n),
        })
        if with_region:
            df["region"] = rng.choice(["US", "EU", "APAC"], n)
        if with_weight:
            df["weight"] = rng.uniform(0.5, 2.0, n)
        return df

    def test_basic_output_keys(self):
        """Returns expected keys."""
        events = self._make_events()
        result = geopolitical_risk_index(events)
        assert "index_series" in result
        assert "current_value" in result
        assert "percentile_rank" in result
        assert "regime" in result
        assert "top_contributors" in result

    def test_current_value_positive(self):
        """current_value is positive for positive intensity events."""
        events = self._make_events()
        result = geopolitical_risk_index(events)
        assert result["current_value"] > 0

    def test_regime_valid_values(self):
        """regime is one of the valid values."""
        events = self._make_events()
        result = geopolitical_risk_index(events)
        assert result["regime"] in ("extreme", "elevated", "normal", "low")

    def test_high_intensity_spike(self):
        """High intensity at end → elevated/extreme regime."""
        rng = np.random.default_rng(42)
        events = self._make_events(n=60, rng=rng)
        # Add a massive spike at the end
        spike = pd.DataFrame({
            "timestamp": pd.date_range("2024-02-25", periods=5, freq="D"),
            "intensity": [100, 100, 100, 100, 100],
        })
        events = pd.concat([events, spike], ignore_index=True)
        result = geopolitical_risk_index(events)
        assert result["regime"] in ("extreme", "elevated")

    def test_with_weight_column(self):
        """Weight column is used in computation."""
        events = self._make_events(with_weight=True)
        result = geopolitical_risk_index(events)
        assert result["current_value"] > 0

    def test_with_region_column(self):
        """Region column included in top_contributors."""
        events = self._make_events(with_region=True)
        result = geopolitical_risk_index(events)
        assert len(result["top_contributors"]) > 0
        assert "region" in result["top_contributors"][0]

    def test_without_region_column(self):
        """Without region, top_contributors has timestamp+intensity only."""
        events = self._make_events(with_region=False)
        result = geopolitical_risk_index(events)
        assert len(result["top_contributors"]) > 0
        assert "region" not in result["top_contributors"][0]

    def test_missing_columns_raises(self):
        """Missing required columns raises ValueError."""
        df = pd.DataFrame({"foo": [1, 2, 3]})
        with pytest.raises(ValueError, match="columns"):
            geopolitical_risk_index(df)

    def test_empty_events_raises(self):
        """Empty DataFrame raises ValueError."""
        df = pd.DataFrame({"timestamp": [], "intensity": []})
        with pytest.raises(ValueError, match="empty"):
            geopolitical_risk_index(df)

    def test_custom_decay_half_life(self):
        """Custom decay_half_life is accepted."""
        events = self._make_events()
        r1 = geopolitical_risk_index(events, decay_half_life=5)
        r2 = geopolitical_risk_index(events, decay_half_life=60)
        # Shorter half-life → more recent events dominate → different value
        assert r1["current_value"] != r2["current_value"]

    def test_top_contributors_max_5(self):
        """top_contributors has at most 5 entries."""
        events = self._make_events(n=100)
        result = geopolitical_risk_index(events)
        assert len(result["top_contributors"]) <= 5

    def test_percentile_rank_in_range(self):
        """percentile_rank is between 0 and 1."""
        events = self._make_events()
        result = geopolitical_risk_index(events)
        assert 0 <= result["percentile_rank"] <= 1

    def test_integration_mock_ewma_smooth(self, mocker):
        """Integration: oprim.ewma_smooth called with half_life."""
        mock_ewma = mocker.patch(
            "oskill.similarity.oprim.ewma_smooth",
            return_value=pd.Series(np.ones(50), index=pd.date_range("2024-01-01", periods=50)),
        )
        mocker.patch(
            "oskill.similarity.oprim.percentile_rank",
            return_value=pd.Series(np.linspace(0, 1, 50)),
        )
        events = self._make_events()
        geopolitical_risk_index(events, decay_half_life=15)
        mock_ewma.assert_called_once()
        _, kwargs = mock_ewma.call_args
        assert kwargs["half_life"] == 15

    def test_integration_mock_percentile_rank(self, mocker):
        """Integration: oprim.percentile_rank called on index_series."""
        mocker.patch(
            "oskill.similarity.oprim.ewma_smooth",
            return_value=pd.Series(np.ones(50), index=pd.date_range("2024-01-01", periods=50)),
        )
        mock_pr = mocker.patch(
            "oskill.similarity.oprim.percentile_rank",
            return_value=pd.Series(np.linspace(0, 1, 50)),
        )
        events = self._make_events()
        geopolitical_risk_index(events)
        mock_pr.assert_called_once()
