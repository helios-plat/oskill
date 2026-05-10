"""Group 4: Similarity Retrieval skills."""

from __future__ import annotations

import warnings
from typing import Literal

import numpy as np
import pandas as pd

import oprim


def historical_analogy_search(
    query: np.ndarray,
    historical_db: list[np.ndarray] | np.ndarray,
    *,
    methods: list[Literal["dtw", "wasserstein", "cosine", "euclidean"]] | None = None,
    ensemble: Literal["mean_rank", "borda", "weighted"] = "mean_rank",
    weights: dict[str, float] | None = None,
    top_k: int = 10,
    sakoe_chiba_band: int | None = None,
) -> list[dict]:
    """Historical analogy ensemble search using multiple distance metrics.

    Calls:
        oprim.dtw_distance, oprim.wasserstein_distance,
        oprim.cosine_similarity_batch, oprim.euclidean_distance_matrix

    Args:
        query: Query time series (1D).
        historical_db: List of historical series or 2D array.
        methods: Distance methods to use. Default: ["dtw", "wasserstein"].
        ensemble: Ensemble strategy.
        weights: Method weights (required for 'weighted' ensemble).
        top_k: Number of top results to return.
        sakoe_chiba_band: Sakoe-Chiba band for DTW.

    Returns:
        List of dicts with rank, historical_idx, ensemble_score, distances, ranks.

    Raises:
        ValueError: If inputs are invalid.
    """
    if methods is None:
        methods = ["dtw", "wasserstein"]

    if ensemble == "weighted" and weights is None:
        raise ValueError("weights must be provided for 'weighted' ensemble")

    query = np.asarray(query, dtype=np.float64)

    # Normalize historical_db to list
    if isinstance(historical_db, np.ndarray) and historical_db.ndim == 2:
        db_list = [historical_db[i] for i in range(historical_db.shape[0])]
    else:
        db_list = [np.asarray(h, dtype=np.float64) for h in historical_db]

    n_db = len(db_list)
    if n_db == 0:
        raise ValueError("historical_db must not be empty")

    top_k = min(top_k, n_db)

    # Compute distances per method
    distances: dict[str, np.ndarray] = {}

    for method in methods:
        dists = np.full(n_db, np.inf)

        if method == "dtw":
            for i, h in enumerate(db_list):
                result = oprim.dtw_distance(query, h, window=sakoe_chiba_band)
                dists[i] = result["distance"]

        elif method == "wasserstein":
            for i, h in enumerate(db_list):
                dists[i] = oprim.wasserstein_distance(query, h)

        elif method == "cosine":
            # Cosine requires same length
            query_len = len(query)
            same_len = [i for i, h in enumerate(db_list) if len(h) == query_len]
            if len(same_len) < n_db:
                warnings.warn(
                    f"cosine: {n_db - len(same_len)} series have different length, skipped",
                    stacklevel=2,
                )
            if same_len:
                db_matrix = np.array([db_list[i] for i in same_len])
                sims = oprim.cosine_similarity_batch(query, db_matrix)
                for j, idx in enumerate(same_len):
                    dists[idx] = 1.0 - sims[j]  # Convert similarity to distance

        elif method == "euclidean":
            query_len = len(query)
            same_len = [i for i, h in enumerate(db_list) if len(h) == query_len]
            if same_len:
                db_matrix = np.array([db_list[i] for i in same_len])
                dist_matrix = oprim.euclidean_distance_matrix(
                    query.reshape(1, -1), db_matrix
                )
                for j, idx in enumerate(same_len):
                    dists[idx] = dist_matrix[0, j]

        distances[method] = dists

    # Compute ranks per method (1 = closest)
    ranks: dict[str, np.ndarray] = {}
    for method, dists in distances.items():
        order = np.argsort(dists)
        r = np.empty(n_db, dtype=int)
        r[order] = np.arange(1, n_db + 1)
        ranks[method] = r

    # Ensemble scoring
    if ensemble == "mean_rank":
        scores = np.mean([ranks[m] for m in methods], axis=0)
    elif ensemble == "borda":
        # Borda: n - rank (higher = better), then negate for sorting
        borda_scores = np.sum([n_db - ranks[m] for m in methods], axis=0)
        scores = -borda_scores.astype(float)  # Negate so lower = better
    elif ensemble == "weighted":
        w = weights or {}
        scores = np.zeros(n_db)
        for m in methods:
            w_m = w.get(m, 1.0)
            scores += w_m * ranks[m]
    else:
        scores = np.mean([ranks[m] for m in methods], axis=0)

    # Sort by score (lower = better)
    top_indices = np.argsort(scores)[:top_k]

    results = []
    for rank_pos, idx in enumerate(top_indices):
        results.append({
            "rank": rank_pos + 1,
            "historical_idx": int(idx),
            "ensemble_score": float(scores[idx]),
            "distances_per_method": {m: float(distances[m][idx]) for m in methods},
            "ranks_per_method": {m: int(ranks[m][idx]) for m in methods},
        })

    return results


def regime_transition_analysis(
    regime_labels: pd.Series,
    *,
    data_per_regime: pd.Series | None = None,
    include_duration_stats: bool = True,
    min_duration: int = 1,
) -> dict:
    """Regime transition analysis with holding period and half-life.

    Calls:
        oprim.regime_transition_matrix, oprim.regime_filter_data, oprim.distribution_summary

    Args:
        regime_labels: Series of regime labels.
        data_per_regime: Optional data series for per-regime statistics.
        include_duration_stats: Whether to include duration distribution.
        min_duration: Minimum duration to count as a regime stay.

    Returns:
        Dict with transition_matrix, stationary_distribution, holding periods, half-lives.

    Raises:
        ValueError: If regime_labels has fewer than 2 unique regimes.
    """
    if not isinstance(regime_labels, pd.Series):
        regime_labels = pd.Series(regime_labels)

    # Remove NaN
    valid_labels = regime_labels.dropna()
    if len(valid_labels) < 2:
        raise ValueError("regime_labels must have at least 2 observations")

    unique_regimes = valid_labels.unique()
    if len(unique_regimes) < 2:
        raise ValueError("regime_labels must have at least 2 unique regimes")

    # Use oprim.regime_transition_matrix
    tm_result = oprim.regime_transition_matrix(
        valid_labels, include_duration=include_duration_stats
    )

    transition_matrix = tm_result["transition_matrix"]
    stationary_dist = tm_result["stationary_distribution"]
    n_transitions = tm_result["n_transitions"]
    duration_dist = tm_result.get("duration_distribution") if include_duration_stats else None

    # Compute expected holding period and half-life
    expected_holding_period = {}
    half_life = {}

    for regime in unique_regimes:
        if regime in transition_matrix.index:
            p_stay = transition_matrix.loc[regime, regime]
            if p_stay >= 1.0:
                expected_holding_period[regime] = np.inf
                half_life[regime] = np.inf
            elif p_stay <= 0.0:
                expected_holding_period[regime] = 1.0
                half_life[regime] = 0.0
            else:
                expected_holding_period[regime] = 1.0 / (1.0 - p_stay)
                half_life[regime] = np.log(0.5) / np.log(p_stay)

    # Per-regime data summary
    data_summary = None
    if data_per_regime is not None:
        if not isinstance(data_per_regime, pd.Series):
            data_per_regime = pd.Series(data_per_regime)
        data_df = pd.DataFrame({"value": data_per_regime})
        data_summary = {}
        for regime in unique_regimes:
            filtered = oprim.regime_filter_data(data_df, regime_labels, regime)
            if len(filtered) > 0:
                data_summary[regime] = oprim.distribution_summary(filtered["value"].values)

    return {
        "transition_matrix": transition_matrix,
        "stationary_distribution": stationary_dist,
        "n_transitions": n_transitions,
        "duration_distribution": duration_dist,
        "expected_holding_period": expected_holding_period,
        "half_life": half_life,
        "data_summary_per_regime": data_summary,
    }
