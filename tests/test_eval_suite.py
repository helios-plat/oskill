"""Tests for eval_suite (ai-agent-book 第6章 3O 内化)。"""

from __future__ import annotations

from oskill.eval_suite import (
    EvalCase,
    cohens_d,
    compare_runs,
    paired_t_test,
    run_suite,
    wilcoxon_signed_rank,
)


def test_run_suite_summary():
    cases = [EvalCase("c1", "a"), EvalCase("c2", "b"), EvalCase("c3", "c")]
    run = run_suite(cases, lambda c: 1.0 if c.id == "c1" else 0.5)
    summary = run.summary()
    assert summary["mean"] == 2 / 3
    assert summary["n"] == 3
    assert summary["max"] == 1.0


def test_run_suite_error_isolated():
    def bad_scorer(case):
        if case.id == "bad":
            raise ValueError("boom")
        return 0.9

    run = run_suite([EvalCase("ok", "x"), EvalCase("bad", "y")], bad_scorer)
    assert run.scores["bad"] == 0.0
    assert "error" in run.details["bad"]


def test_paired_t_test_significant():
    # 明显差异 → significant
    a = [0.5, 0.6, 0.5, 0.55, 0.6]
    b = [0.8, 0.85, 0.78, 0.82, 0.8]
    result = paired_t_test(a, b)
    assert result["mean_diff"] > 0
    assert result["significant_05"] is True
    assert result["df"] == 4


def test_paired_t_test_not_significant():
    a = [0.5, 0.5, 0.5, 0.5]
    b = [0.51, 0.49, 0.52, 0.48]
    result = paired_t_test(a, b)
    assert result["significant_05"] is False


def test_paired_t_test_short():
    result = paired_t_test([0.5], [0.8])
    assert result["p_value"] == 1.0  # n < 2 → 无法判显著


def test_wilcoxon_significant():
    a = [0.4, 0.5, 0.4, 0.6, 0.45]
    b = [0.9, 0.8, 0.85, 0.7, 0.8]
    result = wilcoxon_signed_rank(a, b)
    assert result["significant_05"] is True
    assert result["n"] >= 4


def test_wilcoxon_short():
    result = wilcoxon_signed_rank([0.5], [0.5])
    assert result["significant_05"] is False


def test_cohens_d():
    d = cohens_d([0.5, 0.5, 0.5], [0.7, 0.7, 0.7])
    assert d > 1.0  # 一致差异 → 大效应量


def test_compare_runs_candidate_wins():
    baseline = run_suite([EvalCase(f"c{i}", "x") for i in range(6)],
                         lambda c: 0.5)
    candidate = run_suite([EvalCase(f"c{i}", "x") for i in range(6)],
                          lambda c: 0.85)
    report = compare_runs(baseline, candidate)
    assert report.candidate_wins is True
    assert report.effect_size > 0
    assert report.to_dict()["candidate"]["mean"] == 0.85


def test_compare_runs_uses_common_cases():
    baseline = run_suite([EvalCase("c1", "x"), EvalCase("c2", "x")], lambda c: 0.5)
    candidate = run_suite([EvalCase("c1", "x"), EvalCase("c9", "x")], lambda c: 0.9)
    report = compare_runs(baseline, candidate)
    # 只有 c1 配对
    assert report.t_test["df"] == 0
    assert report.candidate_wins is False
