"""oskill.drawio_diagram — DrawIO 非数据图示绘制技能 (4drawio SKILL 3O 内化)。

机制: 节点/边 spec → mxfile XML → 写 .drawio → drawio CLI 导出 PDF → 自检。
领域无关: 不预设技术路线图/求解流程图等建模专属图型, 由调用方通过节点/边
spec 自由组合; 导出与自检是纯机制, 可服务任何文档的非数据图示需求。

零 veya 反向依赖: drawio 命令由装配层提供 (缺失时返回结构化结果, 保留
.drawio 源文件并记录失败原因)。XML 生成用 ElementTree 保证转义正确。
"""

from __future__ import annotations

import shlex
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from oprim._bash_exec import bash_exec

# ── 样式常量 (drawio 节点常用样式, 可按需覆盖) ──────────────────────

STYLE_BOX = "rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=12;"
STYLE_PROCESS = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;"
)
STYLE_DECISION = "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;"
STYLE_DATA = "ellipse;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=12;"
STYLE_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;fontSize=11;"


def drawio_node(
    node_id: str,
    label: str,
    *,
    x: float = 0,
    y: float = 0,
    width: float = 120,
    height: float = 60,
    style: str | None = None,
) -> dict[str, Any]:
    """构造一个 drawio 节点描述 (不直接生成 XML)。

    Args:
        node_id: 节点唯一 id (edge 引用用)。
        label: 节点文字 (应短, 长句留给正文)。
        x, y: 左上角坐标。
        width, height: 尺寸。
        style: 样式串, 默认 STYLE_BOX。

    Returns:
        节点 dict, 供 drawio_doc() 使用。
    """
    return {
        "type": "node",
        "id": node_id,
        "label": label,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "style": style or STYLE_BOX,
    }


def drawio_edge(
    edge_id: str,
    source: str,
    target: str,
    *,
    label: str = "",
) -> dict[str, Any]:
    """构造一条 drawio 边描述。

    Args:
        edge_id: 边唯一 id。
        source: 源节点 id。
        target: 目标节点 id。
        label: 边上的文字 (可空)。

    Returns:
        边 dict, 供 drawio_doc() 使用。
    """
    return {"type": "edge", "id": edge_id, "source": source, "target": target, "label": label}


def _build_mxfile_xml(
    title: str,
    elements: list[dict[str, Any]],
    page_width: float,
    page_height: float,
    edge_style: str,
) -> str:
    """由元素列表生成 mxfile XML 字符串。"""
    mxfile = ET.Element("mxfile")
    diagram = ET.SubElement(mxfile, "diagram", {"name": "Page-1"})
    model = ET.SubElement(
        diagram, "mxGraphModel", {"dx": "0", "dy": "0", "grid": "1", "gridSize": "10"}
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for el in elements:
        if el["type"] == "node":
            attrs: dict[str, str] = {
                "id": el["id"],
                "value": el["label"],
                "style": el["style"],
                "vertex": "1",
                "parent": "1",
            }
            geometry = ET.SubElement(root, "mxCell", attrs)
            ET.SubElement(
                geometry,
                "mxGeometry",
                {
                    "x": str(el["x"]),
                    "y": str(el["y"]),
                    "width": str(el["width"]),
                    "height": str(el["height"]),
                    "as": "geometry",
                },
            )
        else:  # edge
            attrs = {
                "id": el["id"],
                "value": el["label"],
                "style": edge_style,
                "edge": "1",
                "parent": "1",
                "source": el["source"],
                "target": el["target"],
            }
            edge = ET.SubElement(root, "mxCell", attrs)
            ET.SubElement(
                edge,
                "mxGeometry",
                {"relative": "1", "as": "geometry"},
            )
    ET.indent(mxfile, space="  ")
    return ET.tostring(mxfile, encoding="unicode")


def drawio_doc(
    title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    page_width: float = 800,
    page_height: float = 600,
    edge_style: str | None = None,
) -> str:
    """由节点/边描述生成完整的 .drawio 源文件内容。

    Args:
        title: diagram 名称 (仅元数据)。
        nodes: drawio_node() 输出列表。
        edges: drawio_edge() 输出列表。
        page_width, page_height: 画布尺寸。
        edge_style: 边样式, 默认 STYLE_EDGE。

    Returns:
        mxfile XML 字符串, 可直接写入 .drawio 文件。

    Example:
        >>> nodes = [drawio_node("n1", "输入"), drawio_node("n2", "处理", x=200)]
        >>> edges = [drawio_edge("e1", "n1", "n2")]
        >>> "<mxfile>" in drawio_doc("流程", nodes, edges)
        True
    """
    elements = list(nodes) + list(edges)
    return _build_mxfile_xml(title, elements, page_width, page_height, edge_style or STYLE_EDGE)


def export_drawio(
    source: str | Path,
    output_pdf: str | Path,
    *,
    binary: str | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """用 drawio CLI 将 .drawio 导出为 PDF。

    自动探测可用二进制 (drawio / draw.io / draw.io.exe)。

    Args:
        source: .drawio 源文件。
        output_pdf: 输出 PDF 路径。
        binary: 显式指定 drawio 命令; None 时自动探测。
        extra_args: 额外 CLI 参数 (如 ["--crop"] 已默认包含)。

    Returns:
        {available, ok, code, stdout, stderr, output}
    """
    source_path = Path(source)
    output_path = Path(output_pdf)
    candidates = [binary] if binary else ["drawio", "draw.io", "draw.io.exe"]
    chosen = None
    for cand in candidates:
        if cand is None:
            continue
        probe = bash_exec(f"command -v {shlex.quote(cand)}")
        if probe.ok and probe.stdout.strip():
            chosen = cand
            break
    if chosen is None:
        return {
            "available": False,
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": "DrawIO command not found; keep .drawio source and record export failure.",
            "output": None,
        }
    args = extra_args or []
    cmd = (
        f"{shlex.quote(chosen)} --export --format pdf --crop "
        + " ".join(args)
        + f" --output {shlex.quote(str(output_path))} {shlex.quote(str(source_path))}"
    )
    result = bash_exec(cmd, timeout=120)
    output = str(output_path) if result.ok and output_path.exists() else None
    return {
        "available": True,
        "ok": result.ok,
        "code": result.code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output": output,
    }


def validate_drawio(path: str | Path) -> dict[str, Any]:
    """自检 .drawio 文件: 非空 + XML 良构 + 含有效 mxCell 结构。

    Args:
        path: .drawio 文件。

    Returns:
        {ok, well_formed, node_count, edge_count, problems}
    """
    file_path = Path(path)
    problems: list[str] = []
    if not file_path.exists() or file_path.stat().st_size == 0:
        return {
            "ok": False,
            "well_formed": False,
            "node_count": 0,
            "edge_count": 0,
            "problems": ["文件为空或不存在"],
        }
    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        return {
            "ok": False,
            "well_formed": False,
            "node_count": 0,
            "edge_count": 0,
            "problems": [f"XML 解析失败: {exc}"],
        }
    root = tree.getroot()
    cells = root.findall(".//mxCell")
    node_count = sum(1 for c in cells if c.get("vertex") == "1")
    edge_count = sum(1 for c in cells if c.get("edge") == "1")
    if node_count == 0 and edge_count == 0:
        problems.append("没有有效 mxCell 节点/边")
    node_ids = {c.get("id") for c in cells if c.get("vertex") == "1"}
    for c in cells:
        if c.get("edge") == "1" and (
            c.get("source") not in node_ids or c.get("target") not in node_ids
        ):
            problems.append(f"边 {c.get('id')} 引用了不存在的节点")
    return {
        "ok": not problems,
        "well_formed": True,
        "node_count": node_count,
        "edge_count": edge_count,
        "problems": problems,
    }


def render_drawio(
    title: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    out_dir: str | Path,
    filename: str = "diagram",
    export: bool = True,
    binary: str | None = None,
) -> dict[str, Any]:
    """一站式: 生成 XML → 写 .drawio → 自检 → (可选) 导出 PDF。

    Args:
        title: 图名称。
        nodes: drawio_node() 列表。
        edges: drawio_edge() 列表。
        out_dir: 输出目录 (自动创建)。
        filename: 输出文件名前缀 (不含扩展名)。
        export: True 时尝试导出 PDF。
        binary: drawio 命令; None 自动探测。

    Returns:
        {ok, drawio, pdf, validate, export}
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    drawio_path = out / f"{filename}.drawio"
    pdf_path = out / f"{filename}.pdf"

    xml_text = drawio_doc(title, nodes, edges)
    drawio_path.write_text(xml_text, encoding="utf-8")

    validation = validate_drawio(drawio_path)
    export_result: dict[str, Any] = {"available": False, "ok": False, "output": None}
    if export:
        export_result = export_drawio(drawio_path, pdf_path, binary=binary)

    return {
        "ok": validation["ok"] and (not export or export_result.get("ok", False)),
        "drawio": str(drawio_path),
        "pdf": export_result.get("output"),
        "validate": validation,
        "export": export_result,
    }
