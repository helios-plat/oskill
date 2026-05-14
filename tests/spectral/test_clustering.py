"""Tests for spectral_asset_clustering."""

from __future__ import annotations

import numpy as np
import pytest

from oskill.spectral.clustering import spectral_asset_clustering


def make_block_correlation(n_per_block: int = 5, n_blocks: int = 2, seed: int = 42) -> np.ndarray:
    """Build a block-diagonal correlation matrix (clear clusters)."""
    N = n_per_block * n_blocks
    C = np.eye(N)
    rng = np.random.default_rng(seed)
    for b in range(n_blocks):
        idx = slice(b * n_per_block, (b + 1) * n_per_block)
        noise = rng.random((n_per_block, n_per_block)) * 0.05
        C[idx, idx] += 0.8 + noise
    # Symmetrize and make PD
    C = (C + C.T) / 2
    np.fill_diagonal(C, 1.0)
    return C


def make_identity_corr(n: int = 6) -> np.ndarray:
    return np.eye(n)


class TestSpectralAssetClusteringSpectralLaplacian:
    def test_returns_dict_keys(self):
        C = make_block_correlation()
        result = spectral_asset_clustering(C, method="spectral_laplacian", n_clusters=2)
        assert "cluster_labels" in result
        assert "graph_edges" in result
        assert "modularity" in result
        assert "n_clusters_inferred" in result

    def test_two_blocks_detected(self):
        """Block-diagonal correlation → 2 clusters."""
        C = make_block_correlation(5, 2)
        result = spectral_asset_clustering(C, method="spectral_laplacian", n_clusters=2)
        labels = result["cluster_labels"]
        assert result["n_clusters_inferred"] == 2
        # First 5 in same cluster, next 5 in same cluster
        assert len(set(labels[:5])) == 1
        assert len(set(labels[5:])) == 1
        assert labels[0] != labels[5]

    def test_label_count_matches_n(self):
        C = make_block_correlation(4, 3)
        result = spectral_asset_clustering(C, method="spectral_laplacian", n_clusters=3)
        assert len(result["cluster_labels"]) == 12

    def test_modularity_finite(self):
        C = make_block_correlation()
        result = spectral_asset_clustering(C, method="spectral_laplacian", n_clusters=2)
        assert np.isfinite(result["modularity"])

    def test_mantegna_distance_transform(self):
        C = make_block_correlation()
        result = spectral_asset_clustering(C, distance_transform="mantegna", n_clusters=2)
        assert len(result["cluster_labels"]) == 10

    def test_absolute_distance_transform(self):
        C = make_block_correlation()
        result = spectral_asset_clustering(C, distance_transform="absolute", n_clusters=2)
        assert len(result["cluster_labels"]) == 10


class TestSpectralAssetClusteringMST:
    def test_mst_n_minus_one_edges(self):
        """MST has exactly N-1 edges."""
        C = make_block_correlation(4, 2)  # N=8
        result = spectral_asset_clustering(C, method="mst", n_clusters=2)
        # After removing k-1 = 1 edges, we have N-1 - (k-1) = N-k edges
        # total MST edges = N-1 = 7, after removing k-1=1 → 6 edges in graph_edges
        n = 8
        # Total MST edges were N-1=7, we removed k-1=1, so edges_list has 6
        assert len(result["graph_edges"]) == n - 2  # N-1 - (k-1)

    def test_mst_returns_correct_n_clusters(self):
        C = make_block_correlation(4, 2)
        result = spectral_asset_clustering(C, method="mst", n_clusters=2)
        assert result["n_clusters_inferred"] == 2

    def test_mst_labels_shape(self):
        C = make_block_correlation(3, 3)
        result = spectral_asset_clustering(C, method="mst", n_clusters=3)
        assert len(result["cluster_labels"]) == 9


class TestSpectralAssetClusteringPMFG:
    def test_pmfg_returns_expected_keys(self):
        C = make_block_correlation(4, 2)
        result = spectral_asset_clustering(C, method="pmfg", n_clusters=2)
        assert "cluster_labels" in result
        assert "n_clusters_inferred" in result

    def test_pmfg_labels_correct_shape(self):
        N = 8
        C = make_block_correlation(4, 2)
        result = spectral_asset_clustering(C, method="pmfg", n_clusters=2)
        assert len(result["cluster_labels"]) == N


class TestSpectralAssetClusteringEdgeCases:
    def test_leiden_falls_back_to_kmeans(self):
        """leiden algorithm should work (falls back to KMeans)."""
        C = make_block_correlation()
        result = spectral_asset_clustering(C, clustering_algorithm="leiden", n_clusters=2)
        assert len(result["cluster_labels"]) == 10

    def test_non_square_raises(self):
        with pytest.raises(ValueError):
            spectral_asset_clustering(np.ones((3, 4)))
