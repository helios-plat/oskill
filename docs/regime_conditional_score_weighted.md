# oskill.regime_conditional_score_weighted

## Purpose

Compute a weighted composite score across multiple dimensions, with per-regime weight overrides.
Core building block for regime-aware Fusion Score in any application.

## API

```python
def regime_conditional_score_weighted(
    dim_scores: dict[str, float],
    base_weights: dict[str, float],
    regime_weight_overrides: dict[str, dict[str, float]],
    current_regime: str,
) -> ScoreWeightedResult:
```

### Parameters

- `dim_scores` — Raw score per dimension (0-100 scale).
- `base_weights` — Base weight per dimension (must sum to 1.0).
- `regime_weight_overrides` — Per-regime multiplier dicts.
- `current_regime` — Current regime state name.

### Returns

`ScoreWeightedResult` with:
- `total_score` — Weighted composite score (0-100).
- `dim_contributions` — Per-dimension contribution details.
- `weights_used` — Actual normalized weights applied.
- `regime` — The regime used for this computation.

## Algorithm

1. Compute unnormalized weight = `base_weight × regime_multiplier` for each dim.
2. Normalize: `weights_used = unnormalized / sum(unnormalized)`.
3. For each dim: `contribution = raw_score × weight_used`.
4. `total_score = sum(contributions)`.

## Properties

- `weights_used` always sums to 1.0 (normalization invariant).
- `total_score == sum(contributions)` (math consistency).
- Unknown regime → base weights used unchanged.
- Each dim contribution tagged with `is_boosted` / `is_dampened` for UI display.

## Example

```python
from oskill import regime_conditional_score_weighted

result = regime_conditional_score_weighted(
    dim_scores={"momentum": 92, "volume": 88, ...},
    base_weights={"momentum": 0.15, "volume": 0.10, ...},
    regime_weight_overrides={"积极": {"momentum": 1.3, "volume": 1.2}},
    current_regime="积极",
)
```

## Edge Cases

- Empty `dim_scores` → `ValueError`
- `base_weights` not summing to 1.0 → `ValueError`
- Mismatched keys between `dim_scores` and `base_weights` → `ValueError`
- All multipliers = 0 → `ValueError` (total weight zero)
