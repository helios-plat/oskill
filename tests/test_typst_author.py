"""Tests for typst_author (typst-author SKILL 3O 内化)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oskill.typst_author import (
    TYPST_GUIDE,
    typst_compile,
    typst_format_check,
    typst_minimal_doc,
    typst_probe,
)


# oprim.ShellResult 结构 (stdout/stderr/code + ok 属性)
class _ShellResult:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self) -> bool:
        return self.code == 0


class TestMinimalDoc:
    def test_contains_document_set(self) -> None:
        src = typst_minimal_doc(title="论文", author="作者", lang="zh")
        assert '#set document(title: "论文", author: "作者")' in src
        assert '#set text(lang: "zh")' in src

    def test_defaults(self) -> None:
        src = typst_minimal_doc()
        assert '#set document(title: "My Document"' in src

    def test_no_latex_syntax(self) -> None:
        src = typst_minimal_doc()
        assert "\\begin" not in src
        assert "\\section" not in src


class TestFormatCheck:
    def test_missing_typstyle_returns_available_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "oskill.typst_author.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        result = typst_format_check("a.typ")
        assert result["available"] is False
        assert result["formatted"] is False

    def test_well_formatted_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        path = tmp_path / "doc.typ"
        path.write_text("#set text(font: \"serif\")\n", encoding="utf-8")

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v typstyle"):
                return _ShellResult(stdout="/usr/bin/typstyle")
            return _ShellResult()  # typstyle --check 通过

        monkeypatch.setattr("oskill.typst_author.bash_exec", fake_bash_exec)
        result = typst_format_check(path)
        assert result["available"] is True
        assert result["formatted"] is True
        assert result["applied"] is False

    def test_needs_format_then_apply(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        path = tmp_path / "doc.typ"
        path.write_text("#set text(font: \"serif\")\n", encoding="utf-8")
        calls: list[str] = []

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            calls.append(command)
            if command.startswith("command -v typstyle"):
                return _ShellResult(stdout="/usr/bin/typstyle")
            if command.startswith("typstyle --check"):
                return _ShellResult(stderr="format differs", code=1)
            if command.startswith("typstyle --diff"):
                return _ShellResult(stdout="- old\n+ new")
            if command.startswith("typstyle -i"):
                return _ShellResult()
            return _ShellResult()

        monkeypatch.setattr("oskill.typst_author.bash_exec", fake_bash_exec)
        result = typst_format_check(path, apply=True)
        assert result["available"] is True
        assert result["formatted"] is False
        assert "old" in result["diff"]
        assert result["applied"] is True
        assert any(c.startswith("typstyle -i") for c in calls)


class TestProbe:
    def test_missing_typst(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oskill.typst_author.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        result = typst_probe("1 + 2")
        assert result["available"] is False

    def test_probe_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        commands: list[str] = []

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            commands.append(command)
            if command.startswith("command -v typst"):
                return _ShellResult(stdout="/usr/bin/typst")
            return _ShellResult(stdout="3")

        monkeypatch.setattr("oskill.typst_author.bash_exec", fake_bash_exec)
        result = typst_probe("1 + 2")
        assert result["available"] is True
        assert result["value"] == "3"
        assert any("typst query -" in c for c in commands)


class TestCompile:
    def test_missing_typst(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oskill.typst_author.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        result = typst_compile("doc.typ")
        assert result["available"] is False

    def test_compile_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        doc = tmp_path / "doc.typ"
        doc.write_text("#hello\n", encoding="utf-8")
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF")

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v typst"):
                return _ShellResult(stdout="/usr/bin/typst")
            return _ShellResult()

        monkeypatch.setattr("oskill.typst_author.bash_exec", fake_bash_exec)
        result = typst_compile(doc)
        assert result["available"] is True
        assert result["ok"] is True
        assert result["pdf"] == str(pdf)


class TestGuide:
    def test_guide_has_key_sections(self) -> None:
        for key in (
            "critical_distinctions",
            "hash_usage",
            "styling",
            "common_mistakes",
            "troubleshooting",
        ):
            assert key in TYPST_GUIDE

    def test_guide_mentions_no_tuples(self) -> None:
        assert "tuple" in str(TYPST_GUIDE["critical_distinctions"]).lower()
