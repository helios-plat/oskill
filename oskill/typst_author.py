"""oskill.typst_author — Typst 文档撰写技能 (typst-author SKILL 3O 内化)。

机制: minimal doc 生成 → typstyle 格式化检查 (check→diff→apply) → typst compile
验证 → 无文件 probe 探针 (stdin + typst query)。附 TYPST_GUIDE 结构化知识包
(关键区分 / # 用法 / set vs show / 常见错误 / 排障)。

零 veya 反向依赖: typst / typstyle 命令由装配层提供; 命令缺失时返回结构化
结果而非抛异常, 由调用方决定降级策略。subprocess 统一走 oprim.bash_exec。
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from oprim._bash_exec import bash_exec

# ── 结构化知识包 (typst-author SKILL 要点) ──────────────────────────

TYPST_GUIDE: dict[str, Any] = {
    "critical_distinctions": {
        "array": "(item1, item2) — 圆括号",
        "dictionary": "(key: value, key2: value2) — 圆括号带冒号",
        "content_block": "[markup content] — 方括号",
        "tuple": "不存在! Typst 只有 array",
    },
    "hash_usage": {
        "markup": "正文/内容块中用 # 开始代码表达式: #figure[...], #image(\"x.png\")",
        "code_context": "代码上下文内不要加 #: figure(image(\"x.png\"))",
        "example_bad": "text(...)[(numbering(...))]  # 缺 #",
        "example_good": "text(...)[(#numbering(...))]",
    },
    "styling": {
        "set": "set rule 配置元素函数的可选参数 (作用域为当前块/文件)",
        "show": "show rule 选中元素后应用 set 或变换/替换输出",
        "show_set": "#show heading: set text(navy)  # 只对选中元素生效",
    },
    "common_mistakes": [
        "把 array 叫成 tuple (Typst 只有 array)",
        "用 [] 表示数组 (应该用 ())",
        "用 arr[0] 取元素 (应该用 arr.at(0))",
        "内容块中漏 # (text(...)[numbering(...)] 应为 text(...)[#numbering(...)])",
        "代码上下文里多加 # (figure(#image(\"x.png\")))",
        "混淆内容块 [] 与代码块 {}",
        "忘记命名空间 (用 color.hsl 而不是 hsl)",
        "混用 LaTeX 语法 (\\begin{...} / \\section 都不存在)",
        "幻觉环境 (tabular 不存在, 用 table)",
    ],
    "troubleshooting": {
        "unknown_font": "字体警告不阻止编译, 移除字体设置即回退系统字体",
        "package_not_found": "核对 Typst Universe 包名/版本, 检查 @preview/package:version 拼写",
        "expected_content": "代码出现在 markup 处 — 用 #{ } 包裹或改用正确语法",
        "expected_expression": "markup/内容块中漏 # (或 #(...))",
        "unknown_variable": "检查拼写与 import 是否正确",
    },
}

# ── 工具函数 ────────────────────────────────────────────────────────


def _have(bin_name: str) -> bool:
    """探测命令是否存在 (不抛异常)。"""
    result = bash_exec(f"command -v {shlex.quote(bin_name)}")
    return result.ok and bool(result.stdout.strip())


def typst_minimal_doc(
    *,
    title: str = "My Document",
    author: str = "Author Name",
    lang: str = "en",
) -> str:
    """生成 Typst 最小可用文档 (typst-author SKILL minimal document example)。

    Args:
        title: 文档标题。
        author: 作者名。
        lang: 文档语言 (en / zh 等)。

    Returns:
        可直接写入 .typ 文件的完整文档源码。

    Example:
        >>> src = typst_minimal_doc(title="论文", lang="zh")
        >>> '#set document(title: "论文")' in src
        True
    """
    return f'''#set document(title: "{title}", author: "{author}")
#set page(numbering: "1")
#set text(lang: "{lang}")

// Enable paragraph justification and character-level justification
#set par(
  justify: true,
  justification-limits: (
    tracking: (min: -0.012em, max: 0.012em),
    spacing: (min: 75%, max: 120%),
  )
)

#title[{title}]

= Heading 1

This is a paragraph in Typst.

== Heading 2

#lorem(50)
'''


def typst_format_check(path: str | Path, *, apply: bool = False) -> dict[str, Any]:
    """Typstyle 格式化检查循环 (typst-author SKILL post-edit formatting checks)。

    顺序: typstyle --check → 失败时 --diff 查看改动 → apply=True 且改动受限时
    typstyle -i 应用。typstyle 缺失时返回 available=False, 不抛异常。

    Args:
        path: .typ 文件路径。
        apply: True 时对 check 失败的文件执行 typstyle -i。

    Returns:
        {available, formatted, diff, applied, messages, check, diff_result, apply_result}
    """
    file_path = str(Path(path))
    messages: list[str] = []
    if not _have("typstyle"):
        return {
            "available": False,
            "formatted": False,
            "diff": "",
            "applied": False,
            "messages": ["typstyle 不可用, 跳过格式化检查"],
        }
    check = bash_exec(f"typstyle --check {shlex.quote(file_path)}")
    formatted = check.ok
    diff_text = ""
    diff_result: dict[str, Any] | None = None
    applied = False
    apply_result: dict[str, Any] | None = None
    if not formatted:
        diff_result = {
            "code": None,
            "stdout": "",
            "stderr": "",
        }
        diff = bash_exec(f"typstyle --diff {shlex.quote(file_path)}")
        diff_text = diff.stdout
        diff_result = {"code": diff.code, "stdout": diff.stdout, "stderr": diff.stderr}
        messages.append("typstyle --check 失败, 见 diff")
        if apply:
            applied_result = bash_exec(f"typstyle -i {shlex.quote(file_path)}")
            applied = applied_result.ok
            apply_result = {
                "code": applied_result.code,
                "stdout": applied_result.stdout,
                "stderr": applied_result.stderr,
            }
            messages.append("已执行 typstyle -i" if applied else "typstyle -i 失败")
    else:
        messages.append("格式已符合 typstyle")
    return {
        "available": True,
        "formatted": formatted,
        "diff": diff_text,
        "applied": applied,
        "messages": messages,
        "check": {"code": check.code, "stdout": check.stdout, "stderr": check.stderr},
        "diff_result": diff_result,
        "apply_result": apply_result,
    }


def typst_probe(expr: str, *, label: str = "probe") -> dict[str, Any]:
    """无文件 probe: 用 stdin 求值 Typst 表达式并读取结果。

    typst-author SKILL probing 流程: 用 `metadata(...) <label>` 暴露值, 再
    `typst query - "<label>" --field value --one` 读取。不产生临时 .typ 文件。

    Args:
        expr: 要求值的 Typst 代码表达式, 如 "1 + 2"。
        label: metadata 标签, 默认 "probe"。

    Returns:
        {available, value, code, stdout, stderr}
    """
    probe_src = f"#metadata({expr}) <{label}>"
    cmd = (
        f"printf '%s\\n' {shlex.quote(probe_src)} "
        f"| typst query - {shlex.quote(label)} --field value --one"
    )
    if not _have("typst"):
        return {"available": False, "value": None, "code": None, "stdout": "", "stderr": ""}
    result = bash_exec(cmd)
    value = result.stdout.strip() or None
    return {
        "available": True,
        "value": value,
        "code": result.code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def typst_compile(path: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    """编译 .typ 文件验证 (typst compile)。

    Args:
        path: .typ 文件路径。
        root: 可选 --root 参数 (多文件项目根目录)。

    Returns:
        {available, ok, code, stdout, stderr, pdf}
    """
    file_path = Path(path)
    if not _have("typst"):
        return {
            "available": False,
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": "",
            "pdf": None,
        }
    cmd = f"typst compile {shlex.quote(str(file_path))}"
    if root is not None:
        cmd += f" --root {shlex.quote(str(root))}"
    result = bash_exec(cmd, timeout=300)
    pdf = None
    if result.ok:
        pdf_path = file_path.with_suffix(".pdf")
        pdf = str(pdf_path) if pdf_path.exists() else None
    return {
        "available": True,
        "ok": result.ok,
        "code": result.code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pdf": pdf,
    }
