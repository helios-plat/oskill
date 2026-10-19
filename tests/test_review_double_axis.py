"""Tests for review_double_axis (mattpocock code-review 3O 内化)."""

from __future__ import annotations

from oskill.review_double_axis import (
    review_diff,
    scan_spec_coverage,
    scan_standards,
)


def test_scan_standards_detects_debug_leftover() -> None:
    diff = "+def f():\n+    print(1)\n-    old()\n"
    findings = scan_standards(diff)
    assert any(f.rule == "debug_leftover" for f in findings)


def test_scan_standards_ignores_removed_lines() -> None:
    diff = "-    console.log('gone')\n+    ok()\n"
    findings = scan_standards(diff)
    assert not any(f.rule == "debug_leftover" for f in findings)


def test_scan_standards_extra_patterns() -> None:
    diff = "+    assert user.is_admin  # UNSAFE\n"
    findings = scan_standards(diff, extra_patterns=[("unsafe_comment", r"UNSAFE")])
    assert any(f.rule == "unsafe_comment" for f in findings)


def test_scan_spec_coverage_declared_from_spec_text() -> None:
    diff = "+++ b/src/app.py\n+print('hi')\n"
    spec = "改动文件: `src/app.py` 与 `tests/test_app.py`"
    coverage = scan_spec_coverage(diff, spec)
    assert coverage["touched"] == ["src/app.py"]
    assert "tests/test_app.py" in coverage["missing"]
    assert coverage["extra"] == []


def test_scan_spec_coverage_explicit_files() -> None:
    diff = "+++ b/src/other.py\n+++ b/src/app.py\n"
    coverage = scan_spec_coverage(diff, "", spec_files=["src/app.py"])
    assert coverage["extra"] == ["src/other.py"]
    assert coverage["missing"] == []


def test_review_diff_combines_axes() -> None:
    diff = "+++ b/src/app.py\n+def f():\n+    print('debug')\n+    api_key = 'sk-123456789'\n"
    report = review_diff(diff, spec="只改 src/app.py")
    assert report.ok is False  # 有 fail (secret)
    assert any(f.rule == "hardcoded_secret" and f.severity == "fail" for f in report.findings)
    assert any(f.axis == "STANDARDS" for f in report.findings)
    assert report.spec_coverage["extra"] == []


def test_review_diff_scope_extra_fails() -> None:
    diff = "+++ b/src/unrelated.py\n+print('x')\n"
    report = review_diff(diff, spec="只改 src/app.py")
    assert any(f.rule == "scope_extra" and f.severity == "fail" for f in report.findings)


def test_review_report_helpers() -> None:
    report = review_diff("+TODO fix\n", spec="")
    assert report.warns()  # TODO 是 warn
    assert report.ok is True  # 无 fail
    assert len(report.findings) >= 1
    assert report.fails() == []
