"""oskill.fn_call_adapter — 非函数调用 LLM 适配 (Auto-Deep-Research fn_call_converter 3O 内化)。

让不支持 function calling 的模型也能用于工具调用 agent:
  * **tools_to_prompt** — OpenAI tools → 文本描述 (AutoAgent 格式:
    BEGIN/END FUNCTION + 参数 (类型, 必选/可选) + 枚举);
  * **wrap_tools** — 注入 system prompt: 工具描述 + 输出格式指令
    (<function=name> + <parameter=k>v</parameter> + </function>);
  * **parse_function_tags** — 解析 <function=…>/<parameter=…> 标签;
  * **convert_to_tool_calls** — 标签 → OpenAI tool_calls 结构 (与
    rescue_tool_calls 互补: 那个处理 ```json 块, 这个处理 <function> 标签);
  * **is_function_call_output** — 判断模型输出是否为标签型函数调用。
与 model_routing 组合: 路由到不支持 function calling 的模型时自动适配。
零 veya 反向依赖: 纯文本解析 + 模板。
"""

from __future__ import annotations

import json
import re
from typing import Any

FN_REGEX = re.compile(r"<function=([^>]+)>\s*(.*?)</function>", re.DOTALL)
PARAM_REGEX = re.compile(r"<parameter=([^>]+)>(.*?)</parameter>", re.DOTALL)

# 输出格式指令 (AutoAgent SYSTEM_PROMPT_SUFFIX 内化)
_FORMAT_INSTRUCTION = """\n
If you choose to call a function ONLY reply in the following format with NO suffix:

<function=example_function_name>
<parameter=example_parameter_1>value_1</parameter>
<parameter=example_parameter_2>
This is the value for the second parameter
that can span
multiple lines
</parameter>
</function>

<IMPORTANT>
Reminder:
- Function calls MUST follow the specified format, start with <function= and end with </function>
- Required parameters MUST be specified
- Only call one function at a time
- If there is no function call available, answer the question normally
  with your current knowledge (do not mention function calls).
"""


# ── 1. tools → 文本描述 ──────────────────────────────────────────────


def tools_to_prompt(tools: list[dict[str, Any]]) -> str:
    """OpenAI tools → 文本描述 (供不支持 function calling 的模型读)。

    Args:
        tools: OpenAI 格式 tools (每个 {"type": "function", "function": {...}})。

    Returns:
        工具描述文本。

    Example:
        >>> "BEGIN FUNCTION #1" in tools_to_prompt(
        ...     [{"type": "function", "function": {"name": "f", "description": "d",
        ...       "parameters": {"type": "object", "properties": {"x": {"type": "string"}},
        ...                      "required": ["x"]}}}])
        True
    """
    ret: list[str] = []
    for i, tool in enumerate(tools):
        fn = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = fn.get("name", f"function_{i + 1}")
        ret.append(f"---- BEGIN FUNCTION #{i + 1}: {name} ----")
        ret.append(f"Description: {fn.get('description', '')}")
        parameters = fn.get("parameters", {})
        if parameters:
            ret.append("Parameters:")
            properties = parameters.get("properties", {})
            required = set(parameters.get("required", []))
            if not properties:
                ret.append("  No parameters are required for this function.")
            for j, (param_name, param_info) in enumerate(properties.items()):
                is_required = param_name in required
                status = "required" if is_required else "optional"
                param_type = param_info.get("type", "string")
                desc = param_info.get("description", "No description provided")
                if "enum" in param_info:
                    enum_values = ", ".join(f"`{v}`" for v in param_info["enum"])
                    desc += f"\nAllowed values: [{enum_values}]"
                ret.append(f"  ({j + 1}) {param_name} ({param_type}, {status}): {desc}")
        else:
            ret.append("No parameters are required for this function.")
        ret.append(f"---- END FUNCTION #{i + 1} ----")
    return "\n".join(ret)


# ── 2. 注入 system prompt ────────────────────────────────────────────


def wrap_tools(messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把工具描述 + 格式指令注入 system prompt (不动其他消息)。

    Args:
        messages: 原始消息列表。
        tools: OpenAI 格式 tools。

    Returns:
        新消息列表 (system 消息追加适配指令)。
    """
    description = tools_to_prompt(tools)
    suffix = f"\n\nAvailable functions:\n{description}\n{_FORMAT_INSTRUCTION}"
    converted: list[dict[str, Any]] = []
    for message in messages:
        message = dict(message)
        content = message.get("content")
        if message.get("role") == "system" and isinstance(content, str):
            message["content"] = content + suffix
        converted.append(message)
    return converted


# ── 3. 解析 <function> 标签 ──────────────────────────────────────────


def parse_function_tags(content: str) -> list[dict[str, Any]]:
    """解析 <function=name>…</function> 标签。

    Args:
        content: 模型输出文本。

    Returns:
        [{name, parameters}] 列表 (parameters 为 {参数名: 值字符串})。

    Example:
        >>> parse_function_tags('<function=f><parameter=x>1</parameter></function>')
        [{'name': 'f', 'parameters': {'x': '1'}}]
    """
    calls: list[dict[str, Any]] = []
    for match in FN_REGEX.finditer(content):
        name = match.group(1).strip()
        body = match.group(2)
        parameters: dict[str, str] = {}
        for param_match in PARAM_REGEX.finditer(body):
            parameters[param_match.group(1).strip()] = param_match.group(2).strip()
        calls.append({"name": name, "parameters": parameters})
    return calls


def is_function_call_output(content: str) -> bool:
    """模型输出是否含标签型函数调用。"""
    return bool(FN_REGEX.search(content or ""))


# ── 4. 标签 → OpenAI tool_calls ──────────────────────────────────────


def convert_to_tool_calls(content: str) -> list[dict[str, Any]] | None:
    """<function> 标签 → OpenAI tool_calls 结构。

    参数值尽量 JSON 解析 (合法 JSON 则结构化, 否则保持字符串)。

    Args:
        content: 模型输出。

    Returns:
        OpenAI 格式 tool_calls; 无标签返回 None。

    Example:
        >>> c = convert_to_tool_calls('<function=f><parameter=x>{"a": 1}</parameter></function>')
        >>> c[0]["function"]["name"]
        'f'
    """
    calls = parse_function_tags(content)
    if not calls:
        return None
    tool_calls: list[dict[str, Any]] = []
    for i, call in enumerate(calls):
        arguments: dict[str, Any] = {}
        for key, value in call["parameters"].items():
            try:
                arguments[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                arguments[key] = value
        tool_calls.append(
            {
                "id": f"call_adapted_{i}",
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        )
    return tool_calls


# ── 5. 与 model_routing 组合 ─────────────────────────────────────────

# 已知不支持 function calling 的 provider (适配开关参考)
NO_FUNCTION_CALLING_PROVIDERS: set[str] = set()


def mark_no_function_calling(provider: str) -> None:
    """标记某 provider 不支持 function calling (启用适配)。"""
    NO_FUNCTION_CALLING_PROVIDERS.add(provider)


def needs_adapter(provider: str) -> bool:
    """该 provider 是否需要函数调用适配。"""
    return provider in NO_FUNCTION_CALLING_PROVIDERS


def adapt_call(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    provider: str,
    llm_call: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """组合入口: 对不支持 function calling 的 provider 自动适配。

    流程: wrap_tools 注入提示 → 调用 LLM (无 tools 参数) → 若输出含
    <function> 标签则转换为 tool_calls。

    Args:
        messages: 消息。
        tools: OpenAI 工具。
        provider: provider id。
        llm_call: 注入的 LLM 调用函数 (messages 等 kwargs 透传)。
        **kwargs: 透传 llm_call (移除 tools)。

    Returns:
        OpenAI 格式响应 (含转换后的 tool_calls; 或纯文本回答)。
    """
    if not needs_adapter(provider):
        return llm_call(messages, tools=tools, **kwargs)
    adapted_messages = wrap_tools(messages, tools)
    kwargs.pop("tools", None)
    response = llm_call(adapted_messages, **kwargs)
    content = (response.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if isinstance(content, str) and is_function_call_output(content):
        tool_calls = convert_to_tool_calls(content)
        if tool_calls:
            response["choices"][0]["message"]["tool_calls"] = tool_calls
            response["_fn_call_adapter"] = True
    return response


__all__ = [
    "NO_FUNCTION_CALLING_PROVIDERS",
    "adapt_call",
    "convert_to_tool_calls",
    "is_function_call_output",
    "mark_no_function_calling",
    "needs_adapter",
    "parse_function_tags",
    "tools_to_prompt",
    "wrap_tools",
]
