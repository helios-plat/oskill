"""oskill.capability_intersection — fail-closed capability composition."""
from __future__ import annotations

from collections.abc import Iterable

from oprim._intersect_capabilities import intersect_capabilities


def capability_intersection(
    requested: Iterable[str],
    caller: Iterable[str],
    worker: Iterable[str],
    workspace: Iterable[str],
    policy: Iterable[str],
) -> frozenset[str]:
    """Compute effective capabilities across all execution constraints."""
    return intersect_capabilities(requested, caller, worker, workspace, policy)
