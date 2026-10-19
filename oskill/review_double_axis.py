"""oskill.review_double_axis — 双轴代码审查原语 (mattpocock code-review SKILL 3O 内化)。

机制: 对一次 diff 跑两个正交轴, 各自独立不互相污染:
  * Standards 轴 — 是否遵守代码标准 + 通用坏味道基线 (确定性规则扫描);
  * Spec 轴 — 是否忠实实现发起 issue/spec (改动文件是否在 spec 声明范围)。
两轴结论合并为 ReviewReport; LLM 深度判断 (风格/语义) 由调用方注入,
本模块只提供确定性骨架与合并规则。

零 veya 反向依赖: diff 文本与 spec 内容由调用方提供。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── 通用坏味道基线 (确定性扫描) ─────────────────────────────────────

_SMELL_PATTERNS: list[tuple[str, str, str]] = [
    ("debug_leftover", r"\b(?:console\.log|print\(|println!|fmt\.Println|dbg!)\b", "warn"),
    ("todo_fixme", r"\b(?:TODO|FIXME|HACK|XXX)\b", "warn"),
    ("placeholder", r"\b(?:PLACEHOLDER|TBD|WIP)\b", "warn"),
    (
        "hardcoded_secret",
        r"(?i)(?:password|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"]{4,}['\"]",
        "fail",
    ),
    ("comment_out_code", r"^\s*//\s*(?:if|for|while|return|def|func|class)\b", "warn"),
    ("empty_except", r"except[^:]*:\s*(?:pass|#.*)?\s*$", "warn"),
]


@dataclass(frozen=True)
class ReviewFinding:
    """单条审查发现。

    Attributes:
        axis: STANDARDS 或 SPEC。
        severity: fail / warn / info。
        rule: 命中规则名。
        detail: 说明 (含位置/原文摘要)。
    """

    axis: str
    severity: str
    rule: str
    detail: str


@dataclass
class ReviewReport:
    """双轴审查报告。

    Attributes:
        findings: 全部发现。
        spec_coverage: Spec 轴元信息 {declared, touched, missing, extra}。
        standards_baseline: Standards 轴规则基线文本 (LLM 深度判断用,
            由调用方注入, 如 oskill.rulebooks.standards_rules)。
    """

    findings: list[ReviewFinding] = field(default_factory=list)
    spec_coverage: dict[str, Any] = field(default_factory=dict)
    standards_baseline: str | None = None

    def fails(self) -> list[ReviewFinding]:
        """返回全部 fail 级发现。"""
        return [f for f in self.findings if f.severity == "fail"]

    def warns(self) -> list[ReviewFinding]:
        """返回全部 warn 级发现。"""
        return [f for f in self.findings if f.severity == "warn"]

    @property
    def ok(self) -> bool:
        """无 fail 即通过。"""
        return not self.fails()


# ── Standards 轴: 确定性坏味道扫描 ──────────────────────────────────


def scan_standards(
    diff: str,
    *,
    extra_patterns: list[tuple[str, str]] | None = None,
    severity: str = "warn",
) -> list[ReviewFinding]:
    """扫描 diff 中的通用坏味道 (确定性规则)。

    Args:
        diff: unified diff 文本。
        extra_patterns: 追加 (rule_name, regex) 规则 (默认 severity)。
        severity: 追加规则与无 severity 内置规则的默认严重度
            (内置 hardcoded_secret 固定为 fail)。

    Returns:
        Standards 轴发现列表。
    """
    findings: list[ReviewFinding] = []
    patterns: list[tuple[str, str, str]] = [
        (rule, pattern, rule_sev or severity) for rule, pattern, rule_sev in _SMELL_PATTERNS
    ]
    patterns.extend((name, pattern, severity) for name, pattern in (extra_patterns or []))
    for rule, pattern, rule_sev in patterns:
        for match in re.finditer(pattern, diff, re.MULTILINE):
            # 只报告 diff 中新增行 (+ 开头), 忽略上下文/删除行
            line_start = diff.rfind("\n", 0, match.start()) + 1
            line = diff[line_start : diff.find("\n", match.start())]
            if not line.startswith("+"):
                continue
            findings.append(
                ReviewFinding(
                    axis="STANDARDS",
                    severity=rule_sev,
                    rule=rule,
                    detail=f"{rule}: {line.strip()[:80]}",
                )
            )
            break  # 每个规则只报首处, 避免刷屏
    return findings


# ── Spec 轴: 改动文件与 spec 声明范围的比对 ─────────────────────────


def _diff_files(diff: str) -> list[str]:
    """提取 diff 中改动的文件路径 (+++ b/...)。"""
    files: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:].strip())
    return files


def scan_spec_coverage(
    diff: str,
    spec: str,
    *,
    spec_files: list[str] | None = None,
) -> dict[str, Any]:
    """Spec 轴: 对比改动文件与 spec 声明的范围。

    Args:
        diff: unified diff 文本。
        spec: spec 文档文本 (用于文件名出现检查)。
        spec_files: 显式声明允许改动的文件列表; None 时从 spec 文本
            中按路径样式提取。

    Returns:
        {declared, touched, missing, extra}
        declared=spec 声明范围, touched=实际改动, missing=声明未改,
        extra=改动越界 (不在声明范围)。
    """
    touched = _diff_files(diff)
    if spec_files is not None:
        declared = list(spec_files)
    else:
        declared = list(
            dict.fromkeys(
                path.strip()
                for path in re.findall(
                    r"`?([\w./-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|vue|typ|tex))`?", spec
                )
            )
        )
    touched_set = set(touched)
    declared_set = set(declared)
    return {
        "declared": declared,
        "touched": touched,
        "missing": sorted(declared_set - touched_set),
        "extra": sorted(touched_set - declared_set),
    }


def review_diff(
    diff: str,
    *,
    spec: str | None = None,
    spec_files: list[str] | None = None,
    extra_patterns: list[tuple[str, str]] | None = None,
    standards_rules: str | None = None,
) -> ReviewReport:
    """一站式双轴审查: Standards 扫描 + Spec 覆盖比对。

    Args:
        diff: unified diff 文本。
        spec: spec 文档文本; None 时跳过 Spec 轴。
        spec_files: spec 声明允许改动的文件; None 时从 spec 提取。
        extra_patterns: Standards 轴追加规则。
        standards_rules: Standards 轴规则基线文本 (如
            oskill.rulebooks.standards_rules 拼装的规则), 附到报告供 LLM
            深度判断, 不改变确定性扫描结果。

    Returns:
        ReviewReport。

    Example:
        >>> r = review_diff("+def f():\\n+    print(1)\\n", spec="")
        >>> any(f.rule == "debug_leftover" for f in r.findings)
        True
    """
    report = ReviewReport(standards_baseline=standards_rules)
    report.findings.extend(scan_standards(diff, extra_patterns=extra_patterns))
    if spec is not None:
        coverage = scan_spec_coverage(diff, spec, spec_files=spec_files)
        report.spec_coverage = coverage
        for extra_file in coverage["extra"]:
            report.findings.append(
                ReviewFinding(
                    axis="SPEC",
                    severity="fail",
                    rule="scope_extra",
                    detail=f"改动越界 (spec 未声明): {extra_file}",
                )
            )
        if coverage["missing"]:
            report.findings.append(
                ReviewFinding(
                    axis="SPEC",
                    severity="warn",
                    rule="scope_missing",
                    detail=f"spec 声明未改动: {', '.join(coverage['missing'])}",
                )
            )
    return report
