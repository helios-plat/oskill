"""Tests for fn_call_adapter (Auto-Deep-Research 3O 内化)。"""

from __future__ import annotations

from oskill.fn_call_adapter import (
    adapt_call,
    convert_to_tool_calls,
    is_function_call_output,
    mark_no_function_calling,
    needs_adapter,
    parse_function_tags,
    tools_to_prompt,
    wrap_tools,
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                    "unit": {"type": "string", "enum": ["c", "f"]},
                },
                "required": ["city"],
            },
        },
    },
]


# ── tools → 提示词 ──────────────────────────────────────────────────


def test_tools_to_prompt():
    text = tools_to_prompt(_TOOLS)
    assert "BEGIN FUNCTION #1: get_weather" in text
    assert "查询城市天气" in text
    assert "(string, required): 城市名" in text
    assert "Allowed values: [`c`, `f`]" in text  # 枚举
    assert "END FUNCTION #1" in text


def test_tools_to_prompt_no_parameters():
    tools = [{"type": "function", "function": {"name": "noop", "description": "d"}}]
    assert "No parameters are required" in tools_to_prompt(tools)


# ── 注入 system prompt ──────────────────────────────────────────────


def test_wrap_tools_appends_to_system():
    messages = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "天气?"},
    ]
    wrapped = wrap_tools(messages, _TOOLS)
    assert "Available functions:" in wrapped[0]["content"]
    assert "get_weather" in wrapped[0]["content"]
    assert "<function=example_function_name>" in wrapped[0]["content"]  # 格式指令
    assert wrapped[1] == messages[1]  # 非 system 不动
    assert messages[0]["content"] == "你是助手"  # 原消息不变 (新列表)


# ── 标签解析 ────────────────────────────────────────────────────────


def test_parse_function_tags():
    content = "<function=get_weather>\n<parameter=city>beijing</parameter>\n</function>"
    calls = parse_function_tags(content)
    assert calls == [{"name": "get_weather", "parameters": {"city": "beijing"}}]


def test_parse_function_tags_multiline_value():
    content = (
        "<function=write_file>\n"
        "<parameter=path>/tmp/a.py</parameter>\n"
        "<parameter=content>\nline1\nline2\n</parameter>\n"
        "</function>"
    )
    calls = parse_function_tags(content)
    assert calls[0]["parameters"]["content"] == "line1\nline2"


def test_is_function_call_output():
    assert is_function_call_output("<function=f>\n</function>") is True
    assert is_function_call_output("普通回答") is False
    assert is_function_call_output("") is False


# ── 转换 ────────────────────────────────────────────────────────────


def test_convert_to_tool_calls_json_params():
    content = '<function=get_weather><parameter=city>{"name": "beijing"}</parameter></function>'
    calls = convert_to_tool_calls(content)
    assert calls is not None
    assert calls[0]["function"]["name"] == "get_weather"
    import json

    # 参数 city 的 JSON 值保持结构化
    assert json.loads(calls[0]["function"]["arguments"]) == {"city": {"name": "beijing"}}


def test_convert_to_tool_calls_string_params():
    content = "<function=f><parameter=x>plain value</parameter></function>"
    calls = convert_to_tool_calls(content)
    import json

    assert json.loads(calls[0]["function"]["arguments"]) == {"x": "plain value"}


def test_convert_returns_none_for_plain_text():
    assert convert_to_tool_calls("没有工具调用") is None


def test_convert_multi_function():
    content = (
        "<function=f1><parameter=a>1</parameter></function>\n"
        "<function=f2><parameter=b>2</parameter></function>"
    )
    calls = convert_to_tool_calls(content)
    assert [c["function"]["name"] for c in calls] == ["f1", "f2"]


# ── 与 model_routing 组合 ───────────────────────────────────────────


def test_needs_adapter_flag():
    mark_no_function_calling("llama-local")
    assert needs_adapter("llama-local") is True
    assert needs_adapter("openai") is False  # 默认不需适配


def test_adapt_call_no_adapter_needed():
    calls = []

    def fake_llm(messages, **kw):
        calls.append(kw)
        return {"choices": [{"message": {"content": "ok"}}]}

    result = adapt_call([{"role": "user", "content": "hi"}], _TOOLS, "openai", fake_llm)
    assert calls[0]["tools"] == _TOOLS  # 原样传 tools
    assert "_fn_call_adapter" not in result


def test_adapt_call_adapts_and_converts():
    calls = []

    def fake_llm(messages, **kw):
        calls.append(kw)
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<function=get_weather>"
                            "<parameter=city>beijing</parameter></function>"
                        )
                    }
                }
            ]
        }

    mark_no_function_calling("llama-local")
    received = {}

    def record_llm(messages, **kw):
        received["messages"] = messages
        received["kwargs"] = kw
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<function=get_weather>"
                            "<parameter=city>beijing</parameter></function>"
                        )
                    }
                }
            ]
        }

    result = adapt_call(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "hi"}],
        _TOOLS,
        "llama-local",
        record_llm,
    )
    assert "tools" not in received["kwargs"]  # 适配后不传 tools
    assert received["messages"][0]["content"].startswith("s")  # system 已注入
    assert "Available functions:" in received["messages"][0]["content"]
    assert result["_fn_call_adapter"] is True
    assert result["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_weather"


def test_adapt_call_plain_answer_no_tool_calls():
    def fake_llm(messages, **kw):
        return {"choices": [{"message": {"content": "我直接回答"}}]}

    mark_no_function_calling("llama-local")
    result = adapt_call([{"role": "user", "content": "hi"}], _TOOLS, "llama-local", fake_llm)
    assert "_fn_call_adapter" not in result
    assert "tool_calls" not in result["choices"][0]["message"]
