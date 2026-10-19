"""oskill.test_report — 测试结果契约 (Cypress runner 机制 3O 内化)。

测试运行的结构化契约 (Cypress runner 输出语义):
  * **TestCaseResult** — 用例结果 (name/status/duration/error/证据);
  * **TestRunReport** — 汇总 (passed/failed/skipped + 失败详情 +
    命令轨迹);
  * **collect_test_run** — 执行测试函数 (注入) → 收集结果;
  * 与 test_stability (重试/actionability) / eval_suite 组合。
零 veya 反向依赖: 测试函数注入; 纯收集。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

STATUS_PASSED = "passed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUSES = (STATUS_PASSED, STATUS_FAILED, STATUS_SKIPPED)


@dataclass
class TestCaseResult:
    """一个用例结果。

    Attributes:
        name: 用例名。
        status: passed/failed/skipped。
        duration_ms: 耗时。
        error: 失败信息。
        evidence: 证据 (截图/命令轨迹)。
    """

    name: str
    status: str = STATUS_PASSED
    duration_ms: float = 0.0
    error: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error[:300],
            "evidence": self.evidence,
        }


@dataclass
class TestRunReport:
    """一次测试运行的汇总报告 (Cypress runner 输出语义)。"""

    suite: str
    results: list[TestCaseResult] = field(default_factory=list)
    command_log: list[str] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def passed(self) -> list[TestCaseResult]:
        return [r for r in self.results if r.status == STATUS_PASSED]

    @property
    def failed(self) -> list[TestCaseResult]:
        return [r for r in self.results if r.status == STATUS_FAILED]

    @property
    def skipped(self) -> list[TestCaseResult]:
        return [r for r in self.results if r.status == STATUS_SKIPPED]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "total": len(self.results),
            "passed": len(self.passed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "ok": self.ok,
            "results": [r.to_dict() for r in self.results],
            "command_log": self.command_log[-50:],
        }

    def summary_line(self) -> str:
        return (
            f"{self.suite}: {len(self.passed)} passed, "
            f"{len(self.failed)} failed, {len(self.skipped)} skipped"
        )


TestCaseFn = Callable[[], TestCaseResult]
"""用例执行函数: () → 结果 (或抛异常记 failed)。"""


def collect_test_run(
    suite: str,
    cases: dict[str, TestCaseFn],
    *,
    log_command: Callable[[str], str] | None = None,
) -> TestRunReport:
    """执行一组用例并收集结果 (异常 → failed, 跳过标记 handled 由调用方)。

    Args:
        suite: 套件名。
        cases: 用例名 → 执行函数。
        log_command: 命令记录函数 (注入, 如 Cypress command log)。

    Returns:
        TestRunReport。
    """
    report = TestRunReport(suite=suite)
    for name, fn in cases.items():
        start = time.monotonic()
        try:
            result = fn()
            if not isinstance(result, TestCaseResult):
                result = TestCaseResult(name=name, status=STATUS_PASSED)
        except Exception as exc:  # noqa: BLE001
            result = TestCaseResult(
                name=name, status=STATUS_FAILED, error=f"{exc.__class__.__name__}: {exc}"
            )
        result.duration_ms = (time.monotonic() - start) * 1000
        report.results.append(result)
        if log_command is not None:
            report.command_log.append(log_command(f"{name}: {result.status}"))
    report.finished_at = time.time()
    return report


def skipped_case(reason: str) -> TestCaseResult:
    """构造跳过用例。"""
    return TestCaseResult(name=reason, status=STATUS_SKIPPED)


__all__ = [
    "STATUS_FAILED",
    "STATUS_PASSED",
    "STATUS_SKIPPED",
    "STATUSES",
    "TestCaseResult",
    "TestRunReport",
    "collect_test_run",
    "skipped_case",
]
