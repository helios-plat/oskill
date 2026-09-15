from oskill.context_engineering import compact_context, rank_context_items, select_context_window
from oskill.skill_qualification import compare_skill_runs, detect_skill_regression


def test_context_pipeline_is_deterministic_and_bounded():
    items = [
        {"content": "alpha project", "importance": 2},
        {"content": "unrelated", "importance": 0},
    ]
    ranked = rank_context_items(items=items, query="alpha")
    selected = select_context_window(ranked_items=ranked["ranked_items"], token_budget=10)
    assert selected["selected_items"]
    assert selected["used_tokens"] <= 10
    assert (
        compact_context(items=items, token_budget=10)["selected_items"]
        == selected["selected_items"]
    )


def test_skill_comparison_reuses_metric_authority_and_detects_regression():
    comparison = compare_skill_runs(
        baseline={"metrics": {"accuracy": 0.9}},
        candidate={"metrics": {"accuracy": 0.5}},
        dimensions={"accuracy": {"direction": "higher_is_better"}},
        thresholds={"accuracy": {"degradation_threshold": 0.2}},
    )
    assert comparison["losses"] == ["accuracy"]
    regression = detect_skill_regression(comparison=comparison)
    assert regression["regressed"] is True


def test_skill_comparison_fails_closed_on_missing_metric():
    comparison = compare_skill_runs(
        baseline={"metrics": {"accuracy": 0.9}},
        candidate={"metrics": {}},
        dimensions=["accuracy"],
    )
    assert comparison["evidence"]["fail_closed"] is True
    assert detect_skill_regression(comparison=comparison)["severity"] == "blocked"


def test_skill_comparison_equal_and_small_change_are_not_regressions():
    for value in (1.0, 0.95):
        comparison = compare_skill_runs(
            baseline={"metrics": {"score": 1.0}},
            candidate={"metrics": {"score": value}},
            dimensions={"score": {"direction": "higher_is_better"}},
            thresholds={"score": {"degradation_threshold": 0.1}},
        )
        assert comparison["losses"] == []
        assert detect_skill_regression(comparison=comparison)["regressed"] is False
