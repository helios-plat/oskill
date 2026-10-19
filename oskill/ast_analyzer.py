"""3O 范式全栈 — AST 分析技能 (纯计算, 无 IO, stateless)."""

from __future__ import annotations

import ast


def parse_imports(python_code: str) -> list[str]:
    """技能 15: AST 解析 (模拟 agent-skills)。

    提取顶层/嵌套 `import x` 语句的模块名 (不含 from-import)。
    """
    tree = ast.parse(python_code)
    return [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
