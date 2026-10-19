"""oskill.edge_confidence — 代码图边的置信标签 (graphify EXTRACTED/INFERRED 内化)。Pure.

确定性代码图 (parse_code) 的调用边靠**符号名**跨文件解析。名字唯一时解析可信;
名字在多个模块重名时, "谁调用了 X / X 调用了谁"可能张冠李戴 (跨文件误连)。据此给边
打置信标签, 让上层 (graft 上下文装配) 把低置信边标注出来, 不当成铁的事实喂主脑:

  * ``EXTRACTED`` — 目标名在工作区**唯一定义**, 边可信;
  * ``INFERRED``  — 目标名**多处定义** (重名歧义) 或**未在工作区定义** (外部/未解析)。

纯函数, 无 I/O。graft 侧只需先建 name→定义模块集 的索引, 再逐边查询。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

EXTRACTED = "EXTRACTED"
INFERRED = "INFERRED"


def build_definition_index(symbols_by_module: Mapping[str, Iterable[str]]) -> dict[str, set[str]]:
    """symbols_by_module: {module: [定义的符号名, …]} → {符号名: {定义它的模块集}}。"""
    index: dict[str, set[str]] = {}
    for module, names in (symbols_by_module or {}).items():
        for name in names or ():
            key = str(name).strip()
            if key:
                index.setdefault(key, set()).add(str(module))
    return index


def edge_confidence(name: str, def_index: Mapping[str, set[str]]) -> str:
    """单条边目标名的置信: 唯一定义 → EXTRACTED; 多处/未定义 → INFERRED。"""
    modules = def_index.get(str(name).strip()) or set()
    return EXTRACTED if len(modules) == 1 else INFERRED


def annotate_edges(
    names: Iterable[str], def_index: Mapping[str, set[str]]
) -> list[tuple[str, str]]:
    """给一组边目标名批量打标签 → [(name, EXTRACTED|INFERRED), …] (保序去空)。"""
    out: list[tuple[str, str]] = []
    for name in names or ():
        key = str(name).strip()
        if key:
            out.append((key, edge_confidence(key, def_index)))
    return out


def is_low_confidence(name: str, def_index: Mapping[str, set[str]]) -> bool:
    """便捷判定: 该边是否低置信 (INFERRED)。"""
    return edge_confidence(name, def_index) == INFERRED
