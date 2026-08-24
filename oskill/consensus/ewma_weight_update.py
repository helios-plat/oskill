"""EWMA online weight learning for signal engines.

Extraction source: helixa services/prob-engine/src/weight_learner.py. Pure:
takes a prior accuracy + realized win/loss results and returns the updated
accuracy and dynamic weight; the caller handles trade-matching and persistence.
"""

from __future__ import annotations


def ewma_weight_update(
    prior_accuracy: float,
    results: list[float],
    *,
    base_weight: float,
    lam: float = 0.95,
    floor_mult: float = 0.5,
    ceil_mult: float = 1.5,
) -> dict:
    """Update an engine's accuracy (EWMA) and derive its dynamic weight.

    For each result ``r`` (1.0 win / 0.0 loss) in chronological order:
    ``acc = lam * acc + (1 - lam) * r``. Then
    ``dynamic_weight = clip(base_weight * (0.5 + acc),
    base_weight*floor_mult, base_weight*ceil_mult)`` — an engine at 50% accuracy
    keeps its base weight, better/worse scales it up/down within ±(ceil/floor).

    Parameters
    ----------
    prior_accuracy : float
        Prior EWMA accuracy in [0, 1] (0.5 if no history).
    results : list[float]
        Ordered win(1.0)/loss(0.0) outcomes since the prior.
    base_weight : float
        The engine's static base weight.
    lam : float
        EWMA decay (0.95 ≈ 20-observation effective window).
    floor_mult, ceil_mult : float
        Hard clamp on dynamic_weight as multiples of base_weight.

    Returns
    -------
    dict
        ``{"accuracy": float, "dynamic_weight": float, "n_results": int}``.

    Raises
    ------
    ValueError
        If `prior_accuracy` not in [0, 1] or `base_weight` <= 0.
    """
    if not 0.0 <= prior_accuracy <= 1.0:
        raise ValueError(f"prior_accuracy must be in [0,1], got {prior_accuracy}")
    if base_weight <= 0:
        raise ValueError(f"base_weight must be > 0, got {base_weight}")

    acc = prior_accuracy
    for r in results:
        acc = lam * acc + (1.0 - lam) * (1.0 if r > 0 else 0.0)

    dyn = base_weight * (0.5 + acc)
    dyn = max(base_weight * floor_mult, min(base_weight * ceil_mult, dyn))
    return {"accuracy": acc, "dynamic_weight": dyn, "n_results": len(results)}
