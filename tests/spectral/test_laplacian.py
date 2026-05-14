"""Tests for graph_laplacian_compute."""

from __future__ import annotations

import numpy as np
import pytest

from oskill.spectral.laplacian import graph_laplacian_compute


def make_connected_graph(n: int = 5, seed: int = 42) -> np.ndarray:
    """Build a symmetric connected adjacency matrix."""
    rng = np.random.default_rng(seed)
    W = rng.random((n, n))
    W = (W + W.T) / 2
    np.fill_diagonal(W, 0.0)
    return W


def make_disconnected_graph() -> np.ndarray:
    """Two disconnected components: nodes 0-1 and 2-3."""
    W = np.zeros((4, 4))
    W[0, 1] = W[1, 0] = 1.0
    W[2, 3] = W[3, 2] = 1.0
    return W


def make_path_graph(n: int = 5) -> np.ndarray:
    """Path graph: 0-1-2-...(n-1)."""
    W = np.zeros((n, n))
    for i in range(n - 1):
        W[i, i + 1] = W[i + 1, i] = 1.0
    return W


class TestGraphLaplacianConnected:
    def test_returns_dict_with_keys(self):
        W = make_connected_graph(12)
        result = graph_laplacian_compute(W)
        assert "laplacian" in result
        assert "eigenvalues" in result
        assert "eigenvectors" in result
        assert "n_connected_components" in result

    def test_laplacian_shape(self):
        W = make_connected_graph(6)
        result = graph_laplacian_compute(W, n_eigenvalues=5)
        assert result["laplacian"].shape == (6, 6)
        assert result["eigenvalues"].shape == (5,)
        assert result["eigenvectors"].shape == (6, 5)

    def test_connected_graph_one_zero_eigenvalue(self):
        """A connected graph has exactly one zero eigenvalue."""
        W = make_connected_graph(5)
        result = graph_laplacian_compute(W, normalization="unnormalized", n_eigenvalues=5)
        assert result["n_connected_components"] == 1

    def test_disconnected_two_zero_eigenvalues(self):
        """Two connected components → two zero eigenvalues."""
        W = make_disconnected_graph()
        result = graph_laplacian_compute(W, normalization="unnormalized", n_eigenvalues=4)
        assert result["n_connected_components"] == 2

    def test_symmetric_laplacian_is_psd(self):
        """Symmetric normalized Laplacian is positive semi-definite."""
        W = make_connected_graph(12)
        result = graph_laplacian_compute(W, normalization="symmetric", n_eigenvalues=5)
        eigs = result["eigenvalues"]
        assert np.all(eigs >= -1e-10)

    def test_unnormalized_laplacian_correct(self):
        """L = D - W for unnormalized."""
        W = make_path_graph(4)
        result = graph_laplacian_compute(W, normalization="unnormalized", return_eigendecomp=False)
        D = np.diag(W.sum(axis=1))
        expected = D - W
        np.testing.assert_allclose(result["laplacian"], expected, atol=1e-12)

    def test_no_eigendecomp(self):
        """return_eigendecomp=False should not have eigenvalue keys."""
        W = make_connected_graph(4)
        result = graph_laplacian_compute(W, return_eigendecomp=False)
        assert "eigenvalues" not in result
        assert "eigenvectors" not in result

    def test_n_eigenvalues_capped_at_n(self):
        """n_eigenvalues larger than N raises ValueError."""
        W = make_connected_graph(3)
        with pytest.raises(ValueError, match="n_eigenvalues"):
            graph_laplacian_compute(W, n_eigenvalues=10)

    def test_random_walk_laplacian_shape(self):
        W = make_connected_graph(5)
        result = graph_laplacian_compute(W, normalization="random_walk", n_eigenvalues=4)
        assert result["laplacian"].shape == (5, 5)

    def test_invalid_normalization(self):
        W = make_connected_graph(3)
        with pytest.raises((ValueError, KeyError)):
            graph_laplacian_compute(W, normalization="bogus")  # type: ignore[arg-type]

    def test_non_square_raises(self):
        with pytest.raises(ValueError, match="square"):
            graph_laplacian_compute(np.ones((3, 4)))

    def test_negative_adjacency_raises(self):
        W = -np.ones((3, 3))
        with pytest.raises(ValueError, match="non-negative"):
            graph_laplacian_compute(W)

    def test_path_graph_eigenvalues_sorted(self):
        W = make_path_graph(5)
        result = graph_laplacian_compute(W, normalization="unnormalized", n_eigenvalues=5)
        eigs = result["eigenvalues"]
        assert np.all(np.diff(eigs) >= -1e-10)  # ascending


class TestGraphLaplacianMultipleComponents:
    def test_three_components(self):
        """Three disconnected nodes → 3 zero eigenvalues."""
        W = np.zeros((3, 3))
        result = graph_laplacian_compute(W, normalization="unnormalized", n_eigenvalues=3)
        assert result["n_connected_components"] == 3

    def test_eigenvectors_orthonormal(self):
        """eigh should return orthonormal eigenvectors."""
        W = make_connected_graph(5)
        result = graph_laplacian_compute(W, n_eigenvalues=5)
        V = result["eigenvectors"]
        VtV = V.T @ V
        np.testing.assert_allclose(VtV, np.eye(5), atol=1e-10)
