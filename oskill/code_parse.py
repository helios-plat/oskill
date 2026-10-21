"""oskill.code_parse — 代码解析管线 (Graft/Graphify tree-sitter 机制 3O 内化)。

把"代码符号/调用关系"解析做成确定性机制 (tree-sitter 语义, 纯 Python 实现):
  * **parse_python_tree** — 用标准库 ast 精确解析 Python 代码: 符号
    (函数/类/方法) + import 依赖 + 调用边;
  * **CodeSymbol** — 符号 (name/kind/line/module);
  * **CallEdge** — 调用关系 (caller → callee);
  * 与其他语言: 简化行级符号提取 (fallback)。
与 code_graph_semantic 组合: 符号边 → SemanticNode 来源证据。

零 veya 反向依赖: 标准库 ast (Python 精确) + 正则 (其他语言 fallback)。
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SYMBOL_FUNCTION = "function"
SYMBOL_CLASS = "class"
SYMBOL_METHOD = "method"
SYMBOL_IMPORT = "import"


@dataclass(frozen=True)
class CodeSymbol:
    """一个代码符号。

    Attributes:
        name: 符号名。
        kind: function/class/method/import。
        line: 定义行。
        module: 所属文件 (相对路径)。
    """

    name: str
    kind: str
    line: int
    module: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "line": self.line, "module": self.module}


@dataclass(frozen=True)
class CallEdge:
    """一条调用边。

    Attributes:
        caller: 调用方符号。
        callee: 被调用符号。
        line: 调用行。
    """

    caller: str
    callee: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {"caller": self.caller, "callee": self.callee, "line": self.line}


@dataclass
class CodeTree:
    """解析出的代码树 (符号 + 调用边 + 依赖)。"""

    module: str
    symbols: list[CodeSymbol] = field(default_factory=list)
    calls: list[CallEdge] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    def symbol_names(self, kind: str | None = None) -> list[str]:
        if kind is None:
            return [s.name for s in self.symbols]
        return [s.name for s in self.symbols if s.kind == kind]

    def callers_of(self, callee: str) -> list[str]:
        """调用某符号的调用方 (impact analysis 基础)。"""
        return [e.caller for e in self.calls if e.callee == callee]

    def callees_of(self, caller: str) -> list[str]:
        """某符号调用的被调用方。"""
        return [e.callee for e in self.calls if e.caller == caller]

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "symbols": [s.to_dict() for s in self.symbols],
            "calls": [e.to_dict() for e in self.calls],
            "imports": self.imports,
        }


# ── Python 精确解析 (标准库 ast) ───────────────────────────────────


def parse_python_tree(source: str | Path, *, module: str = "") -> CodeTree:
    """解析 Python 代码: 符号 + import + 调用边 (标准库 ast)。

    Args:
        source: 代码文本或文件路径。
        module: 模块名 (相对路径, 用于符号归属)。

    Returns:
        CodeTree。

    Example:
        >>> tree = parse_python_tree("def f():\n    g()\n", module="a.py")
        >>> tree.symbols[0].name
        'f'
    """
    if isinstance(source, Path) or (
        isinstance(source, str) and "\n" not in source and Path(source).exists()
    ):
        path = Path(source)
        module = module or str(path)
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return CodeTree(module=module)  # 语法错误 → 空树 (调用方处理)

    code_tree = CodeTree(module=module)
    _walk_python(tree, code_tree, in_class=False, current_fn=None)
    return code_tree


def _walk_python(
    node: ast.AST,
    tree: CodeTree,
    *,
    in_class: bool,
    current_fn: str | None,
) -> None:
    """按源码顺序遍历 AST, 维护函数/类上下文 (替代 ast.walk 无序遍历)。"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = SYMBOL_METHOD if in_class else SYMBOL_FUNCTION
            tree.symbols.append(CodeSymbol(child.name, kind, child.lineno or 0, tree.module))
            _walk_python(child, tree, in_class=in_class, current_fn=child.name)
        elif isinstance(child, ast.ClassDef):
            tree.symbols.append(
                CodeSymbol(child.name, SYMBOL_CLASS, child.lineno or 0, tree.module)
            )
            _walk_python(child, tree, in_class=True, current_fn=current_fn)
        elif isinstance(child, ast.Import):
            for alias in child.names:
                tree.imports.append(alias.name.split(".")[0])
        elif isinstance(child, ast.ImportFrom):
            if child.module:
                tree.imports.append(child.module.split(".")[0])
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            if current_fn:
                tree.calls.append(CallEdge(current_fn, child.func.id, child.lineno or 0))
            _walk_python(child, tree, in_class=in_class, current_fn=current_fn)
        else:
            _walk_python(child, tree, in_class=in_class, current_fn=current_fn)


# ── 其他语言 fallback (行级符号提取) ────────────────────────────────

_FN_PATTERNS = {
    ".py": r"^\s*(?:async\s+)?def\s+(\w+)\s*\(",
    ".js": r"^\s*(?:export\s+(?:default\s+)?)?(?:function\s+(\w+)|"
    r"const\s+(\w+)\s*=\s*(?:async\s*)?\(|class\s+(\w+))",
    ".ts": r"^\s*(?:export\s+(?:default\s+)?)?(?:function\s+(\w+)|"
    r"const\s+(\w+)\s*=\s*(?:async\s*)?\(|class\s+(\w+))",
    ".go": r"^\s*(?:func\s+(\w+)|type\s+(\w+)\s+struct)",
    ".rs": r"^\s*(?:fn\s+(\w+)|struct\s+(\w+)|enum\s+(\w+))",
}


def parse_generic_tree(source: str | Path, *, module: str = "", ext: str | None = None) -> CodeTree:
    """其他语言行级符号提取 (fallback, 不如 ast 精确但够导向)。"""
    if isinstance(source, Path) or (
        isinstance(source, str) and "\n" not in source and Path(source).exists()
    ):
        path = Path(source)
        module = module or str(path)
        ext = ext or path.suffix
        text = path.read_text(encoding="utf-8")
    else:
        text = str(source)
    code_tree = CodeTree(module=module)
    pattern = _FN_PATTERNS.get(ext or "", "")
    if not pattern:
        return code_tree
    regex = re.compile(pattern)
    for i, line in enumerate(text.splitlines(), start=1):
        match = regex.search(line)
        if match:
            name = next((g for g in match.groups() if g), "unknown")
            code_tree.symbols.append(CodeSymbol(name, SYMBOL_FUNCTION, i, module))
    return code_tree


def parse_code(source: str | Path, *, module: str = "", ext: str | None = None) -> CodeTree:
    """统一入口: Python 用 ast 精确解析, 其他语言 fallback。"""
    if ext is None:
        ext = Path(module).suffix if module else ".py"
    if ext == ".py":
        return parse_python_tree(source, module=module)
    return parse_generic_tree(source, module=module, ext=ext)


__all__ = [
    "CallEdge",
    "CodeSymbol",
    "CodeTree",
    "SYMBOL_CLASS",
    "SYMBOL_FUNCTION",
    "SYMBOL_IMPORT",
    "SYMBOL_METHOD",
    "parse_code",
    "parse_generic_tree",
    "parse_python_tree",
]
