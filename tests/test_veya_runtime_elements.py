from oprim._controller_generation import controller_generation_id, next_controller_generation
from oprim._execution_lineage import ExecutionLineage
from oprim._intersect_capabilities import intersect_capabilities
from oskill._capability_intersection import capability_intersection
from oskill._context_lineage import context_lineage
from oskill._controller_generation import ControllerGeneration


def test_capability_intersection_is_fail_closed():
    assert capability_intersection(
        {"read", "write"},
        {"read", "write"},
        {"read"},
        {"read", "write"},
        {"read", "write"},
    ) == frozenset({"read"})
    assert capability_intersection({"write"}, {"read"}, {"write"}, {"write"}, {"write"}) == frozenset()


def test_primitive_rejects_malformed_capability():
    try:
        intersect_capabilities({"read "}, {"read"})
    except ValueError:
        pass
    else:
        raise AssertionError("malformed capability must fail closed")


def test_lineage_is_immutable_and_preserves_parent():
    root = context_lineage("goal-1", execution_id="exec-1", task_id="task-1")
    child = root.child(execution_id="exec-2", task_id="task-2", attempt_id="attempt-1")
    assert root.execution_id == "exec-1"
    assert child.parent_execution_id == "exec-1"
    assert child.root_run_id == "goal-1"


def test_controller_generation_is_monotonic_and_stable():
    assert next_controller_generation(None) == 1
    assert next_controller_generation(1) == 2
    assert controller_generation_id("goal-1", 1) == controller_generation_id("goal-1", 1)
    generation = ControllerGeneration.create("goal-1")
    assert generation.generation == 1
    assert generation.generation_id.startswith("cg_")
