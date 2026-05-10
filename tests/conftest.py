"""Shared test fixtures for oskill."""

import numpy as np
import pytest


@pytest.fixture
def rng():
    """Reproducible random number generator."""
    return np.random.default_rng(42)


@pytest.fixture
def normal_returns(rng):
    """Standard normal daily returns (252 days)."""
    return rng.normal(0.0005, 0.01, 252)


@pytest.fixture
def positive_returns(rng):
    """Positive-mean daily returns."""
    return rng.normal(0.001, 0.01, 252)
