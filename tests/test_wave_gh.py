from oskill.coding_intelligence import (
    analyze_diff_risk,
    analyze_symbol_impact,
    select_relevant_tests,
)
from oskill.engineering_qualification import (
    evaluate_contract,
    evaluate_proven_red,
    evaluate_ratchet,
)


def test_contract_unknown_and_violation_fail_closed():
    result = evaluate_contract(
        contract={"required": ["status"], "expect": {"status": "ok"}}, observed={}, evidence=[]
    )
    assert result["passed"] is False
    assert result["unknown"]
    result = evaluate_contract(
        contract={"expect": {"status": "ok"}}, observed={"status": "bad"}, evidence=[]
    )
    assert result["violations"]


def test_proven_red_requires_matching_pre_fix_failure():
    good = evaluate_proven_red(
        claim={"id": "bug-1", "fixture": "same"},
        pre_change_evidence={"claim_id": "bug-1", "fixture": "same", "status": "failed"},
        failure_contract={"id": "bug-1", "fixture": "same"},
    )
    assert good["proven_red"] is True
    env = evaluate_proven_red(
        claim={"id": "bug-1"},
        pre_change_evidence={
            "claim_id": "bug-1",
            "status": "failed",
            "failure_kind": "environment",
        },
        failure_contract={"id": "bug-1"},
    )
    assert env["proven_red"] is False
    missing = evaluate_proven_red(
        claim={"id": "bug-1"}, pre_change_evidence=[], failure_contract={"id": "bug-1"}
    )
    assert missing["evidence_sufficient"] is False


def test_ratchet_handles_equal_tolerance_and_missing():
    assert evaluate_ratchet(
        baseline={"metrics": {"x": 1}},
        candidate={"metrics": {"x": 1}},
        rules={"directions": {"x": "higher_is_better"}},
    )["passed"]
    assert evaluate_ratchet(
        baseline={"metrics": {"x": 1}},
        candidate={"metrics": {"x": 0.95}},
        rules={"directions": {"x": "higher_is_better"}, "tolerance": 0.1},
    )["passed"]
    missing = evaluate_ratchet(
        baseline={"metrics": {"x": 1}}, candidate={"metrics": {}}, rules={"required": ["x"]}
    )
    assert missing["passed"] is False and missing["unknown"] == ["x"]


def test_coding_intelligence_preserves_unresolved_and_unmapped():
    impact = analyze_symbol_impact(
        changed_symbols=[{"name": "f"}],
        ast_evidence={"symbols": [{"name": "f"}]},
        lsp_evidence={"references": [{"file": "b.py"}], "unresolved": ["dynamic"]},
        dependency_evidence={"transitive": ["c.py"]},
        changed_files=["a.py"],
    )
    assert impact["unresolved_symbols"] == ["dynamic"]
    risk = analyze_diff_risk(
        diff={"changed_lines": 600, "files": ["auth.py"]}, symbol_impact=impact
    )
    assert risk["risk_level"] in {"medium", "high", "critical"}
    selected = select_relevant_tests(
        changed_files=["a.py"], changed_symbols=["f"], symbol_impact=impact, test_inventory=[]
    )
    assert selected["selected_tests"] == []
    assert selected["unmapped_changes"] == ["dynamic"]
