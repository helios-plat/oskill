"""Stateless coding-intelligence evidence composition."""

from __future__ import annotations

from typing import Any


def analyze_symbol_impact(
    *,
    changed_symbols: list[dict[str, Any]] | None = None,
    ast_evidence: dict[str, Any] | None = None,
    lsp_evidence: dict[str, Any] | None = None,
    dependency_evidence: dict[str, Any] | None = None,
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    """Combine syntactic AST and semantic LSP evidence without hiding unknowns."""
    ast_evidence = ast_evidence or {}
    lsp_evidence = lsp_evidence or {}
    dependency_evidence = dependency_evidence or {}
    symbols = list(changed_symbols or ast_evidence.get("symbols", []))
    direct = list(lsp_evidence.get("references", lsp_evidence.get("direct_impacts", [])))
    transitive = list(dependency_evidence.get("transitive", dependency_evidence.get("reached", [])))
    unresolved = list(lsp_evidence.get("unresolved", [])) + list(
        dependency_evidence.get("unresolved", [])
    )
    files = set(changed_files or [])
    for item in direct + transitive:
        if isinstance(item, dict) and item.get("file"):
            files.add(item["file"])
        elif isinstance(item, str) and "." in item:
            files.add(item)
    confidence = "high" if direct and not unresolved else "medium" if symbols else "low"
    return {
        "changed_symbols": symbols,
        "direct_impacts": direct,
        "transitive_impacts": transitive,
        "affected_files": sorted(files),
        "unresolved_symbols": unresolved,
        "confidence": confidence,
        "evidence": {"ast": ast_evidence, "lsp": lsp_evidence, "dependency": dependency_evidence},
    }


def analyze_diff_risk(
    *,
    diff: dict[str, Any],
    symbol_impact: dict[str, Any],
    diagnostics: list[dict[str, Any]] | None = None,
    test_impact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score traceable change risk; never make a merge/release decision."""
    diagnostics = diagnostics or []
    test_impact = test_impact or {}
    factors: list[dict[str, Any]] = []
    score = 0.0
    lines = int(diff.get("changed_lines", diff.get("insertions", 0)) + diff.get("deletions", 0))
    if lines > 500:
        score += 0.35
        factors.append({"name": "large_diff", "value": lines})
    elif lines > 100:
        score += 0.15
        factors.append({"name": "diff_size", "value": lines})
    if symbol_impact.get("unresolved_symbols"):
        score += 0.25
        factors.append({"name": "unresolved_symbols", "value": symbol_impact["unresolved_symbols"]})
    if len(symbol_impact.get("transitive_impacts", [])) > 10:
        score += 0.2
        factors.append(
            {"name": "dependency_fanout", "value": len(symbol_impact["transitive_impacts"])}
        )
    if diagnostics:
        score += 0.3
        factors.append({"name": "diagnostics", "value": diagnostics})
    files = list(diff.get("files", []))
    sensitive = [
        path
        for path in files
        if any(mark in path.lower() for mark in ("auth", "secret", "permission", "schema"))
    ]
    if sensitive:
        score += 0.25
        factors.append({"name": "sensitive_area", "value": sensitive})
    score = min(1.0, score)
    level = (
        "critical"
        if score >= 0.85 and diagnostics
        else "high"
        if score >= 0.6
        else "medium"
        if score >= 0.25
        else "low"
    )
    return {
        "risk_level": level,
        "risk_score": score,
        "factors": factors,
        "affected_areas": files,
        "unknowns": symbol_impact.get("unresolved_symbols", []),
        "evidence": {
            "diff": diff,
            "symbol_impact": symbol_impact,
            "diagnostics": diagnostics,
            "test_impact": test_impact,
        },
    }


def select_relevant_tests(
    *,
    changed_files: list[str],
    changed_symbols: list[dict[str, Any]] | list[str],
    symbol_impact: dict[str, Any],
    test_inventory: list[dict[str, Any]],
    dependency_mappings: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Select test names only; this function never executes tests."""
    dependency_mappings = dependency_mappings or {}
    selected: list[str] = []
    required: list[str] = []
    optional: list[str] = []
    rationale: dict[str, list[str]] = {}
    changed = set(changed_files)
    changed_names = {
        item if isinstance(item, str) else item.get("name") for item in changed_symbols
    }
    for test in test_inventory:
        name = str(test.get("name", test.get("path", "")))
        covered = set(test.get("files", [])) & changed
        covered_symbols = set(test.get("symbols", [])) & changed_names
        mapped = set(dependency_mappings.get(name, [])) & changed
        if covered or covered_symbols or mapped:
            selected.append(name)
            rationale[name] = ["file", "symbol", "dependency"][
                : bool(covered) + bool(covered_symbols) + bool(mapped)
            ]
            (required if test.get("required") else optional).append(name)
    unmapped = list(symbol_impact.get("unresolved_symbols", []))
    return {
        "selected_tests": selected,
        "required_tests": required,
        "optional_tests": optional,
        "unmapped_changes": unmapped,
        "rationale": rationale,
    }


__all__ = ["analyze_symbol_impact", "analyze_diff_risk", "select_relevant_tests"]
