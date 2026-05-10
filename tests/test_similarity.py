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
        """Cosine with variable-length series warns."""
        rng = np.random.default_rng(42)
        query = rng.normal(0, 1, 20)
        db = [rng.normal(0, 1, 15), rng.normal(0, 1, 20), rng.normal(0, 1, 25)]
        with pytest.warns(UserWarning, match="different length"):
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
