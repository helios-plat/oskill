"""Tests for figure_templates (mathmodel-figure-templates SKILL 3O 内化)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oskill.figure_templates import (
    FIGURE_TEMPLATES,
    list_figure_templates,
    normalize,
    render_figure_template,
    resolve_template,
)


class TestNormalize:
    def test_lowercase_and_dash(self) -> None:
        assert normalize("Paired_Raincloud") == "paired-raincloud"

    def test_folds_garbage(self) -> None:
        assert normalize("  cv  roc  ") == "cv-roc"


class TestResolveTemplate:
    def test_canonical_id(self) -> None:
        assert resolve_template("paired-raincloud") == "paired-raincloud"

    def test_alias(self) -> None:
        assert resolve_template("raincloud") == "paired-raincloud"
        assert resolve_template("circos") == "nature-chord-diagram"

    def test_cjk_hint(self) -> None:
        assert resolve_template("云雨图") == "paired-raincloud"
        assert resolve_template("泰勒图") == "taylor-diagram"
        assert resolve_template("环形热图") == "grouped-circular-heatmap"

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            resolve_template("does-not-exist")


class TestList:
    def test_all_registered(self) -> None:
        ids = list_figure_templates()
        assert set(ids) == set(FIGURE_TEMPLATES)
        assert ids == sorted(ids)


class TestRender:
    def test_copies_script_and_writes_readme(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        project = tmp_path / "绘图复刻"
        outputs_dir = project / "outputs"
        outputs_dir.mkdir(parents=True)
        # 预置输出文件, 模拟脚本执行成功
        stem = "paired_raincloud_replica"
        for suffix in (".png", ".pdf", ".svg"):
            (outputs_dir / f"{stem}{suffix}").write_bytes(b"x")

        def fake_subprocess_run(cmd, **kwargs):  # noqa: ANN001
            class _R:
                returncode = 0
                stderr = ""

            return _R()

        monkeypatch.setattr("oskill.figure_templates.subprocess.run", fake_subprocess_run)

        result = render_figure_template("raincloud", project_dir=project, python="python3")
        assert result["ok"] is True
        assert result["template_id"] == "paired-raincloud"

        project = tmp_path / "绘图复刻"
        scripts_dir = project / "scripts"
        assert (scripts_dir / "make_paired_raincloud.py").exists()
        assert result["script"] == str(scripts_dir / "make_paired_raincloud.py")
        assert len(result["outputs"]) == 3
        assert (project / "README.md").exists()
        assert "paired-raincloud" in (project / "README.md").read_text(encoding="utf-8")

    def test_reuses_existing_script_without_overwrite(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        project = tmp_path / "p"
        scripts_dir = project / "scripts"
        scripts_dir.mkdir(parents=True)
        existing = scripts_dir / "make_paired_raincloud.py"
        existing.write_text("# user-customized\n", encoding="utf-8")

        def fake_subprocess_run(cmd, **kwargs):  # noqa: ANN001
            class _R:
                returncode = 0
                stderr = ""

            return _R()

        monkeypatch.setattr("oskill.figure_templates.subprocess.run", fake_subprocess_run)

        result = render_figure_template("paired-raincloud", project_dir=project)
        assert result["ok"] is True
        # 未 overwrite → 用户定制脚本保留
        assert existing.read_text(encoding="utf-8") == "# user-customized\n"

    def test_render_failure_reports_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def fake_subprocess_run(cmd, **kwargs):  # noqa: ANN001
            class _R:
                returncode = 2
                stderr = "boom"

            return _R()

        monkeypatch.setattr("oskill.figure_templates.subprocess.run", fake_subprocess_run)

        result = render_figure_template("raincloud", project_dir=tmp_path / "p")
        assert result["ok"] is False
        assert result["returncode"] == 2
        assert "boom" in result["error"]
        assert result["outputs"] == []
