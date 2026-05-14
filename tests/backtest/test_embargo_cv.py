"""Tests for embargo_purged_cv."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from oskill.backtest.embargo_cv import embargo_purged_cv


@pytest.fixture
def simple_data():
    rng = np.random.default_rng(42)
    T = 200
    X = pd.DataFrame(rng.standard_normal((T, 4)))
    y = pd.Series(rng.standard_normal(T))
    return X, y


def test_embargo_cv_basic(simple_data):
    X, y = simple_data
    splits = embargo_purged_cv(X, y, None, n_splits=5)
    assert isinstance(splits, list)
    assert len(splits) == 5
    for train_idx, test_idx in splits:
        assert isinstance(train_idx, np.ndarray)
        assert isinstance(test_idx, np.ndarray)


def test_embargo_cv_n_splits(simple_data):
    X, y = simple_data
    for n in (3, 5, 8):
        splits = embargo_purged_cv(X, y, None, n_splits=n)
        assert len(splits) == n


def test_embargo_cv_no_overlap(simple_data):
    X, y = simple_data
    splits = embargo_purged_cv(X, y, None, n_splits=5)
    for train_idx, test_idx in splits:
        overlap = np.intersect1d(train_idx, test_idx)
        assert len(overlap) == 0


def test_embargo_cv_embargo_removes_train_rows(simple_data):
    X, y = simple_data
    # Large embargo → training set shrinks relative to zero embargo
    splits_small = embargo_purged_cv(X, y, None, n_splits=5, embargo_pct=0.0)
    splits_large = embargo_purged_cv(X, y, None, n_splits=5, embargo_pct=0.1)
    for (tr_s, _), (tr_l, _) in zip(splits_small, splits_large):
        assert len(tr_l) <= len(tr_s)


def test_embargo_cv_with_datetime_index():
    T = 200
    dates = pd.date_range("2020-01-01", periods=T, freq="D")
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.standard_normal((T, 2)), index=dates)
    y = pd.Series(rng.standard_normal(T), index=dates)
    splits = embargo_purged_cv(X, y, None, n_splits=4)
    assert len(splits) == 4
    for train_idx, test_idx in splits:
        assert len(np.intersect1d(train_idx, test_idx)) == 0


def test_embargo_cv_train_larger_than_test(simple_data):
    X, y = simple_data
    splits = embargo_purged_cv(X, y, None, n_splits=5)
    for train_idx, test_idx in splits:
        assert len(train_idx) > len(test_idx)


def test_embargo_cv_purge_pct(simple_data):
    X, y = simple_data
    splits_no_purge = embargo_purged_cv(X, y, None, n_splits=5, purge_pct=0.0)
    splits_purge = embargo_purged_cv(X, y, None, n_splits=5, purge_pct=0.05)
    for (tr_np, _), (tr_p, _) in zip(splits_no_purge, splits_purge):
        assert len(tr_p) <= len(tr_np)
