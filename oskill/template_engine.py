"""oskill.template_engine — Prompt 变量注入引擎 (Dify 机制 3O 内化)。

把 {{variable}} 模板渲染通用化 (veya officecli render_template 的增强版):
  * **渲染** — {{var}} 替换 (支持嵌套 dict 访问 a.b.c 与数组索引 a[0]);
  * **校验** — 必填变量缺失检测, 未使用变量警告;
  * **默认值** — {{var|default}} 语法, 缺失用默认;
  * **转义** — 可选 {{var!e}} 对注入值做 shell/JSON 转义 (防注入)。

零 veya 反向依赖: 纯模板渲染。
"""

from __future__ import annotations

import json
import re
from typing import Any

_VAR_RE = re.compile(r"\{\{\s*([\w.\[\]|!]+?)\s*\}\}")


def _resolve(value: Any, path: str) -> Any:
    """按 a.b.c / a[0] 路径取嵌套值。"""
    for part in path.replace("]", "").split("."):
        if part == "":
            continue
        if "[" in part:
            key, index = part.split("[", 1)
            if key:
                value = value[key] if isinstance(value, dict) else {}
            value = value[int(index)] if isinstance(value, list) else None
        else:
            value = value.get(part) if isinstance(value, dict) else None
        if value is None:
            break
    return value


def render_template(
    template: str,
    variables: dict[str, Any],
    *,
    required: list[str] | None = None,
    escape: str | None = None,
) -> dict[str, Any]:
    """渲染 {{variable}} 模板。

    Args:
        template: 模板文本。
        variables: 变量字典。
        required: 必填变量 (缺失报 missing)。
        escape: 可选转义模式: "json" / "shell" / None。

    Returns:
        {rendered, missing, unused} — rendered 为渲染后文本。

    Example:
        >>> render_template("Hello {{name}}", {"name": "veya"})["rendered"]
        'Hello veya'
    """
    missing: list[str] = []
    used: set[str] = set()

    def replace(match: re.Match) -> str:
        expr = match.group(1)
        parts = expr.split("|")
        path = parts[0].strip()
        default = parts[1] if len(parts) > 1 else ""
        escaped = expr.endswith("!e")
        if escaped:
            path = path[:-2].strip()
        base = path.split(".")[0].split("[")[0]
        used.add(base)
        value = _resolve(variables, path)
        if value is None and default:
            value = default
        if value is None:
            missing.append(path)
            return ""
        text = str(value)
        if escaped or escape == "json":
            text = json.dumps(text, ensure_ascii=False)[1:-1]
        elif escape == "shell":
            text = text.replace("'", "'\\''")
        return text

    rendered = _VAR_RE.sub(replace, template)
    unused = [k for k in (required or []) if k not in used]
    return {"rendered": rendered, "missing": missing, "unused": unused}


def extract_variables(template: str) -> list[str]:
    """提取模板中的变量名 (去重保序)。"""
    seen: list[str] = []
    for match in _VAR_RE.finditer(template):
        path = match.group(1).split("|")[0].strip().rstrip("!").strip()
        base = path.split(".")[0].split("[")[0]
        if base not in seen:
            seen.append(base)
    return seen


__all__ = ["extract_variables", "render_template"]
