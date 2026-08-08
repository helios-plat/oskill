"""oskill.doc_extractors — 文档提取器 (Dify datasource 真实适配 3O 内化)。

真实文档文本提取 (纯 Python 优先, 无外部依赖):
  * **extract_text** — 按扩展名分派 (txt/md/csv/json/docx/xlsx/pdf);
  * **docx/xlsx** — zip + XML 解析 (纯 Python, 无 openpyxl/docx 依赖);
  * **pdf** — pymupdf 可选 (缺失时报清晰错误);
  * **fetch_url** — urllib 网页拉取 + HTML strip;
  * **DataSourceAdapter** — 格式注册器 (可扩展)。
零 veya 反向依赖: zipfile/xml/urllib 标准库。
"""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from pathlib import Path

Extractor = Callable[[str | Path], str]
"""提取器: (源) → 文本。"""

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_txt(source: str | Path) -> str:
    return Path(source).read_text(encoding="utf-8", errors="replace")


def extract_csv(source: str | Path) -> str:
    with open(source, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    return "\n".join("\t".join(row) for row in rows)


def extract_json(source: str | Path) -> str:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=1)


def extract_docx(source: str | Path) -> str:
    """Word 文档文本 (zip + document.xml, 纯 Python)。"""
    with zipfile.ZipFile(source) as zf:
        if "word/document.xml" not in zf.namelist():
            raise ValueError(f"not a docx: {source}")
        root = ET.fromstring(zf.read("word/document.xml"))
    paragraphs: list[str] = []
    for para in root.iter(f"{{{_NS['w']}}}p"):
        texts = [node.text or "" for node in para.iter(f"{{{_NS['w']}}}t")]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def extract_xlsx(source: str | Path) -> str:
    """Excel 工作表文本 (sharedStrings + sheet, 纯 Python)。"""
    with zipfile.ZipFile(source) as zf:
        names = zf.namelist()
        if "xl/sharedStrings.xml" in names:
            ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.itertext())
                for node in ss_root.iter(
                    "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"
                )
            ]
        else:
            shared = []
        sheet_name = next(
            (n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")), None
        )
        if sheet_name is None:
            return ""
        sheet_root = ET.fromstring(zf.read(sheet_name))
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows: list[str] = []
    for row in sheet_root.iter(f"{ns}row"):
        cells: list[str] = []
        for cell in row.iter(f"{ns}c"):
            value_node = cell.find(f"{ns}v")
            if value_node is None or value_node.text is None:
                continue
            if cell.get("t") == "s":
                idx = int(value_node.text)
                cells.append(shared[idx] if idx < len(shared) else "")
            else:
                cells.append(value_node.text)
        if cells:
            rows.append("\t".join(cells))
    return "\n".join(rows)


def extract_pdf(source: str | Path) -> str:
    """PDF 文本 (pymupdf 可选)。"""
    try:
        import pymupdf  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("pymupdf 未安装; pip install pymupdf 后可提取 PDF") from exc
    doc = pymupdf.open(str(source))
    return "\n".join(page.get_text() for page in doc)


def fetch_url(url: str, *, max_chars: int = 100_000) -> str:
    """网页拉取 + HTML strip (urllib)。"""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "veya-doc-extractor"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


class DataSourceAdapter:
    """数据源适配器: 格式 → 提取器注册表。"""

    def __init__(self) -> None:
        self.extractors: dict[str, Extractor] = {
            ".txt": extract_txt,
            ".md": extract_txt,
            ".csv": extract_csv,
            ".json": extract_json,
            ".docx": extract_docx,
            ".xlsx": extract_xlsx,
            ".pdf": extract_pdf,
        }

    def register(self, ext: str, extractor: Extractor) -> None:
        self.extractors[ext.lower()] = extractor

    def supported(self) -> list[str]:
        return sorted(self.extractors)

    def extract(self, source: str | Path) -> str:
        """按扩展名分派提取。"""
        ext = Path(str(source)).suffix.lower()
        if ext not in self.extractors:
            raise ValueError(f"unsupported format: {ext!r}; supported: {self.supported()}")
        return self.extractors[ext](source)


DEFAULT_ADAPTER = DataSourceAdapter()


def extract_text(source: str | Path) -> str:
    """统一提取入口。"""
    return DEFAULT_ADAPTER.extract(source)


__all__ = [
    "DEFAULT_ADAPTER",
    "DataSourceAdapter",
    "extract_csv",
    "extract_docx",
    "extract_json",
    "extract_pdf",
    "extract_text",
    "extract_txt",
    "extract_xlsx",
    "fetch_url",
]
