"""Stateless skill qualification signals.

These functions consume already-produced evidence.  They never execute a
skill, mutate a registry, or decide promotion.
"""

from __future__ import annotations

from typing import Any

from oskill.metric_baseline_compare import metric_baseline_compare


def _metrics(run: dict[str, Any]) -> dict[str, float]:
    values = run.get("metrics", run)
    if not isinstance(values, dict):
        return {}
    return {name: value for name, value in values.items() if isinstance(value, (int, float))}


def _spec(
    dimensions: list[str] | dict[str, Any] | None, thresholds: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    names = dimensions.keys() if isinstance(dimensions, dict) else dimensions
    if names is None:
        names = sorted(set(thresholds))
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        value = dimensions[name] if isinstance(dimensions, dict) else {}
        value = value if isinstance(value, dict) else {"direction": value}
        threshold = thresholds.get(name, {})
        threshold = (
            threshold if isinstance(threshold, dict) else {"degradation_threshold": threshold}
        )
        result[str(name)] = {**threshold, **value}
    return result


def compare_skill_runs(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    dimensions: list[str] | dict[str, Any] | None = None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare two completed run evidence records using the metric authority."""
    thresholds = thresholds or {}
    baseline_metrics = _metrics(baseline)
    candidate_metrics = _metrics(candidate)
    specs = _spec(dimensions, thresholds)
    missing = {
        name: {"baseline": name in baseline_metrics, "candidate": name in candidate_metrics}
        for name in specs
        if name not in baseline_metrics or name not in candidate_metrics
    }
    if missing:
        return {
            "wins": [],
            "losses": [],
            "neutral": [],
            "deltas": {},
            "qualified_dimensions": {},
            "evidence": {"missing_metrics": missing, "fail_closed": True},
        }

    wins: list[str] = []
    losses: list[str] = []
    neutral: list[str] = []
    deltas: dict[str, Any] = {}
    qualified: dict[str, bool] = {}
    for name, config in specs.items():
        direction = config.get("direction", "higher_is_better")
        degradation = float(config.get("degradation_threshold", 0.2))
        critical = float(config.get("critical_threshold", max(0.5, degradation)))
        result = metric_baseline_compare(
            current_metrics={name: candidate_metrics[name]},
            baseline_metrics={name: baseline_metrics[name]},
            degradation_threshold=degradation,
            critical_threshold=critical,
            metric_directions={name: direction},
        )
        delta = (
            result.degraded_metrics[0] if result.degraded_metrics else result.improved_metrics[0]
        )
        deltas[name] = delta.model_dump()
        qualified[name] = not delta.degraded
        baseline_value = baseline_metrics[name]
        candidate_value = candidate_metrics[name]
        improved = (
            candidate_value > baseline_value
            if direction == "higher_is_better"
            else candidate_value < baseline_value
        )
        degraded = delta.degraded
        if degraded:
            losses.append(name)
        elif improved:
            wins.append(name)
        else:
            neutral.append(name)
    return {
        "wins": wins,
        "losses": losses,
        "neutral": neutral,
        "deltas": deltas,
        "qualified_dimensions": qualified,
        "evidence": {"missing_metrics": {}, "fail_closed": False},
    }


def detect_skill_regression(
    *,
    comparison: dict[str, Any],
    regression_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Turn comparison evidence into regression findings only."""
    rules = regression_rules or {}
    evidence = comparison.get("evidence", {})
    if evidence.get("missing_metrics") or evidence.get("ambiguous"):
        return {
            "regressed": True,
            "regressions": [{"type": "insufficient_evidence", "evidence": evidence}],
            "severity": "blocked",
            "evidence": evidence,
        }
    losses = list(comparison.get("losses", []))
    blocked = [name for name in losses if rules.get(name, {}).get("block", True)]
    findings = [{"dimension": name, "reason": "material_degradation"} for name in blocked]
    return {
        "regressed": bool(findings),
        "regressions": findings,
        "severity": "high" if findings else "none",
        "evidence": {"losses": losses, "rules": rules},
    }


__all__ = ["compare_skill_runs", "detect_skill_regression"]
