# SELF_CHECK — oskill B10: Tide v4 step2 oskills (12 elements)

**Date**: 2026-05-30
**Commit**: 7f1eb0d
**Version**: 3.7.0 → 3.8.0
**Files added**:
- `oskill/macro_surprise_compute.py`
- `oskill/macro_cycle_engine_v2.py`
- `oskill/policy_sector_attribution.py`
- `oskill/seat_winrate_aggregator.py`
- `oskill/unknown_seats_audit_loop.py`
- `oskill/sector_strength_aggregator.py`
- `oskill/candidate_universe_builder_v3.py`
- `oskill/similar_context_injector.py`
- `oskill/industry_valuation_percentile.py`
- `oskill/discipline_vs_violation_winrate_compute.py`
- `oskill/system_history_aggregator.py`
- `oskill/equity_curve_3seg_compute.py`
- `tests/tide_step2/test_b10_oskills.py`

---

## Test count

| File | Tests |
|------|-------|
| test_b10_oskills.py | 100 |
| **Total new** | **100** |

---

## Gate results

```
100 passed in 2.48s
```

### mypy --strict

```
Success: no issues found in 12 source files
```

### ruff

```
All checks passed!
```

---

## Key fixes applied during session

1. **`apply_screen_filter` bridge** — `oprim.apply_screen_filter` expects `pd.DataFrame`, but
   `candidate_universe_builder_v3` was passing `list[dict]`. Fixed by `pd.DataFrame(pool_candidates)`
   before call; reconstruct final candidates by matching `symbol` from `screen_result.passed`.

2. **`ScreenRule` field names** — test used `operator`/`value` (wrong) → `op`/`threshold`/`reason`.

3. **`oprim.__all__` gap** — B1-B3/B7-B9 imports were in `__init__.py` but NOT in `__all__`, causing
   mypy `[attr-defined]` errors on `oprim.func()` calls. Added all 68 symbols to `__all__`
   (commit `033ed37` on oprim).

4. **`macro_cycle_engine_v2`** — `_last_n`/`_trend` needed explicit type annotations; `phase` variable
   needed `cast(_PHASES, phase_str)` to satisfy Literal type; unused `signals` var removed.

5. **`dict` → `dict[str, object]`** — strict mypy rejects bare `dict` in type annotations.

6. **pandas `# type: ignore[import-untyped]`** — `pandas-stubs` not installed in environment;
   added inline ignore to 9 files.
