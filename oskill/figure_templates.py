"""oskill.figure_templates — 科研绘图模板渲染技能 (mathmodel-figure-templates SKILL 3O 内化)。

机制: 模板 id / 别名 / 中文关键词 → 解析 → 将内置 matplotlib 脚本复制到工作区
→ 执行 → 输出 png/pdf/svg。模板脚本 (确定性模拟数据, 自包含) 位于
oskill/_figure_templates/templates/, 复制到工作区后可按需编辑定制, 不污染
包内原件。

零 veya 反向依赖: 运行用 subprocess 参数列表 (无 shell), 避免路径注入。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── 模板注册表 (id → 内置脚本文件名) ────────────────────────────────

FIGURE_TEMPLATES: dict[str, str] = {
    "multiclass-shap-combo": "make_multiclass_shap_combo.py",
    "paired-raincloud": "make_paired_raincloud.py",
    "cv-roc-ci": "make_cv_roc_ci.py",
    "taylor-diagram": "make_taylor_diagram.py",
    "correlation-pairgrid": "make_correlation_pairgrid.py",
    "prediction-marginal-grid": "make_prediction_marginal_grid.py",
    "rf-tpe-surface": "make_rf_tpe_surface.py",
    "grouped-corr-split-violin": "make_grouped_corr_split_violin.py",
    "grouped-circular-heatmap": "make_grouped_circular_heatmap.py",
    "urban-park-cooling-combo": "make_urban_park_cooling_combo.py",
    "nature-chord-diagram": "make_nature_chord_diagram.py",
}

ALIASES: dict[str, str] = {
    "shap": "multiclass-shap-combo",
    "multiclass-shap": "multiclass-shap-combo",
    "raincloud": "paired-raincloud",
    "roc": "cv-roc-ci",
    "cv-roc": "cv-roc-ci",
    "taylor": "taylor-diagram",
    "pairgrid": "correlation-pairgrid",
    "correlation": "correlation-pairgrid",
    "pred-true": "prediction-marginal-grid",
    "prediction": "prediction-marginal-grid",
    "surface": "rf-tpe-surface",
    "tpe": "rf-tpe-surface",
    "split-violin": "grouped-corr-split-violin",
    "circular-heatmap": "grouped-circular-heatmap",
    "urban-cooling": "urban-park-cooling-combo",
    "chord": "nature-chord-diagram",
    "circos": "nature-chord-diagram",
}

CJK_HINTS: dict[str, str] = {
    "多分类": "multiclass-shap-combo",
    "shap": "multiclass-shap-combo",
    "云雨": "paired-raincloud",
    "roc": "cv-roc-ci",
    "泰勒": "taylor-diagram",
    "相关矩阵组合": "correlation-pairgrid",
    "拟合线": "correlation-pairgrid",
    "预测": "prediction-marginal-grid",
    "真实": "prediction-marginal-grid",
    "tpe": "rf-tpe-surface",
    "曲面": "rf-tpe-surface",
    "半边小提琴": "grouped-corr-split-violin",
    "环形热图": "grouped-circular-heatmap",
    "城市公园": "urban-park-cooling-combo",
    "堆叠": "urban-park-cooling-combo",
    "和弦": "nature-chord-diagram",
    "circos": "nature-chord-diagram",
}

_TEMPLATES_DIR = Path(__file__).parent / "_figure_templates" / "templates"


def normalize(value: str) -> str:
    """规范化模板输入: 小写、下划线转连字符、非法字符折叠。"""
    value = value.strip().lower().replace("_", "-")
    value = re.sub(r"[^a-z0-9\-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def resolve_template(value: str) -> str:
    """将模板 id / 别名 / 中文关键词解析为规范 id。

    Args:
        value: 用户输入 (如 "paired-raincloud"、"raincloud"、"云雨图")。

    Returns:
        规范模板 id。

    Raises:
        ValueError: 无法解析的输入。

    Example:
        >>> resolve_template("云雨")
        'paired-raincloud'
    """
    raw = value.strip()
    key = normalize(raw)
    if key in FIGURE_TEMPLATES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    lowered = raw.lower()
    for hint, template_id in CJK_HINTS.items():
        if hint.lower() in lowered:
            return template_id
    raise ValueError(
        f"Unknown template: {value!r}. "
        f"Available ids: {', '.join(sorted(FIGURE_TEMPLATES))}"
    )


def list_figure_templates() -> list[str]:
    """列出全部模板 id (排序)。"""
    return sorted(FIGURE_TEMPLATES)


def render_figure_template(
    template: str,
    *,
    project_dir: str | Path = "绘图复刻",
    overwrite: bool = False,
    python: str | None = None,
) -> dict[str, Any]:
    """渲染一个科研绘图模板。

    流程: 解析模板 → 复制内置脚本到 <project>/scripts/ → 在项目目录执行 →
    写入 README 记录 → 返回输出路径。脚本与输出均在调用方工作区, 可再编辑。

    Args:
        template: 模板 id / 别名 / 中文关键词。
        project_dir: 输出项目目录, 默认 "绘图复刻" (相对当前目录)。
        overwrite: 已存在工作区脚本时是否覆盖。
        python: 执行脚本用的解释器, 默认 sys.executable。

    Returns:
        {ok, template_id, script, outputs, returncode, error}
        outputs 为 png/pdf/svg 三个产物路径 (执行成功时)。

    Raises:
        ValueError: 模板无法解析或内置脚本缺失。

    Example:
        >>> r = render_figure_template("raincloud", project_dir="/tmp/figs")
        >>> r["template_id"]
        'paired-raincloud'
    """
    template_id = resolve_template(template)
    filename = FIGURE_TEMPLATES[template_id]
    src = _TEMPLATES_DIR / filename
    if not src.exists():
        raise ValueError(f"Bundled script missing: {src}")

    project = Path(project_dir).expanduser().resolve()
    scripts_dir = project / "scripts"
    outputs_dir = project / "outputs"
    mpl_dir = project / ".mplconfig"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    mpl_dir.mkdir(parents=True, exist_ok=True)

    dst = scripts_dir / filename
    if dst.exists() and not overwrite:
        pass  # 复用已有工作区脚本
    else:
        shutil.copy2(src, dst)

    python_bin = python or sys.executable
    result = subprocess.run(
        [python_bin, str(dst)],
        cwd=str(project),
        check=False,
        capture_output=True,
        text=True,
    )

    outputs: list[str] = []
    if result.returncode == 0:
        stem = dst.stem.removeprefix("make_")
        for suffix in (".png", ".pdf", ".svg"):
            out = outputs_dir / f"{stem}_replica{suffix}"
            if out.exists():
                outputs.append(str(out))
        _write_readme(project, template_id, dst)

    return {
        "ok": result.returncode == 0,
        "template_id": template_id,
        "script": str(dst),
        "outputs": outputs,
        "returncode": result.returncode,
        "error": result.stderr[-500:] if result.returncode != 0 else None,
    }


def _write_readme(project: Path, template_id: str, script_path: Path) -> None:
    """在项目 README 追加该模板的生成记录 (幂等, 已存在则跳过)。"""
    readme = project / "README.md"
    output_stem = project / "outputs" / f"{script_path.stem.removeprefix('make_')}_replica"
    block = f"""
## {template_id}

Generated from the bundled oskill figure-template skill.

```bash
python3 {script_path.as_posix()}
```

Outputs:

- `{output_stem.with_suffix('.png').as_posix()}`
- `{output_stem.with_suffix('.pdf').as_posix()}`
- `{output_stem.with_suffix('.svg').as_posix()}`
""".strip()
    marker = f"## {template_id}"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if marker in text:
            return
        readme.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
    else:
        readme.write_text("# 绘图复刻\n\n" + block + "\n", encoding="utf-8")
