"""oskill.code_symbol_investigate — 多文件代码符号依赖图构建与深度分析技能.

组合 oprim.ast_parse_code（符号提取）+ oprim.file_read_slice（截断读取），
构建跨文件符号引用图并给出调用链分析。stateless，路径列表由调用方注入。

Example:
    >>> g = await code_symbol_investigate(["/repo/app.py", "/repo/util.py"])
    >>> "app.py" in g["modules"]
    True
"""

from __future__ import annotations

from typing import Any

from oprim import ast_parse_code, file_read_slice

from oskill._exceptions import OskillError


async def code_symbol_investigate(
    file_paths: list[str],
    *,
    max_lines_per_file: int = 2000,
    include_imports: bool = True,
) -> dict[str, Any]:
    """解析多文件符号并构建依赖图。

    Args:
        file_paths: 待分析文件路径列表（≥1）。
        max_lines_per_file: 单文件截断读取行数上限。
        include_imports: 是否纳入 import 边。

    Returns:
        {
            "modules": {path: {"functions": [...], "classes": [...], "imports": [...]}},
            "edges": [{"from": path, "symbol": str, "to": path}],
            "total_symbols": int,
            "orphan_symbols": [str],
        }

    Raises:
        OskillError: file_paths 为空或全部文件不可解析。
    """
    if not file_paths:
        raise OskillError("code_symbol_investigate: file_paths must not be empty")


    modules: dict[str, dict[str, Any]] = {}
    symbols_by_module: dict[str, set[str]] = {}
    errors: list[str] = []

    for path in file_paths:
        try:
            await file_read_slice(path, max_lines=max_lines_per_file)
        except Exception as exc:  # noqa: BLE001 - 单文件失败不致命
            errors.append(f"{path}: {type(exc).__name__}")
            continue
        try:
            parsed = await ast_parse_code(path, include_imports=include_imports)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            continue

        fns = {f["name"] for f in parsed["functions"]}
        cls = {c["name"] for c in parsed["classes"]}
        modules[path] = parsed
        symbols_by_module[path] = fns | cls

    if not modules:
        raise OskillError(f"code_symbol_investigate: no parseable files (errors: {errors[:3]})")

    # 依赖边：模块 A 的 import 名在模块 B 的符号集中 → A → B
    edges: list[dict[str, Any]] = []
    for path, parsed in modules.items():
        imported_names: set[str] = set()
        for imp in parsed.get("imports", []):
            imported_names.update(imp.get("names", []))
            if imp.get("module"):
                imported_names.add(imp["module"].split(".")[-1])
        for other, other_symbols in symbols_by_module.items():
            if other == path:
                continue
            hit = imported_names & other_symbols
            for symbol in sorted(hit):
                edges.append({"from": path, "symbol": symbol, "to": other})

    total = sum(m.get("symbols", 0) for m in modules.values())
    all_symbols: set[str] = set()
    for s in symbols_by_module.values():
        all_symbols |= s
    referenced: set[str] = {e["symbol"] for e in edges}
    orphans = sorted(all_symbols - referenced)

    return {
        "modules": modules,
        "edges": edges,
        "total_symbols": total,
        "orphan_symbols": orphans,
        "errors": errors,
    }
