"""oskill.context_lineage — reusable lineage propagation algorithm."""
from __future__ import annotations

from oprim._execution_lineage import ExecutionLineage


def context_lineage(
    root_run_id: str,
    *,
    execution_id: str | None = None,
    parent_execution_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    controller_generation: int = 0,
) -> ExecutionLineage:
    """Construct a validated immutable execution lineage."""
    return ExecutionLineage(
        root_run_id=root_run_id,
        parent_execution_id=parent_execution_id,
        execution_id=execution_id,
        task_id=task_id,
        attempt_id=attempt_id,
        controller_generation=controller_generation,
    )
