"""Stateless engineering qualification signals."""

from __future__ import annotations

from typing import Any

from oskill.metric_baseline_compare import metric_baseline_compare


def _evidence_list(evidence: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(evidence, dict):
        return [evidence]
    return [item for item in evidence if isinstance(item, dict)]


def evaluate_contract(
    *,
    contract: dict[str, Any],
    observed: dict[str, Any],
    evidence: list[dict[str, Any]] | dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate declared requirements; unknown required evidence fails closed."""
    records = _evidence_list(evidence)
    policy = policy or {}
    required = list(contract.get("required", contract.get("requirements", [])))
    expectations = contract.get("expect", contract.get("expected", {}))
    satisfied: list[str] = []
    violations: list[str] = []
    unknown: list[str] = []
    for name in required:
        if name not in observed:
            unknown.append(f"missing_observed:{name}")
        elif name not in expectations or observed[name] == expectations[name]:
            satisfied.append(str(name))
        else:
            violations.append(f"mismatch:{name}")
    for name, expected in expectations.items():
        if name not in required:
            if name not in observed:
                unknown.append(f"missing_observed:{name}")
            elif observed[name] == expected:
                satisfied.append(str(name))
            else:
                violations.append(f"mismatch:{name}")
    required_evidence = list(policy.get("required_evidence", contract.get("required_evidence", [])))
    for marker in required_evidence:
        if not any(
            record.get("type") == marker
            or record.get("name") == marker
            or record.get("evidence") == marker
            for record in records
        ):
            unknown.append(f"missing_evidence:{marker}")
    return {
        "passed": not violations and not unknown,
        "violations": violations,
        "satisfied": sorted(set(satisfied)),
        "unknown": sorted(set(unknown)),
        "evidence": {"records": records, "fail_closed": bool(unknown)},
    }


def evaluate_proven_red(
    *,
    claim: dict[str, Any],
    pre_change_evidence: dict[str, Any] | list[dict[str, Any]],
    failure_contract: dict[str, Any],
) -> dict[str, Any]:
    """Prove that the claimed defect reproduced before the change."""
    records = _evidence_list(pre_change_evidence)
    violations: list[str] = []
    if not records:
        violations.append("missing_pre_change_evidence")
    if any(
        record.get("environment_failure") or record.get("failure_kind") == "environment"
        for record in records
    ):
        violations.append("environment_failure_not_claimed_defect")
    claim_id = claim.get("id", claim.get("name", claim.get("defect")))
    required_id = failure_contract.get("id", failure_contract.get("claim_id", claim_id))
    matches = [
        record
        for record in records
        if record.get("claim_id", record.get("id", record.get("defect"))) == required_id
    ]
    if not matches:
        violations.append("claim_not_matched")
    expected_fixture = failure_contract.get("fixture", claim.get("fixture"))
    if expected_fixture is not None and any(
        record.get("fixture") != expected_fixture for record in matches
    ):
        violations.append("fixture_mismatch")
    reproduced = any(
        record.get("status") == "failed" or record.get("passed") is False for record in matches
    )
    if not reproduced:
        violations.append("failure_not_reproduced")
    sufficient = bool(matches) and not any(
        item in violations
        for item in ("missing_pre_change_evidence", "claim_not_matched", "fixture_mismatch")
    )
    return {
        "proven_red": sufficient and reproduced and not violations,
        "failure_reproduced": reproduced,
        "evidence_sufficient": sufficient,
        "violations": sorted(set(violations)),
        "evidence": {"pre_change": records, "claim_id": claim_id, "fail_closed": bool(violations)},
    }


def evaluate_ratchet(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """Apply non-regression rules through metric_baseline_compare."""
    base = baseline.get("metrics", baseline)
    current = candidate.get("metrics", candidate)
    directions = rules.get("directions", {})
    names = list(rules.get("required", set(base) | set(current)))
    unknown: list[str] = []
    regressions: list[str] = []
    improvements: list[str] = []
    unchanged: list[str] = []
    for name in names:
        if name not in base or name not in current:
            unknown.append(str(name))
            continue
        threshold = rules.get("tolerances", {}).get(name, rules.get("tolerance", 0.2))
        result = metric_baseline_compare(
            current_metrics={name: current[name]},
            baseline_metrics={name: base[name]},
            degradation_threshold=float(threshold),
            metric_directions={name: directions.get(name, "lower_is_better")},
        )
        delta = (
            result.degraded_metrics[0] if result.degraded_metrics else result.improved_metrics[0]
        )
        if delta.degraded:
            regressions.append(str(name))
        elif current[name] == base[name]:
            unchanged.append(str(name))
        else:
            improvements.append(str(name))
    return {
        "passed": not regressions and not unknown,
        "regressions": regressions,
        "improvements": improvements,
        "unchanged": unchanged,
        "unknown": unknown,
    }


__all__ = ["evaluate_contract", "evaluate_proven_red", "evaluate_ratchet"]
