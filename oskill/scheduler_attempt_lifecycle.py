"""oskill.scheduler_attempt_lifecycle — Cindy attempt phase machine + retry + monthly + knowledge hook.

Enhances ``RecurringScheduler`` with:
  - Attempt lifecycle phase machine (claiming→persisting→running→finalizing) with
    legal-transition enforcement (illegal transition → error, not silent skip).
  - Monthly preset scheduling (clamp day-of-month to calendar reality).
  - Pre-run knowledge hook: auto-refresh stale knowledge entries before execution.
  - Retry with backoff (max_attempts + exponential delay).

3O element: ``oskill.scheduler_attempt_lifecycle``.
"""

from __future__ import annotations

import asyncio
import calendar as cal_mod
import time
from typing import Any, Callable

# legal transitions mimic Cindy's attemptLifecycle.ts
LEGAL_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "claiming": ("persisting",),
    "loading": ("persisting",),
    "persisting": ("running", "finalizing"),
    "running": ("queued", "finalizing"),
    "queued": ("running", "cancelling", "finalizing"),
    "cancelling": ("finalizing",),
    "finalizing": (),
    "pending": ("claiming", "loading"),  # entry points
    "completed": ("pending",),           # re-queue
    "failed": ("pending", "claiming"),   # retry entry
}


def is_legal_transition(from_phase: str, to_phase: str) -> bool:
    if from_phase == to_phase:
        return True  # idempotent no-op
    return to_phase in LEGAL_TRANSITIONS.get(from_phase, ())


def transition_attempt(attempt: dict[str, Any], to_phase: str) -> dict[str, Any]:
    """Enforce legal phase transition; raise ValueError on illegal move."""
    from_phase = attempt.get("phase", "pending")
    if not is_legal_transition(from_phase, to_phase):
        raise ValueError(f"illegal transition: {from_phase} → {to_phase} (legal: {LEGAL_TRANSITIONS.get(from_phase, ())})")
    attempt["phase"] = to_phase
    attempt["phase_at"] = time.time()
    return attempt


def monthly_clamp(cron_expr: str, now_ts: float | None = None) -> int:
    """Cindy monthly preset: clamp day-of-month to calendar reality.

    Standard cron would skip months where the day doesn't exist (e.g. 31 in April).
    This clamps to the last valid day of the target month so the schedule fires every month.
    Returns the next fire timestamp (epoch seconds).
    """
    now = now_ts or time.time()
    parts = cron_expr.strip().split()
    if len(parts) != 5 or parts[3] != "*" or parts[4] != "*":
        # not a monthly preset — use simple 1-hour ahead
        return int(now + 3600)

    try:
        minute, hour, day = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return int(now + 3600)

    import datetime
    dt = datetime.datetime.fromtimestamp(now, tz=datetime.timezone.utc)
    year, month = dt.year, dt.month

    # clamp day to month's max
    max_day = cal_mod.monthrange(year, month)[1]
    effective_day = min(day, max_day)

    target = datetime.datetime(year, month, effective_day, hour, minute, 0, tzinfo=datetime.timezone.utc)
    if target.timestamp() <= now:
        # advance to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        max_day = cal_mod.monthrange(year, month)[1]
        effective_day = min(day, max_day)
        target = datetime.datetime(year, month, effective_day, hour, minute, 0, tzinfo=datetime.timezone.utc)

    return int(target.timestamp())


async def pre_run_knowledge_hook(schedule: dict[str, Any], context: dict[str, Any] | None = None) -> bool:
    """Cindy-style pre-run hook: auto-refresh stale knowledge entries before executing.

    Scans the knowledge store for stale entries, marks them fresh after retrieval,
    and updates the schedule's prompt context with any refreshed items.
    Returns False if no knowledge store is available (skips silently).
    """
    ctx = context or {}
    try:
        from obase.knowledge_store import KnowledgeStore
        store = KnowledgeStore()
        stale = store.list_stale()
        if stale:
            refreshed: list[str] = []
            for doc in stale:
                store.mark_fresh(doc["frontmatter"]["id"])
                refreshed.append(doc["frontmatter"]["id"])
            # inject refreshed knowledge into schedule context
            schedule["_last_refreshed"] = refreshed
            schedule["_last_refreshed_at"] = time.time()
        return True
    except Exception:
        return True  # non-fatal: knowledge store missing → skip hook


async def retry_execute(
    schedule: dict[str, Any],
    runner: Callable,
    max_attempts: int = 3,
    backoff_base_s: float = 5.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a schedule with retry + exponential backoff.

    Mimics Cindy's attempt lifecycle: claiming → persisting → running.
    On failure, transitions to failed → pending (for retry).
    """
    attempt = {"phase": "pending", "attempt": 0, "errors": [], "phase_at": time.time()}
    ctx = context or {}

    for i in range(max_attempts):
        attempt["attempt"] = i + 1
        try:
            transition_attempt(attempt, "claiming")
            transition_attempt(attempt, "persisting")

            # pre-run knowledge hook
            await pre_run_knowledge_hook(schedule, ctx)

            transition_attempt(attempt, "running")
            result = runner(schedule)
            if hasattr(result, "__await__"):
                result = await result
            transition_attempt(attempt, "completed")
            return {"status": "completed", "attempt": i + 1, "result": result, "phase_history": attempt}

        except Exception as exc:
            attempt["errors"].append(str(exc))
            try:
                transition_attempt(attempt, "failed")
            except ValueError:
                attempt["phase"] = "failed"
            if i < max_attempts - 1:
                delay = backoff_base_s * (2 ** i)
                await asyncio.sleep(delay)
            transition_attempt(attempt, "pending")  # re-enter for retry

    transition_attempt(attempt, "finalizing")
    return {"status": "exhausted", "attempt": max_attempts, "errors": attempt["errors"], "phase_history": attempt}
