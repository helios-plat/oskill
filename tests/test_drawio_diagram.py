"""Tests for drawio_diagram (4drawio SKILL 3O 内化)."""

from __future__ import annotations

from pathlib import Path

import pytest

from oskill.drawio_diagram import (
    STYLE_BOX,
    drawio_doc,
    drawio_edge,
    drawio_node,
    export_drawio,
    render_drawio,
    validate_drawio,
)


class _ShellResult:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self) -> bool:
        return self.code == 0


class TestElements:
    def test_node_defaults(self) -> None:
        node = drawio_node("n1", "输入")
        assert node["type"] == "node"
        assert node["id"] == "n1"
        assert node["style"] == STYLE_BOX
        assert node["width"] == 120

    def test_edge(self) -> None:
        edge = drawio_edge("e1", "n1", "n2", label="处理")
        assert edge == {"type": "edge", "id": "e1", "source": "n1", "target": "n2", "label": "处理"}


class TestDoc:
    def test_builds_mxfile_with_nodes_and_edges(self) -> None:
        nodes = [drawio_node("n1", "输入"), drawio_node("n2", "处理", x=200, y=50)]
        edges = [drawio_edge("e1", "n1", "n2", label="步骤")]
        xml_text = drawio_doc("流程", nodes, edges)
        assert "<mxfile>" in xml_text
        assert 'id="n1"' in xml_text
        assert 'id="e1"' in xml_text
        assert 'source="n1"' in xml_text
        assert 'target="n2"' in xml_text
        assert 'vertex="1"' in xml_text
        assert 'edge="1"' in xml_text

    def test_escapes_special_chars(self) -> None:
        nodes = [drawio_node("n1", '含 "引号" 与 <尖括号> & 符号')]
        xml_text = drawio_doc("t", nodes, [])
        assert '"引号"' not in xml_text  # 引号必须被转义
        assert "&lt;" in xml_text
        assert "&amp;" in xml_text

    def test_empty_diagram_still_valid_xml(self) -> None:
        xml_text = drawio_doc("empty", [], [])
        assert xml_text.startswith("<mxfile>")


class TestValidate:
    def test_valid_file(self, tmp_path: Path) -> None:
        path = tmp_path / "fig.drawio"
        nodes = [drawio_node("n1", "A"), drawio_node("n2", "B", x=200)]
        edges = [drawio_edge("e1", "n1", "n2")]
        path.write_text(drawio_doc("t", nodes, edges), encoding="utf-8")
        result = validate_drawio(path)
        assert result["ok"] is True
        assert result["node_count"] == 2
        assert result["edge_count"] == 1

    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "fig.drawio"
        path.write_text("", encoding="utf-8")
        result = validate_drawio(path)
        assert result["ok"] is False

    def test_bad_xml(self, tmp_path: Path) -> None:
        path = tmp_path / "fig.drawio"
        path.write_text("<mxfile><diagram>", encoding="utf-8")
        result = validate_drawio(path)
        assert result["ok"] is False
        assert result["well_formed"] is False

    def test_dangling_edge(self, tmp_path: Path) -> None:
        path = tmp_path / "fig.drawio"
        path.write_text(
            drawio_doc("t", [drawio_node("n1", "A")], [drawio_edge("e1", "n1", "ghost")]),
            encoding="utf-8",
        )
        result = validate_drawio(path)
        assert result["ok"] is False
        assert any("不存在" in problem for problem in result["problems"])


class TestExport:
    def test_missing_binary_reports_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oskill.drawio_diagram.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        result = export_drawio("in.drawio", "out.pdf")
        assert result["available"] is False
        assert result["output"] is None

    def test_export_success(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        src = tmp_path / "in.drawio"
        src.write_text("<mxfile/>", encoding="utf-8")
        pdf = tmp_path / "out.pdf"
        commands: list[str] = []

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            commands.append(command)
            if command.startswith("command -v"):
                return _ShellResult(stdout="/usr/bin/drawio")
            pdf.write_bytes(b"%PDF")
            return _ShellResult()

        monkeypatch.setattr("oskill.drawio_diagram.bash_exec", fake_bash_exec)
        result = export_drawio(src, pdf)
        assert result["available"] is True
        assert result["ok"] is True
        assert result["output"] == str(pdf)
        assert any("--export --format pdf" in c for c in commands)


class TestRender:
    def test_full_flow(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        pdf_path = tmp_path / "out" / "diagram.pdf"

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v"):
                return _ShellResult(stdout="/usr/bin/drawio")
            pdf_path.write_bytes(b"%PDF")
            return _ShellResult()

        monkeypatch.setattr("oskill.drawio_diagram.bash_exec", fake_bash_exec)
        nodes = [drawio_node("n1", "输入"), drawio_node("n2", "处理", x=200)]
        result = render_drawio(
            "流程", nodes, [drawio_edge("e1", "n1", "n2")], out_dir=tmp_path / "out"
        )
        assert result["ok"] is True
        assert Path(result["drawio"]).exists()
        assert result["pdf"] == str(pdf_path)
        assert result["validate"]["node_count"] == 2

    def test_no_export_keeps_source(self, tmp_path: Path) -> None:
        result = render_drawio(
            "t", [drawio_node("n1", "A")], [], out_dir=tmp_path / "out", export=False
        )
        assert result["ok"] is True
        assert Path(result["drawio"]).exists()
        assert result["pdf"] is None
