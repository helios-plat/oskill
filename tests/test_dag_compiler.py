"""compile_spec_to_dag + validate + ready ids."""

from __future__ import annotations

from oskill.dag_compiler import (
    compile_spec_to_dag,
    pick_ready_task_ids,
    validate_taskgraph_dag,
)
from oskill.constitutional_violation import detect_constitution_violation

TASKS = """
# Tasks
- [ ] T1 Setup repo
  Acceptance: repo exists
- [ ] T2 Add fetch client
  Depends: T1
  Acceptance: uses fetch
  - [ ] T2.1 Write types
"""


def test_compile_ids_and_deps() -> None:
    nodes = compile_spec_to_dag(TASKS)
    by_id = {n.id: n for n in nodes}
    assert "T1" in by_id and "T2" in by_id
    assert by_id["T2"].depends_on == ["T1"]
    assert "T2.1" in by_id
    assert "T2" in by_id["T2.1"].depends_on
    assert validate_taskgraph_dag(nodes) == []


def test_cycle_detected() -> None:
    nodes = compile_spec_to_dag(
        "- [ ] T1 A\n  Depends: T2\n- [ ] T2 B\n  Depends: T1\n"
    )
    errors = validate_taskgraph_dag(nodes)
    assert any("cycle" in e for e in errors)


def test_ready_after_first() -> None:
    nodes = compile_spec_to_dag(TASKS)
    ready = pick_ready_task_ids(nodes, completed_ids=set())
    assert ready == ["T1"]
    ready2 = pick_ready_task_ids(nodes, completed_ids={"T1"})
    assert "T2" in ready2


def test_constitution_bans_axios() -> None:
    hit = detect_constitution_violation(
        "ran npm i axios",
        constitution_rules=["Do not use axios", "Must use fetch"],
    )
    assert hit is not None
    assert "axios" in hit


def test_constitution_ok_with_fetch() -> None:
    assert (
        detect_constitution_violation(
            "used window.fetch",
            constitution_rules=["Do not use axios", "Must use fetch"],
        )
        is None
    )
