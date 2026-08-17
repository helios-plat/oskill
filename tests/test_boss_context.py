"""assemble_boss_context + graph-dict DAG validator."""

from __future__ import annotations

from obase.workspace_snapshot import WorkspaceSnapshot

from oskill.context_assembler import assemble_boss_context, assemble_intent_context
from oskill.dag_validator import validate_taskgraph_dag
from oskill.leaf_contract import validate_intent_brief, validate_leaf_contract


def test_assemble_intent_is_triage_not_plan() -> None:
    snap = WorkspaceSnapshot(git_diff="", ast_summary={}, active_files=["a.py"])
    text = assemble_intent_context(snap, "fix login")
    assert "plan | ask | refuse" in text
    assert "Goal: fix login" in text


def test_assemble_uses_brief_as_authority() -> None:
    snap = WorkspaceSnapshot(
        git_diff="diff --git a/a.py b/a.py\n",
        ast_summary={},
        active_files=["a.py"],
    )
    text = assemble_boss_context(
        snap,
        "fix it",
        brief={
            "interpretation": "expire session in auth.py",
            "in_scope_files": ["auth.py"],
            "out_of_scope_files": ["ui.tsx"],
            "acceptance_draft": ["git diff touches auth.py"],
        },
    )
    assert "expire session in auth.py" in text
    assert "auth.py" in text
    assert "authoritative" in text


def test_intent_brief_plan_requires_acceptance() -> None:
    errors = validate_intent_brief(
        {"action": "plan", "interpretation": "do x", "acceptance_draft": []}
    )
    assert any("acceptance_draft" in e for e in errors)


def test_leaf_contract_requires_files_logic_forbidden() -> None:
    errors = validate_leaf_contract(
        {
            "tasks": [
                {
                    "id": "T1",
                    "instruction": "edit a.py",
                    "acceptance": ["foo"],
                    "assignee": "hicode",
                }
            ]
        }
    )
    assert any("missing files" in e for e in errors)
    assert any("missing logic" in e for e in errors)
    assert any("missing forbidden" in e for e in errors)


def test_assemble_includes_goal_and_diff() -> None:
    snap = WorkspaceSnapshot(
        git_diff="diff --git a/a.py b/a.py\n",
        ast_summary={"a.py": {"classes": ["A"], "functions": ["f"]}},
        active_files=["a.py"],
    )
    text = assemble_boss_context(snap, "fix login")
    assert "Goal: fix login" in text
    assert "a.py" in text
    assert "classes=A" in text


def test_validator_rejects_cycle_and_empty_acceptance() -> None:
    errors = validate_taskgraph_dag(
        {
            "tasks": [
                {
                    "id": "T1",
                    "title": "A",
                    "instruction": "A",
                    "acceptance": [],
                    "depends_on": ["T2"],
                },
                {
                    "id": "T2",
                    "title": "B",
                    "instruction": "B",
                    "acceptance": ["done"],
                    "depends_on": ["T1"],
                },
            ]
        }
    )
    assert any("empty acceptance" in e for e in errors)
    assert any("cycle" in e for e in errors)


def test_validator_ok() -> None:
    errors = validate_taskgraph_dag(
        {
            "tasks": [
                {
                    "id": "T1",
                    "title": "A",
                    "instruction": "edit a.py: add f; do not touch b.py",
                    "acceptance": ["git diff contains def f"],
                    "depends_on": [],
                }
            ]
        }
    )
    assert errors == []
