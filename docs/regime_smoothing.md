# oskill.regime_smoothing

## Purpose

Smooth raw regime classifications to prevent flapping (rapid back-and-forth switches).
Required by Domain 01 of any application using regime-based decisions.

## API

```python
def regime_smoothing(
    raw_state_history: list[RawRegimeState],
    smoothing_config: SmoothingConfig,
    current_smoothed_state: str | None = None,
) -> SmoothingResult:
```

### Parameters

- `raw_state_history` — Recent raw regime states, chronological order.
- `smoothing_config` — Per-regime minimum duration configuration.
- `current_smoothed_state` — Current confirmed state. `None` for first computation.

### Returns

`SmoothingResult` with:
- `smoothed_state` — Confirmed regime state after smoothing.
- `state_changed` — Whether a switch was confirmed this call.
- `change_confirmed_at` — Datetime of confirmed switch (or None).
- `days_in_current_state` — Consecutive days in smoothed_state.
- `transitional_state` — Pending state not yet confirmed (or None).
- `transitional_days` — Days in transitional state.

## Algorithm

1. First call (`current_smoothed_state=None`): return latest raw state immediately.
2. Same state continuation: no switch, increment `days_in_current_state`.
3. Different latest state: check transitional days.
   - If latest is a stress state and `transitional_days >= stress_min_days` → confirm switch.
   - If latest is a normal state and `transitional_days >= normal_min_days` → confirm switch.
   - Otherwise: maintain `current_smoothed_state`, record as transitional.

## Configuration

`SmoothingConfig` fields:
- `stress_states` — List of state names requiring fast confirmation.
- `stress_min_days` — Minimum consecutive days to confirm a stress state switch.
- `normal_min_days` — Minimum consecutive days to confirm a normal state switch.

## Example

```python
from oskill import regime_smoothing
from oskill.types import RawRegimeState, SmoothingConfig

config = SmoothingConfig(
    stress_states=["冰点", "恐慌", "狂热"],
    stress_min_days=1,
    normal_min_days=2,
)

result = regime_smoothing(history, config, current_smoothed_state="积极")
```

## Edge Cases

- Empty history → `ValueError`
- Single-day history + `None` current → returns that state immediately
- Oscillating raw states (A→B→A→B) → never confirms switch (transitional resets)
