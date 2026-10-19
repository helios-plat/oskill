"""oskill.repomap_gen — 全局 Repomap 算法（Tree-sitter 符号索引 + 引用图）.

组合 oprim.ast_extract_symbols / obase.treesitter_indexer（注入的 indexer
Protocol），构建代码库全局符号索引与模块引用图。stateless：indexer 经参数
注入，不直接依赖任何具体实现。

Example:
    >>> m = await repomap_gen("/repo", indexer=my_indexer)
    >>> m["symbol_count"] >= 1
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class RepomapIndexer(Protocol):
    """符号索引器协议（obase.treesitter_indexer.SymbolIndexer 对齐）。"""

    async def index_file(self, path: str | Any) -> list[Any]: ...
    async def index_tree(self, root: str | Any, *, max_files: int = 500) -> Any: ...


async def repomap_gen(
    root: str,
    *,
    indexer: RepomapIndexer,
    max_files: int = 500,
    include_graph: bool = True,
) -> dict[str, Any]:
    """生成全局 Repomap。

    Args:
        root: 代码库根目录。
        indexer: 注入的符号索引器（TreesitterIndexer / AstFallbackIndexer）。
        max_files: 最大索引文件数。
        include_graph: 是否构建模块引用图（import 边）。

    Returns:
        {
            "root": str,
            "files": [str],
            "languages": {lang: count},
            "symbol_count": int,
            "symbols": [{"name", "kind", "path", "line", ...}],
            "symbol_index": {name: [paths]},   # 同名符号多文件定位
            "edges": [{"from": path, "to": path}],   # 模块引用边
            "orphan_modules": [path],
        }

    Raises:
        OskillError: root 非法 / indexer 未注入 / 索引失败。
    """
    if not root or not root.strip():
        raise OskillError("repomap_gen: root must not be empty")
    if indexer is None:
        raise OskillError("repomap_gen: indexer must be injected")

    try:
        index = await indexer.index_tree(root, max_files=max_files)
    except FileNotFoundError as exc:
        raise OskillError(f"repomap_gen: root not found: {root}") from exc
    except Exception as exc:
        raise OskillError(f"repomap_gen: indexing failed: {type(exc).__name__}: {exc}") from exc

    symbols = [s.to_dict() if hasattr(s, "to_dict") else s for s in index.symbols]

    # 符号索引：name -> [paths]
    symbol_index: dict[str, list[str]] = {}
    for s in symbols:
        symbol_index.setdefault(str(s.get("name", "")), []).append(str(s.get("path", "")))

    # 模块引用图：import 命中其他模块顶层符号 或 模块文件名 stem
    edges: list[dict[str, str]] = []
    if include_graph:
        modules: dict[str, set[str]] = {}
        for s in symbols:
            if s.get("kind") == "import":
                continue
            modules.setdefault(str(s["path"]), set()).add(str(s["name"]))
        module_stems = {_stem_of(p): p for p in index.files}
        import_names: dict[str, set[str]] = {}
        for s in symbols:
            if s.get("kind") == "import":
                import_names.setdefault(str(s["path"]), set()).add(str(s["name"]))
        for src_path, imports in import_names.items():
            for dst_path, top_symbols in modules.items():
                if src_path != dst_path and imports & top_symbols:
                    edges.append({"from": src_path, "to": dst_path})
            for imp in imports:
                # import b → b.py / b/__init__.py 模块级引用
                if imp in module_stems and module_stems[imp] != src_path:
                    edge = {"from": src_path, "to": module_stems[imp]}
                    if edge not in edges:
                        edges.append(edge)

    referenced = {e["to"] for e in edges}
    orphans = sorted(p for p in index.files if p not in referenced and _py_of(p))

    return {
        "root": index.root,
        "files": list(index.files),
        "languages": dict(index.languages),
        "symbol_count": index.symbol_count,
        "symbols": symbols,
        "symbol_index": symbol_index,
        "edges": edges,
        "orphan_modules": orphans,
    }


def _py_of(path: str) -> bool:
    return path.endswith(".py") or path.endswith(".pyi")


def _stem_of(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    return base.split(".")[0]
