# oskill.screening.candidate_pool_builder

## Purpose

Build a ranked candidate pool from a universe of candidates by applying filter rules, scoring, and top-N selection.

## API

```python
def candidate_pool_builder(
    *,
    universe: list[dict[str, Any]],
    scoring_fn: Callable[[dict[str, Any]], float],
    filter_rules: list[Callable[[dict[str, Any]], bool]] | None = None,
    top_n: int = 30,
    min_score: float = 0.0,
    regime_aware: bool = False,
    regime: str | None = None,
) -> dict[str, Any]:
```

## v3.7.0 — regime_aware Extension

New optional parameters:
- `regime_aware: bool = False`
- `regime: str | None = None`

When `regime_aware=True`, the `regime` value is injected into each candidate dict as `_regime` before passing to `scoring_fn`. This allows the scoring function to implement regime-conditional logic.

The function itself does not implement regime-specific scoring logic — it only handles data injection. Application-layer `scoring_fn` decides how to use regime (e.g., by calling `oskill.regime_conditional_score_weighted`).

### Metadata

The return dict now includes a `metadata` field:
```python
{
    "candidates": [...],
    "stats": {...},
    "metadata": {"regime_aware": True, "regime": "积极"},
}
```

### Backward Compatibility

Not passing `regime_aware` parameter results in behavior identical to v3.x (`metadata.regime_aware=False`, `metadata.regime=None`).
