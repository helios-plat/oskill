"""oskill.loop_detection — cycle detection on tool-call hashes. Pure, no I/O."""

from __future__ import annotations


def detect_trajectory_loop(hashes: list[str], *, window_size: int = 4) -> bool:
    """True when the tail repeats a period-k cycle (A-A, A-B-A-B, …)."""
    if window_size < 2 or len(hashes) < window_size:
        return False
    n = len(hashes)
    max_period = min(window_size, n // 2)
    for period in range(1, max_period + 1):
        if n < 2 * period:
            continue
        if hashes[-2 * period : -period] == hashes[-period:]:
            return True
    return False
