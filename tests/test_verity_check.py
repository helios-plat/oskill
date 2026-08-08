"""Tests for verity_check (6verity SKILL 3O 内化)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oskill.verity_check import (
    VerityConfig,
    compile_paper,
    pdf_pages,
    resolve_config,
    run_text_gate,
    run_verity,
)


class _ShellResult:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self) -> bool:
        return self.code == 0


def _build_good_paper(tmp_path: Path) -> Path:
    """构造一份通过文本门禁的最小 Typst 论文。"""
    paper = tmp_path / "paper"
    sections = paper / "sections"
    figures = tmp_path / "figures"
    sections.mkdir(parents=True)
    figures.mkdir(parents=True)
    (paper / "main.typ").write_text(
        '#include("sections/1_intro.typ")\n#include("sections/2_body.typ")\n',
        encoding="utf-8",
    )
    (sections / "1_intro.typ").write_text(
        "= 引言\n\n这是引言内容, 足够长以通过章节长度检查。\n", encoding="utf-8"
    )
    (sections / "2_body.typ").write_text("= 主体\n\n主体内容足够长。\n", encoding="utf-8")
    (tmp_path / "results.json").write_text('{"rmse": 0.42}', encoding="utf-8")
    return tmp_path


class TestResolveConfig:
    def test_detects_main_and_sections(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        assert cfg.main == root / "paper" / "main.typ"
        assert cfg.sections_dir == root / "paper" / "sections"

    def test_root_dir_defaults_to_paper_parent(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        assert cfg.root_dir == root


class TestTextGate:
    def test_good_paper_passes(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert not any(item.level == "FAIL" for item in items), [
            i.detail for i in items if i.level == "FAIL"
        ]

    def test_missing_main_fails(self, tmp_path: Path) -> None:
        cfg = resolve_config(VerityConfig(paper_dir=tmp_path / "nope"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and item.check == "main_file" for item in items)

    def test_duplicate_include_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        main = root / "paper" / "main.typ"
        main.write_text(
            '#include("sections/1_intro.typ")\n#include("sections/1_intro.typ")\n',
            encoding="utf-8",
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and "duplicate" in item.detail for item in items)

    def test_missing_included_file_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        main = root / "paper" / "main.typ"
        main.write_text('#include("sections/9_ghost.typ")\n', encoding="utf-8")
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and "does not exist" in item.detail for item in items)

    def test_include_order_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        main = root / "paper" / "main.typ"
        main.write_text(
            '#include("sections/2_body.typ")\n#include("sections/1_intro.typ")\n',
            encoding="utf-8",
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and "not ascending" in item.detail for item in items)

    def test_placeholder_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        (root / "paper" / "sections" / "2_body.typ").write_text(
            "= 主体\n\n这里 TODO 还没写完。\n", encoding="utf-8"
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and item.check == "placeholder" for item in items)

    def test_internal_leak_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        (root / "paper" / "sections" / "2_body.typ").write_text(
            "= 主体\n\n数据来自 _tmp/ 目录。\n", encoding="utf-8"
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and item.check == "internal_leak" for item in items)

    def test_internal_check_can_be_disabled(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        (root / "paper" / "sections" / "2_body.typ").write_text(
            "= 主体\n\n数据来自 _tmp/ 目录。\n", encoding="utf-8"
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper", no_internal_check=True))
        items = run_text_gate(cfg)
        assert not any(item.level == "FAIL" and item.check == "internal_leak" for item in items)

    def test_missing_image_fails(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        (root / "paper" / "sections" / "2_body.typ").write_text(
            '= 主体\n\n#figure(image("../../figures/missing.pdf")) 图\n\n正文内容。\n',
            encoding="utf-8",
        )
        cfg = resolve_config(VerityConfig(paper_dir=root / "paper"))
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and item.check == "image_ref" for item in items)

    def test_custom_internal_terms(self, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        (root / "paper" / "sections" / "2_body.typ").write_text(
            "= 主体\n\n秘密标记 SECRET_MARKER 出现在正文。\n", encoding="utf-8"
        )
        cfg = resolve_config(
            VerityConfig(paper_dir=root / "paper", internal_terms=["SECRET_MARKER"])
        )
        items = run_text_gate(cfg)
        assert any(item.level == "FAIL" and item.check == "internal_leak" for item in items)


class TestCompile:
    def test_missing_typst(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(
            "oskill.verity_check.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        cfg = resolve_config(VerityConfig(paper_dir=tmp_path / "paper"))
        result = compile_paper(cfg)
        assert result["available"] is False
        assert result["ok"] is False

    def test_compile_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        main = tmp_path / "main.typ"
        main.write_text("#hello\n", encoding="utf-8")
        pdf = tmp_path / "main.pdf"

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v typst"):
                return _ShellResult(stdout="/usr/bin/typst")
            pdf.write_bytes(b"%PDF")
            return _ShellResult()

        monkeypatch.setattr("oskill.verity_check.bash_exec", fake_bash_exec)
        cfg = resolve_config(VerityConfig(paper_dir=tmp_path, main=main))
        result = compile_paper(cfg)
        assert result["available"] is True
        assert result["ok"] is True
        assert result["pdf"] == str(pdf)


class TestPdfPages:
    def test_missing_pdf(self, tmp_path: Path) -> None:
        result = pdf_pages(tmp_path / "no.pdf", tmp_path / "pages")
        assert result["available"] is False

    def test_missing_rasterizer(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF")
        monkeypatch.setattr(
            "oskill.verity_check.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        result = pdf_pages(pdf, tmp_path / "pages")
        assert result["available"] is False
        assert "No PDF rasterizer" in result["stderr"]

    def test_rasterize_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"%PDF")
        pages_dir = tmp_path / "pages"
        pages_dir.mkdir()

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v"):
                return _ShellResult(stdout="/usr/bin/pdftoppm")
            (pages_dir / "page-1.png").write_bytes(b"png")
            (pages_dir / "page-2.png").write_bytes(b"png")
            return _ShellResult()

        monkeypatch.setattr("oskill.verity_check.bash_exec", fake_bash_exec)
        result = pdf_pages(pdf, pages_dir)
        assert result["available"] is True
        assert result["tool"] == "pdftoppm"
        assert len(result["pages"]) == 2


class TestRunVerity:
    def test_full_orchestration(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        root = _build_good_paper(tmp_path)
        pdf = root / "paper" / "main.pdf"

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v typst"):
                return _ShellResult(stdout="/usr/bin/typst")
            if command.startswith("typst compile"):
                pdf.write_bytes(b"%PDF")
                return _ShellResult()
            return _ShellResult(stdout="", code=1)

        monkeypatch.setattr("oskill.verity_check.bash_exec", fake_bash_exec)
        report = run_verity(VerityConfig(paper_dir=root / "paper"), compile=True, rasterize=True)
        assert report.engine == "typst"
        assert report.compile is not None
        assert report.compile["ok"] is True
        assert report.pdf_pages is not None  # 栅格化工具缺失 → not_run, 但流程不崩
        assert report.ok is True
        assert any(item.level == "PASS" and item.check == "compile" for item in report.items)
