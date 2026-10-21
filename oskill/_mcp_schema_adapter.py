"""oskill.mcp_schema_adapter — MCP Schema 转换.

JSON Schema ↔ MCP 工具 Schema（inputSchema camelCase 化）↔ OpenAI tools
格式的纯算法转换。stateless。

Example:
    >>> schema = {"type": "object", "properties": {"user_id": {"type": "string"}},
    ...           "required": ["user_id"]}
    >>> out = mcp_schema_adapter(schema)
    >>> out["properties"]["userId"]  # camelCase
    {'type': 'string'}
"""

from __future__ import annotations

import json
from typing import Any, Literal

from oskill._exceptions import OskillError

Direction = Literal["to_mcp", "to_python"]


def mcp_schema_adapter(
    schema: dict[str, Any],
    *,
    direction: Direction = "to_mcp",
) -> dict[str, Any]:
    """JSON Schema ↔ MCP Schema 互转。

    Args:
        schema: 输入 JSON Schema（object 类型）。
        direction:
            - "to_mcp": 属性名转 camelCase（MCP 线协议惯例），required 同步映射。
            - "to_python": 属性名转 snake_case（Python handler 惯例）。

    Returns:
        转换后的 schema dict。

    Raises:
        OskillError: schema 非法（非 object / 无 properties）。
    """
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise OskillError("mcp_schema_adapter: schema must be a JSON Schema object")
    props = schema.get("properties")
    if not isinstance(props, dict):
        raise OskillError("mcp_schema_adapter: schema.properties must be an object")

    converter = _to_camel if direction == "to_mcp" else _to_snake
    new_props: dict[str, Any] = {}
    for key, spec in props.items():
        new_props[converter(key)] = _convert_prop(spec, converter, depth=0)

    required = schema.get("required", [])
    new_required = [converter(r) for r in required] if required else []

    out: dict[str, Any] = {"type": "object", "properties": new_props}
    if new_required:
        out["required"] = new_required
    for extra in ("title", "description"):
        if extra in schema:
            out[extra] = schema[extra]
    return out


def to_openai_tools(schema: dict[str, Any], *, name: str, description: str) -> dict[str, Any]:
    """转 OpenAI tools 格式（function 壳）。"""
    if not name:
        raise OskillError("to_openai_tools: name must not be empty")
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": mcp_schema_adapter(schema, direction="to_mcp"),
        },
    }


def schema_to_json(schema: dict[str, Any], *, indent: int = 2) -> str:
    """schema 序列化为 JSON 字符串（供注册/调试）。"""
    return json.dumps(schema, ensure_ascii=False, indent=indent)


def _convert_prop(spec: Any, converter: Any, *, depth: int) -> Any:
    if depth > 6 or not isinstance(spec, dict):
        return spec
    out = dict(spec)
    if isinstance(spec.get("properties"), dict):
        out["properties"] = {
            converter(k): _convert_prop(v, converter, depth=depth + 1)
            for k, v in spec["properties"].items()
        }
    if isinstance(spec.get("items"), dict):
        out["items"] = _convert_prop(spec["items"], converter, depth=depth + 1)
    return out


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _to_snake(name: str) -> str:
    out = ""
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out += "_"
        out += ch.lower()
    return out
