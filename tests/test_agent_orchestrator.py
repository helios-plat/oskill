"""Tests for agent_orchestrator (Dify Agent 三模式 3O 内化)。"""

from __future__ import annotations

import pytest

from oskill.agent_orchestrator import (
    MODE_FUNCTION_CALLING,
    MODE_PLAN,
    MODE_REACT,
    run_agent,
    run_function_calling,
    run_react,
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
]


# ── function-calling 模式 ───────────────────────────────────────────


def test_fc_loop_executes_and_returns():
    """模型先调用工具, 拿到结果后给出最终回答。"""
    llm_calls = []

    def fake_llm(messages, kwargs):
        llm_calls.append((messages, kwargs))
        tool_call_count = len([m for m in messages if m.get("role") == "tool"])
        if tool_call_count == 0:
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"city": "beijing"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"content": "北京晴 25 度"}}]}

    tool_results = []

    def fake_tool(name, args):
        tool_results.append((name, args))
        return {"city": "beijing", "temp": 25}

    result = run_function_calling(
        [{"role": "user", "content": "北京天气?"}],
        tools=_TOOLS,
        llm=fake_llm,
        tool_executor=fake_tool,
    )
    assert result.answer == "北京晴 25 度"
    assert result.tool_calls == [
        ("get_weather", {"city": "beijing"}, {"city": "beijing", "temp": 25})
    ]
    assert result.iterations == 2
    assert any(m.get("role") == "tool" for m in result.messages)


def test_fc_no_tool_calls_immediate():
    result = run_function_calling(
        [{"role": "user", "content": "hi"}],
        tools=_TOOLS,
        llm=lambda m, k: {"choices": [{"message": {"content": "你好"}}]},
        tool_executor=lambda n, a: None,
    )
    assert result.answer == "你好"
    assert result.iterations == 1


def test_fc_max_iterations():
    """模型一直返回 tool_calls → 轮次耗尽报错。"""

    def fake_llm(messages, kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "c",
                                "type": "function",
                                "function": {"name": "get_weather", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ]
        }

    result = run_function_calling(
        [{"role": "user", "content": "x"}],
        tools=_TOOLS,
        llm=fake_llm,
        tool_executor=lambda n, a: "r",
        max_iterations=3,
    )
    assert result.error is not None
    assert "max_iterations" in result.error
    assert result.iterations == 3


def test_fc_tool_error_does_not_crash():
    """工具执行抛异常 → 结果记为 error, 循环继续。"""

    def fake_llm(messages, kwargs):
        if not any(m.get("role") == "tool" for m in messages):
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c",
                                    "type": "function",
                                    "function": {"name": "get_weather", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"content": "done"}}]}

    def boom(name, args):
        raise RuntimeError("network down")

    result = run_function_calling(
        [{"role": "user", "content": "x"}],
        tools=_TOOLS,
        llm=fake_llm,
        tool_executor=boom,
    )
    assert result.error is None  # 工具错误不终止 agent
    assert "error" in str(result.tool_calls[0][2])


# ── react 模式 ──────────────────────────────────────────────────────


def test_react_loop():
    """Thought/Action/Action Input → Observation → 最终回答。"""
    llm_responses = iter(
        [
            'Thought: 需要天气.\nAction: get_weather\nAction Input: {"city": "sh"}',
            "Thought: 已拿到.\nAnswer: 上海晴。",
        ]
    )

    def fake_llm(messages, kwargs):
        return {"choices": [{"message": {"content": next(llm_responses)}}]}

    result = run_react(
        [{"role": "user", "content": "上海天气?"}],
        tools=_TOOLS,
        llm=fake_llm,
        tool_executor=lambda n, a: {"temp": 28},
        max_iterations=5,
    )
    assert "上海晴" in result.answer
    assert result.tool_calls[0][0] == "get_weather"
    assert result.mode == MODE_REACT


def test_react_no_action_direct_answer():
    result = run_react(
        [{"role": "user", "content": "hi"}],
        tools=_TOOLS,
        llm=lambda m, k: {"choices": [{"message": {"content": "Answer: 你好"}}]},
        tool_executor=lambda n, a: None,
    )
    assert "你好" in result.answer
    assert result.tool_calls == []


# ── plan 模式 ───────────────────────────────────────────────────────


def test_plan_mode():
    llm_responses = iter(
        [
            'Plan:\n1. 查天气\nAction: get_weather\nAction Input: {"city": "gz"}',
            "Answer: 广州晴。",
        ]
    )

    def fake_llm(messages, kwargs):
        return {"choices": [{"message": {"content": next(llm_responses)}}]}

    result = run_agent(
        [{"role": "user", "content": "广州天气?"}],
        tools=_TOOLS,
        mode=MODE_PLAN,
        llm=fake_llm,
        tool_executor=lambda n, a: {"temp": 30},
    )
    assert result.mode == MODE_PLAN
    assert "广州晴" in result.answer
    assert result.tool_calls


# ── 统一入口 ────────────────────────────────────────────────────────


def test_run_agent_invalid_mode():
    with pytest.raises(ValueError, match="unknown mode"):
        run_agent(
            [], tools=[], mode="telepathy", llm=lambda m, k: {}, tool_executor=lambda n, a: None
        )


def test_run_agent_function_calling_default():
    result = run_agent(
        [{"role": "user", "content": "hi"}],
        tools=[],
        llm=lambda m, k: {"choices": [{"message": {"content": "ok"}}]},
        tool_executor=lambda n, a: None,
    )
    assert result.answer == "ok"
    assert result.mode == MODE_FUNCTION_CALLING


def test_result_to_dict():
    result = run_agent(
        [{"role": "user", "content": "hi"}],
        tools=[],
        llm=lambda m, k: {"choices": [{"message": {"content": "ok"}}]},
        tool_executor=lambda n, a: None,
    )
    data = result.to_dict()
    assert data["answer"] == "ok"
    assert data["mode"] == MODE_FUNCTION_CALLING
