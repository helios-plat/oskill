"""Tests for meta_labeling function."""

import numpy as np
import pandas as pd
import pytest

from oskill.ml_finance.meta_labeling import meta_labeling


class TestMetaLabeling:
    """Tests for meta_labeling."""

    def _make_signals_returns(self, rng: np.random.Generator, n: int = 50):
        signals = rng.choice([-1.0, 1.0], size=n)
        returns = rng.normal(0, 0.01, size=n)
        return signals, returns

    def test_returns_required_keys(self):
        """Result must contain all required keys."""
        rng = np.random.default_rng(1)
        signals, returns = self._make_signals_returns(rng)
        result = meta_labeling(signals, returns)
        assert "meta_labels" in result
        assert "meta_label_balance" in result
        assert "precision_baseline" in result
        assert "estimated_precision_with_meta" in result

    def test_meta_labels_binary(self):
        """meta_labels must be in {0, 1}."""
        rng = np.random.default_rng(2)
        signals, returns = self._make_signals_returns(rng, 100)
        result = meta_labeling(signals, returns)
        unique = set(result["meta_labels"].tolist())
        assert unique.issubset({0, 1})

    def test_meta_labels_length(self):
        """meta_labels should match input length."""
        rng = np.random.default_rng(3)
        signals, returns = self._make_signals_returns(rng, 80)
        result = meta_labeling(signals, returns)
        assert len(result["meta_labels"]) == 80

    def test_balance_sums_to_n(self):
        """Balance counts should sum to total observations."""
        rng = np.random.default_rng(4)
        n = 60
        signals, returns = self._make_signals_returns(rng, n)
        result = meta_labeling(signals, returns)
        balance = result["meta_label_balance"]
        assert balance[0] + balance[1] == n

    def test_precision_baseline_range(self):
        """precision_baseline should be in [0, 1]."""
        rng = np.random.default_rng(5)
        signals, returns = self._make_signals_returns(rng, 50)
        result = meta_labeling(signals, returns)
        assert 0.0 <= result["precision_baseline"] <= 1.0

    def test_perfect_signal(self):
        """A perfect signal (signal always matches return direction) should have high precision."""
        n = 30
        returns = np.array([0.01 * i for i in range(1, n + 1)])  # all positive
        signals = np.ones(n)  # all predict positive
        result = meta_labeling(signals, returns)
        assert result["precision_baseline"] == 1.0

    def test_with_triple_barrier_labels(self):
        """Should accept pre-computed triple barrier labels."""
        rng = np.random.default_rng(6)
        n = 40
        signals = rng.choice([-1.0, 1.0], size=n)
        returns = rng.normal(0, 0.01, size=n)
        tb_labels = rng.choice([-1, 0, 1], size=n)
        result = meta_labeling(signals, returns, triple_barrier_labels=tb_labels)
        assert len(result["meta_labels"]) == n
        assert "meta_labels" in result

    def test_pandas_series_input(self):
        """Should accept pd.Series inputs."""
        rng = np.random.default_rng(7)
        signals = pd.Series(rng.choice([-1.0, 1.0], size=30))
        returns = pd.Series(rng.normal(0, 0.01, 30))
        result = meta_labeling(signals, returns)
        assert len(result["meta_labels"]) == 30

    def test_shape_mismatch_raises(self):
        """Mismatched shapes should raise ValueError."""
        signals = np.ones(10)
        returns = np.ones(20)
        with pytest.raises(ValueError, match="length"):
            meta_labeling(signals, returns)
