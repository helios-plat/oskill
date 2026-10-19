"""oskill.verity_check — 论文验收与一致性检查技能 (6verity SKILL 3O 内化)。

机制: 文本质量门禁 (引擎探测 / include 结构 / 标题 / 占位符 / 内部词泄露 /
图表引用 / caption / 引用 / 数值一致性) → 编译 (typst / xelatex×2) →
PDF 页面栅格化 (视觉检查辅助)。检查清单参数化: 领域专属规则 (如"子问题
章节数量核对") 通过 VerityConfig 注入, 不内置任何具体工作流假设。

零 veya 反向依赖: 编译/栅格化命令由装配层提供, 缺失时返回结构化结果。
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from oprim._bash_exec import bash_exec

# ── 数据结构 ────────────────────────────────────────────────────────

PLACEHOLDER_RE = re.compile(r"PLACEHOLDER|TODO|TBD|XXX|待补充|待续写|这里补|示例数据|待完善")

DEFAULT_INTERNAL_TERMS: list[str] = [
    "_tmp/",
    "*.json",
]


@dataclass
class VerityConfig:
    """验收检查的路径与参数配置。

    Attributes:
        paper_dir: 论文目录 (必填)。
        root_dir: 项目根; None 时取 paper_dir 的父目录。
        main: 论文入口 (main.typ / main.tex); None 时自动探测。
        sections_dir: 正文章节目录; None 时自动探测 paper/sections。
        references: 参考文献文件; None 时自动探测。
        figures_dir: 图表目录; None 时自动探测 root/figures。
        results_file: 结果记录文件; None 时自动探测。
        problem_analysis: 问题分析报告 (用于子问题数量软核对); None 跳过。
        all_results: 汇总结果 JSON; None 时自动探测 figures/all_results.json。
        internal_terms: 额外内部工作流词 (正文中出现判 FAIL), 叠加默认项。
        no_internal_check: True 时跳过内部词泄露检查。
        placeholder_pattern: 自定义占位符正则; None 用 PLACEHOLDER_RE。
        problem_section_hint: 问题章节名匹配提示 (如 r"problem|问题|q\\d"),
            仅用于子问题数量软核对; None 跳过该核对。
    """

    paper_dir: str | Path
    root_dir: str | Path | None = None
    main: str | Path | None = None
    sections_dir: str | Path | None = None
    references: str | Path | None = None
    figures_dir: str | Path | None = None
    results_file: str | Path | None = None
    problem_analysis: str | Path | None = None
    all_results: str | Path | None = None
    internal_terms: list[str] = field(default_factory=list)
    no_internal_check: bool = False
    placeholder_pattern: str | None = None
    problem_section_hint: str | None = None


@dataclass
class VerityItem:
    """单条检查结果。

    Attributes:
        level: PASS / WARN / FAIL / INFO。
        check: 检查项名称。
        detail: 说明。
    """

    level: str
    check: str
    detail: str


@dataclass
class VerityReport:
    """验收总报告。

    Attributes:
        engine: 探测到的引擎 (typst / latex / unknown)。
        items: 全部检查项。
        ok: 无 FAIL 项。
        compile: compile_paper() 输出 (如执行)。
        pdf_pages: pdf_pages() 输出 (如执行)。
    """

    engine: str
    items: list[VerityItem] = field(default_factory=list)
    ok: bool = True
    compile: dict[str, Any] | None = None
    pdf_pages: dict[str, Any] | None = None

    def add(self, level: str, check: str, detail: str) -> None:
        """追加一条检查结果 (FAIL 时同步 ok=False)。"""
        self.items.append(VerityItem(level=level, check=check, detail=detail))
        if level == "FAIL":
            self.ok = False

    def fails(self) -> list[VerityItem]:
        """返回全部 FAIL 项。"""
        return [item for item in self.items if item.level == "FAIL"]

    def warns(self) -> list[VerityItem]:
        """返回全部 WARN 项。"""
        return [item for item in self.items if item.level == "WARN"]


# ── 路径解析 (对应 writing_check.sh 的默认推断逻辑) ─────────────────


def resolve_config(config: VerityConfig) -> VerityConfig:
    """补全默认路径推断, 返回可用的完整配置 (不修改原对象)。

    推断顺序与 writing_check.sh 一致: paper_dir → root_dir → main →
    sections_dir → references → figures_dir → results_file →
    problem_analysis → all_results。
    """
    paper = Path(config.paper_dir)
    if config.main is None:
        if (paper / "main.typ").exists():
            main = paper / "main.typ"
        elif (paper / "main.tex").exists():
            main = paper / "main.tex"
        else:
            main = paper / "main.typ"
    else:
        main = Path(config.main)

    if config.root_dir is None:
        root = paper if paper.resolve() == Path(".").resolve() else paper.parent
    else:
        root = Path(config.root_dir)

    sections_dir = (
        Path(config.sections_dir)
        if config.sections_dir
        else (paper / "sections" if (paper / "sections").is_dir() else None)
    )
    references = (
        Path(config.references)
        if config.references
        else (
            paper / "references.typ"
            if (paper / "references.typ").exists()
            else paper / "references.tex"
            if (paper / "references.tex").exists()
            else None
        )
    )
    figures_dir = (
        Path(config.figures_dir)
        if config.figures_dir
        else (root / "figures" if (root / "figures").is_dir() else None)
    )
    results_file = (
        Path(config.results_file)
        if config.results_file
        else (
            root / "reports" / "RESULTS_REPORT.md"
            if (root / "reports" / "RESULTS_REPORT.md").exists()
            else root / "RESULTS_REPORT.md"
            if (root / "RESULTS_REPORT.md").exists()
            else root / "RESULTS_REPORT"
            if (root / "RESULTS_REPORT").exists()
            else None
        )
    )
    problem_analysis = (
        Path(config.problem_analysis)
        if config.problem_analysis
        else (root / "PROBLEM_ANALYSIS.md" if (root / "PROBLEM_ANALYSIS.md").exists() else None)
    )
    all_results = (
        Path(config.all_results)
        if config.all_results
        else (
            figures_dir / "all_results.json"
            if figures_dir and (figures_dir / "all_results.json").exists()
            else None
        )
    )
    return VerityConfig(
        paper_dir=paper,
        root_dir=root,
        main=main,
        sections_dir=sections_dir,
        references=references,
        figures_dir=figures_dir,
        results_file=results_file,
        problem_analysis=problem_analysis,
        all_results=all_results,
        internal_terms=config.internal_terms,
        no_internal_check=config.no_internal_check,
        placeholder_pattern=config.placeholder_pattern,
        problem_section_hint=config.problem_section_hint,
    )


# ── 文本质量门禁 (writing_check.sh Python 化) ──────────────────────


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _extract_calls(text: str, name: str) -> list[tuple[int, int, str]]:
    """提取 Typst 函数调用区间 (支持嵌套括号与字符串)。"""
    calls: list[tuple[int, int, str]] = []
    pattern = re.compile(r"#" + re.escape(name) + r"\s*\(")
    for match in pattern.finditer(text):
        open_pos = text.find("(", match.start())
        depth = 0
        in_string = False
        escape = False
        for idx in range(open_pos, len(text)):
            ch = text[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    calls.append((match.start(), idx + 1, text[open_pos + 1 : idx]))
                    break
    return calls


def _section_sort_key(path: Path) -> tuple[int, str]:
    match = re.match(r"^(\d+)[_-](.*)$", path.name)
    if match:
        return (0, match.group(1), match.group(2))  # type: ignore[return-value]
    return (1, path.name)


def run_text_gate(config: VerityConfig) -> list[VerityItem]:
    """文本质量门禁: 结构 / 标题 / 占位符 / 泄露 / 图表 / 引用 / 数值一致性。

    Args:
        config: 完整配置 (先经 resolve_config)。

    Returns:
        检查项列表 (含 FAIL/WARN/INFO)。
    """
    items: list[VerityItem] = []
    add = lambda level, check, detail: items.append(VerityItem(level, check, detail))  # noqa: E731

    paper = Path(config.paper_dir)
    root = Path(config.root_dir or paper.parent)
    main = Path(config.main)
    sections_dir = config.sections_dir
    refs = config.references
    figures_dir = config.figures_dir
    results_file = config.results_file
    problem_analysis = config.problem_analysis
    all_results = config.all_results

    add("INFO", "paths", f"paper={paper} root={root} main={main}")
    if not paper.exists():
        add("FAIL", "paper_dir", f"paper directory not found: {paper}")
    if not main.exists():
        add("FAIL", "main_file", f"missing main paper file: {main}")
        return items

    is_latex = main.suffix == ".tex"
    is_typst = main.suffix == ".typ"
    engine = "LaTeX" if is_latex else ("Typst" if is_typst else "unknown")
    add("INFO", "engine", f"detected engine: {engine} (main suffix: {main.suffix})")
    if engine == "unknown":
        add("FAIL", "engine", f"unsupported main file extension: {main.suffix}")

    main_text = _read(main)

    # ── section 文件收集 ──
    section_ext = "*.tex" if is_latex else "*.typ"
    if sections_dir and Path(sections_dir).exists():
        section_files = sorted(Path(sections_dir).glob(section_ext), key=_section_sort_key)
    elif paper.exists():
        excluded = {main.resolve()}
        if refs:
            excluded.add(Path(refs).resolve())
        section_files = [
            path
            for path in sorted(paper.rglob(section_ext), key=_section_sort_key)
            if path.resolve() not in excluded
        ]
        if section_files:
            add(
                "WARN",
                "sections_dir",
                "sections dir not supplied; using other files under paper dir as body sections",
            )
    else:
        section_files = []
    add("INFO", "sections", f"section file count: {len(section_files)}")
    if not section_files:
        add(
            "WARN",
            "sections",
            f"no separate section {section_ext} files; treating paper as single-file document",
        )

    # ── include / input 检测 ──
    if is_typst:
        include_re = re.compile(r'#include\(\s*"([^"]+\.typ)"\s*\)')
        includes = include_re.findall(main_text)
    elif is_latex:
        include_re = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
        raw = [inc.strip() for inc in include_re.findall(main_text)]
        includes = [inc if inc.endswith(".tex") else inc + ".tex" for inc in raw]
    else:
        includes = []
    include_names = [Path(inc).name for inc in includes]
    include_paths = [(main.parent / inc).resolve() for inc in includes]

    add("INFO", "includes", f"main include count: {len(includes)}")
    seen: set[str] = set()
    for name in include_names:
        if name in seen:
            add("FAIL", "includes", f"duplicate include: {name}")
        seen.add(name)
    for inc, path in zip(includes, include_paths):
        if not path.exists():
            add("FAIL", "includes", f"included file does not exist: {inc}")

    actual_names = [path.name for path in section_files]
    if includes:
        included_set = set(include_names)
        for name in actual_names:
            if name not in included_set and not name.startswith("A_"):
                add("WARN", "includes", f"body section file not included by main: {name}")
    else:
        add("WARN", "includes", "main has no include/input calls; skip include order checks")

    # ── include 顺序 ──
    def leading_number(name: str) -> int | None:
        match = re.match(r"^(\d+)[_-]", name)
        return int(match.group(1)) if match else None

    numbers = [n for n in (leading_number(nm) for nm in include_names) if n is not None]
    if numbers and numbers != sorted(numbers):
        add("FAIL", "include_order", f"section include order is not ascending: {numbers}")
    if numbers:
        missing = [num for num in range(min(numbers), max(numbers) + 1) if num not in numbers]
        if missing:
            add("WARN", "include_order", f"numbered section sequence has gaps: {missing}")

    # ── 子问题数量软核对 (领域参数化) ──
    if problem_analysis and Path(problem_analysis).exists():
        pa = _read(Path(problem_analysis))
        problem_hits = re.findall(r"(?:子问题|问题)\s*[一二三四五六七八九十0-9]+", pa)
        expected_count = len(set(problem_hits))
        hint = config.problem_section_hint or r"problem|问题|q\d"
        paper_problem = [
            name for name in (include_names or actual_names) if re.search(hint, name, re.I)
        ]
        if expected_count and paper_problem and len(paper_problem) < min(expected_count, 3):
            add(
                "WARN",
                "problem_sections",
                f"paper problem sections may be fewer than analysis subproblems: "
                f"paper={len(paper_problem)}, analysis={expected_count}",
            )
    else:
        add(
            "INFO",
            "problem_sections",
            "problem analysis file not supplied; skip subproblem count check",
        )

    # ── 文本扫描: 占位符 / 内部词泄露 / 章节质量 ──
    placeholder_re = (
        re.compile(config.placeholder_pattern) if config.placeholder_pattern else PLACEHOLDER_RE
    )
    internal_terms = list(DEFAULT_INTERNAL_TERMS) + list(config.internal_terms)
    if results_file:
        internal_terms.append(Path(results_file).name)
    if problem_analysis:
        internal_terms.append(Path(problem_analysis).name)
    if all_results:
        internal_terms.append(Path(all_results).name)
    internal_terms = sorted(set(t for t in internal_terms if t))
    internal_re = (
        re.compile("|".join(re.escape(t) for t in internal_terms)) if internal_terms else None
    )

    typ_files: list[Path] = []
    seen_paths: set[str] = set()
    for path in (
        [main]
        + section_files
        + ([Path(refs)] if refs and Path(refs).exists() else [])
        + sorted(paper.glob(section_ext))
    ):
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen_paths:
            typ_files.append(path)
            seen_paths.add(key)

    combined: list[str] = []
    section_titles: list[tuple[str, str]] = []
    for path in typ_files:
        if not path.exists():
            continue
        text = _read(path)
        combined.append(text)
        path_rel = _rel(path, root)

        if placeholder_re.search(text):
            add("FAIL", "placeholder", f"placeholder text remains in {path_rel}")

        is_appendix = path.name.startswith("A_") or "appendix" in path.name.lower()
        if not config.no_internal_check and internal_re and internal_re.search(text):
            if is_appendix:
                add(
                    "WARN",
                    "internal_leak",
                    f"internal workflow term appears in appendix: {path_rel}",
                )
            else:
                add(
                    "FAIL",
                    "internal_leak",
                    f"internal workflow term leaked into paper text: {path_rel}",
                )

        if path in section_files:
            body = text.strip()
            add("INFO", "section_length", f"{path.name} {len(body)} chars")
            if len(body) < 800 and not path.name.startswith("A_"):
                add("WARN", "section_length", f"section is short: {path.name} ({len(body)} chars)")

            lower_name = path.name.lower()
            is_aux = (
                path.name.startswith("A_")
                or lower_name.startswith("abstract")
                or lower_name.startswith("appendices")
            )
            if is_typst:
                malformed = [
                    line.strip()
                    for line in text.splitlines()
                    if re.match(r"^={1,6}(?![=\s]).+", line)
                ]
                for line in malformed[:5]:
                    add(
                        "FAIL",
                        "heading",
                        f"Typst heading missing space after '=' in {path.name}: {line[:80]}",
                    )
                heading = re.search(r"(?m)^=\s+.+", text)
                if not heading and not is_aux:
                    add("FAIL", "heading", f"section has no level-1 Typst heading: {path.name}")
                if heading:
                    title = heading.group(0).lstrip("= ").strip()
                    section_titles.append((path.name, title))
                if re.search(r"(?m)^={3,}\s+", text):
                    add("WARN", "heading", f"deep heading level appears in section: {path.name}")
                list_count = len(re.findall(r"#(?:enum|list)\s*\(", text))
                if list_count >= 3:
                    add(
                        "WARN",
                        "prose",
                        f"many lists in section, consider prose: {path.name} ({list_count})",
                    )
                figure_calls = _extract_calls(text, "figure")
                text_without = (
                    "".join(part for part in [text[: figure_calls[0][0]]] if figure_calls)
                    if figure_calls
                    else text
                )
                if figure_calls:
                    parts = []
                    last = 0
                    for start, end, _ in figure_calls:
                        parts.append(text[last:start])
                        last = end
                    parts.append(text[last:])
                    text_without = "".join(parts)
                if len(figure_calls) >= 2 and len(text_without.strip()) < 1000:
                    add("WARN", "prose", f"many figures but little surrounding prose: {path.name}")
            else:
                section_headings = re.findall(r"\\section\{([^}]*)\}", text)
                subsection_headings = re.findall(r"\\subsection\{([^}]*)\}", text)
                if not section_headings and not subsection_headings and not is_aux:
                    add("FAIL", "heading", f"section has no \\section{{}} heading: {path.name}")
                for title in section_headings:
                    section_titles.append((path.name, title))
                list_count = len(re.findall(r"\\begin\{(?:itemize|enumerate)\}", text))
                if list_count >= 3:
                    add(
                        "WARN",
                        "prose",
                        f"many lists in section, consider prose: {path.name} ({list_count})",
                    )
                figure_env_count = len(re.findall(r"\\begin\{figure\}", text))
                if figure_env_count >= 2 and len(text) < 2000:
                    add("WARN", "prose", f"many figures but little surrounding prose: {path.name}")

    paper_text = "\n".join(combined)

    # ── 标题去重 ──
    if section_titles:
        titles = [title for _, title in section_titles]
        if len(titles) != len(set(titles)):
            add("FAIL", "heading", "duplicate level-1 section titles detected")

    # ── 图片引用存在性 ──
    if is_typst:
        image_re = re.compile(r'image\(\s*"([^"]+)"')
    elif is_latex:
        image_re = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
    else:
        image_re = None
    if image_re:
        for path in typ_files:
            if not path.exists():
                continue
            for ref in image_re.findall(_read(path)):
                target = (path.parent / ref).resolve()
                if not target.exists():
                    add(
                        "FAIL",
                        "image_ref",
                        f"referenced image does not exist from {_rel(path, root)}: {ref}",
                    )

    # ── 未引用图表 ──
    if figures_dir and Path(figures_dir).exists():
        for fig in sorted(Path(figures_dir).glob("*.pdf")):
            if fig.name not in paper_text:
                add("WARN", "unused_figure", f"figure PDF not referenced in paper: {fig.name}")
    else:
        add("INFO", "unused_figure", "figures dir not supplied/found; skip unused figure check")

    # ── caption 检查 ──
    if is_typst:
        for _, _, body in _extract_calls(paper_text, "figure"):
            if "caption:" not in body:
                add("FAIL", "caption", "figure without caption")
                continue
            cap_match = re.search(r"caption:\s*\[(.*?)\]", body, re.S)
            if cap_match:
                cap = re.sub(r"\s+", " ", cap_match.group(1)).strip()
                if len(cap) > 80:
                    add("WARN", "caption", f"long figure caption: {cap[:80]}...")
                if len(cap) < 4:
                    add("WARN", "caption", "very short figure caption")
    elif is_latex:
        for block in re.findall(r"\\begin\{figure\}.*?\\end\{figure\}", paper_text, re.S):
            cap_match = re.search(r"\\caption\{([^}]*)\}", block)
            if not cap_match:
                add("FAIL", "caption", "LaTeX figure without \\caption{}")
                continue
            cap = re.sub(r"\s+", " ", cap_match.group(1)).strip()
            if len(cap) > 80:
                add("WARN", "caption", f"long figure caption: {cap[:80]}...")
            if len(cap) < 4:
                add("WARN", "caption", "very short figure caption")

    # ── 参考文献与引用 ──
    if refs and Path(refs).exists():
        refs_text = _read(Path(refs))
        if len(refs_text.strip()) < 80:
            add("WARN", "references", f"{_rel(Path(refs), root)} looks very short")
        if is_typst:
            citation_re = r"@\w[\w:-]*|#cite\("
        elif is_latex:
            citation_re = r"\\cite\w*\{[^}]+\}"
        else:
            citation_re = None
        if citation_re and re.search(citation_re, paper_text):
            add("INFO", "references", "citation markers detected")
        else:
            add(
                "WARN",
                "references",
                f"{_rel(Path(refs), root)} exists but no citation markers detected in paper",
            )
    else:
        add(
            "WARN",
            "references",
            "references file not supplied/found; skip reference completeness check",
        )

    # ── 指标一致性 (结果记录) ──
    metric_names = [
        r"rmse",
        r"mae",
        r"mape",
        r"r2",
        r"score",
        r"objective",
        r"accuracy",
        r"precision",
        r"recall",
        r"f1",
        r"权重",
        r"目标值",
        r"误差",
        r"得分",
    ]
    if results_file and Path(results_file).exists():
        results_text = _read(Path(results_file))
        found = [
            name
            for name in metric_names
            if re.search(name, results_text, re.I) and re.search(name, paper_text, re.I)
        ]
        if found:
            add("INFO", "metrics", f"metrics shared between results and paper: {found[:10]}")
        elif re.search("|".join(metric_names), results_text, re.I):
            add(
                "WARN",
                "metrics",
                "metrics appear in result file but are hard to find in paper text",
            )
    else:
        add("INFO", "metrics", "results file not supplied/found; skip metric consistency scan")

    # ── 汇总 JSON 数值扫描 ──
    if all_results and Path(all_results).exists():
        try:
            data = json.loads(_read(Path(all_results)))

            def walk(value: Any) -> list[float]:
                nums: list[float] = []
                if isinstance(value, dict):
                    for item in value.values():
                        nums.extend(walk(item))
                elif isinstance(value, list):
                    for item in value:
                        nums.extend(walk(item))
                elif isinstance(value, (int, float)):
                    nums.append(float(value))
                return nums

            key_nums = []
            for num in walk(data)[:100]:
                if abs(num) >= 1:
                    key_nums.append(str(round(num, 4)).rstrip("0").rstrip("."))
            if key_nums and not any(num and num in paper_text for num in key_nums[:30]):
                add(
                    "WARN",
                    "numeric_consistency",
                    "numeric values from all-results JSON are hard to find in paper",
                )
        except Exception as exc:
            add("WARN", "numeric_consistency", f"cannot parse all-results JSON: {exc}")
    else:
        add(
            "INFO",
            "numeric_consistency",
            "all-results JSON not supplied/found; skip JSON numeric scan",
        )

    if not any(item.level == "FAIL" for item in items):
        add("PASS", "text_gate", "writing text gate passed")
    else:
        add("FAIL", "text_gate", "writing text gate failed")
    return items


# ── 编译 ────────────────────────────────────────────────────────────


def compile_paper(
    config: VerityConfig,
    *,
    main: str | Path | None = None,
    output_pdf: str | Path | None = None,
) -> dict[str, Any]:
    """编译论文入口文件。

    Typst: typst compile; LaTeX: xelatex 跑两遍 (解决目录与交叉引用)。

    Args:
        config: 配置 (用于引擎探测)。
        main: 覆盖入口文件路径。
        output_pdf: 覆盖输出 PDF 路径。

    Returns:
        {available, engine, ok, code, stdout, stderr, pdf}
    """
    main_path = Path(main) if main else Path(config.main)
    is_latex = main_path.suffix == ".tex"
    engine = "LaTeX" if is_latex else ("Typst" if main_path.suffix == ".typ" else "unknown")
    pdf_path = Path(output_pdf) if output_pdf else main_path.with_suffix(".pdf")

    if is_latex:
        probe = bash_exec("command -v xelatex")
        if not (probe.ok and probe.stdout.strip()):
            return {
                "available": False,
                "engine": engine,
                "ok": False,
                "code": None,
                "stdout": "",
                "stderr": "xelatex not found",
                "pdf": None,
            }
        cmd = f"xelatex -interaction=nonstopmode {shlex.quote(str(main_path))}"
        first = bash_exec(cmd, timeout=300)
        if first.ok:
            second = bash_exec(cmd, timeout=300)
            result = second
        else:
            result = first
    else:
        probe = bash_exec("command -v typst")
        if not (probe.ok and probe.stdout.strip()):
            return {
                "available": False,
                "engine": engine,
                "ok": False,
                "code": None,
                "stdout": "",
                "stderr": "typst not found",
                "pdf": None,
            }
        result = bash_exec(
            f"typst compile {shlex.quote(str(main_path))} {shlex.quote(str(pdf_path))}",
            timeout=300,
        )
    pdf = str(pdf_path) if result.ok and pdf_path.exists() else None
    return {
        "available": True,
        "engine": engine,
        "ok": result.ok,
        "code": result.code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pdf": pdf,
    }


# ── PDF 页面栅格化 (视觉检查辅助) ──────────────────────────────────


def pdf_pages(
    pdf: str | Path,
    out_dir: str | Path,
    *,
    binary: str | None = None,
    dpi: int = 160,
) -> dict[str, Any]:
    """将 PDF 每页导出为 PNG (供视觉检查)。

    工具探测顺序: pdftoppm → mutool → magick。均缺失时返回 not_run。

    Args:
        pdf: PDF 文件路径。
        out_dir: 输出目录 (自动创建)。
        binary: 显式指定栅格化命令 (pdftoppm/mutool/magick)。
        dpi: 分辨率。

    Returns:
        {available, tool, ok, pages, code, stderr}
    """
    pdf_path = Path(pdf)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not pdf_path.exists():
        return {
            "available": False,
            "tool": None,
            "ok": False,
            "pages": [],
            "code": None,
            "stderr": f"pdf not found: {pdf_path}",
        }
    candidates = [binary] if binary else ["pdftoppm", "mutool", "magick"]
    for tool in candidates:
        if tool is None:
            continue
        probe = bash_exec(f"command -v {shlex.quote(tool)}")
        if not (probe.ok and probe.stdout.strip()):
            continue
        if tool == "pdftoppm":
            cmd = (
                f"pdftoppm -png -r {dpi} "
                f"{shlex.quote(str(pdf_path))} "
                f"{shlex.quote(str(out / 'page'))}"
            )
        elif tool == "mutool":
            cmd = (
                f"mutool draw -r {dpi} -o "
                f"{shlex.quote(str(out / 'page-%03d.png'))} "
                f"{shlex.quote(str(pdf_path))}"
            )
        else:  # magick
            cmd = (
                f"magick -density {dpi} "
                f"{shlex.quote(str(pdf_path))} "
                f"{shlex.quote(str(out / 'page-%03d.png'))}"
            )
        result = bash_exec(cmd, timeout=300)
        pages = sorted(str(p) for p in out.glob("page*.png"))
        return {
            "available": True,
            "tool": tool,
            "ok": result.ok,
            "pages": pages,
            "code": result.code,
            "stderr": result.stderr,
        }
    return {
        "available": False,
        "tool": None,
        "ok": False,
        "pages": [],
        "code": None,
        "stderr": "No PDF rasterizer found (pdftoppm/mutool/magick)",
    }


# ── 总入口 ──────────────────────────────────────────────────────────


def run_verity(
    config: VerityConfig,
    *,
    compile: bool = True,
    rasterize: bool = False,
    rasterize_dir: str | Path | None = None,
) -> VerityReport:
    """执行完整验收流程: 文本门禁 → (可选) 编译 → (可选) PDF 栅格化。

    Args:
        config: 验收配置 (内部先 resolve_config 补全默认路径)。
        compile: True 时执行 compile_paper。
        rasterize: True 时对编译产出的 PDF 执行 pdf_pages。
        rasterize_dir: 栅格化输出目录; None 时用 <paper_dir>/_tmp/pdf-pages。

    Returns:
        VerityReport (ok = 文本门禁无 FAIL)。

    Example:
        >>> cfg = VerityConfig(paper_dir="paper")
        >>> report = run_verity(cfg, compile=False)
        >>> report.ok in (True, False)
        True
    """
    cfg = resolve_config(config)
    report = VerityReport(engine="unknown")
    gate_items = run_text_gate(cfg)
    report.items.extend(gate_items)
    report.ok = not any(item.level == "FAIL" for item in report.items)
    if main := cfg.main:
        suffix = Path(main).suffix
        report.engine = (
            "latex" if suffix == ".tex" else ("typst" if suffix == ".typ" else "unknown")
        )

    if compile:
        result = compile_paper(cfg)
        report.compile = result
        if not result.get("ok", False):
            report.add(
                "FAIL",
                "compile",
                f"compile failed ({result.get('engine')}): {result.get('stderr', '')[-300:]}",
            )
        else:
            report.add("PASS", "compile", f"compiled OK: {result.get('pdf')}")
        if rasterize and result.get("pdf"):
            out = (
                Path(rasterize_dir)
                if rasterize_dir
                else Path(cfg.paper_dir) / "_tmp" / "pdf-pages"
            )
            pages_result = pdf_pages(result["pdf"], out)
            report.pdf_pages = pages_result
            if pages_result.get("available"):
                report.add(
                    "PASS" if pages_result.get("ok") else "WARN",
                    "pdf_pages",
                    "rasterized "
                    f"{len(pages_result.get('pages', []))} pages "
                    f"via {pages_result.get('tool')}",
                )
            else:
                report.add(
                    "WARN", "pdf_pages", pages_result.get("stderr", "rasterizer unavailable")
                )
    return report
