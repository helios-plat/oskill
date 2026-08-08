"""oskill.agent_orchestrator — Agent 三模式编排 (Dify agent runner 3O 内化)。

通用 agent 工具循环编排器, 三种模式:
  * **function-calling** — LLM 输出 tool_calls → 执行 → 结果回填 → 循环
    直到无工具调用 (Dify fc_agent_runner, max_iteration 防死循环);
  * **react** — Thought/Action/Action Input/Observation 循环 (CoT, 适用
    不支持原生工具调用的模型; 与 fn_call_adapter 组合);
  * **plan** — 先生成计划 → 逐步执行 → 汇总 (计划器模式)。
统一 AgentResult (最终回答/工具轨迹/迭代数/错误), LLM 与工具执行注入。
零 veya 反向依赖: 纯编排; llm/tool_executor 由调用方注入。
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

MODE_FUNCTION_CALLING = "function-calling"
MODE_REACT = "react"
MODE_PLAN = "plan"
MODES = (MODE_FUNCTION_CALLING, MODE_REACT, MODE_PLAN)

DEFAULT_MAX_ITERATIONS = 10

LlmFn = Callable[[list[dict[str, Any]], dict[str, Any]], dict[str, Any]]
"""LLM 调用: (messages, kwargs) → OpenAI 格式响应。"""

ToolExecutor = Callable[[str, dict[str, Any]], Any]
"""工具执行: (name, arguments) → 结果 (任意可序列化)。"""


def _json_trunc(value: Any, limit: int = 8000) -> str:
    """JSON 序列化 + 截断 (工具结果回填, 防上下文溢出)。"""
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:limit]


def _content_of(response: dict[str, Any]) -> str:
    message = (response.get("choices") or [{}])[0].get("message", {})
    content = message.get("content", "")
    return content if isinstance(content, str) else ""


def _extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    """从 LLM 响应提取 tool_calls (含 fn_call_adapter 转换结果)。"""
    message = (response.get("choices") or [{}])[0].get("message", {})
    return message.get("tool_calls", []) or []


@dataclass
class AgentResult:
    """一次 agent 运行的完整结果。

    Attributes:
        answer: 最终回答文本。
        messages: 完整消息轨迹 (含工具调用/结果回填)。
        tool_calls: 工具调用轨迹 [(name, arguments, result)]。
        iterations: 迭代轮数。
        error: 错误信息 (None 正常)。
        mode: 使用的模式。
    """

    answer: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[tuple[str, dict[str, Any], Any]] = field(default_factory=list)
    iterations: int = 0
    error: str | None = None
    mode: str = MODE_FUNCTION_CALLING

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "tool_calls": self.tool_calls,
            "iterations": self.iterations,
            "error": self.error,
            "mode": self.mode,
        }


# ── function-calling 模式 ────────────────────────────────────────────


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def run_function_calling(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    llm: LlmFn,
    tool_executor: ToolExecutor,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> AgentResult:
    """function-calling 模式: 工具调用循环。

    Args:
        messages: 初始消息。
        tools: OpenAI 格式工具。
        llm: LLM 调用 (返回 OpenAI 格式, 含 tool_calls)。
        tool_executor: 工具执行。
        max_iterations: 最大迭代 (防死循环)。

    Returns:
        AgentResult。
    """
    history = list(messages)
    tool_trail: list[tuple[str, dict[str, Any], Any]] = []
    for iteration in range(max_iterations):
        response = llm(history, {"tools": tools})
        content = _content_of(response)
        tool_calls = _extract_tool_calls(response)
        if not tool_calls:
            answer = content
            history.append({"role": "assistant", "content": answer})
            return AgentResult(
                answer=str(answer),
                messages=history,
                tool_calls=tool_trail,
                iterations=iteration + 1,
                mode=MODE_FUNCTION_CALLING,
            )
        history.append({"role": "assistant", "content": content or None, "tool_calls": tool_calls})
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = _parse_arguments(fn.get("arguments", "{}"))
            try:
                result = tool_executor(name, args)
            except Exception as exc:  # noqa: BLE001
                result = {"error": f"{exc.__class__.__name__}: {exc}"}
            tool_trail.append((name, args, result))
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", f"call_{iteration}"),
                    "content": _json_trunc(result),
                }
            )
    return AgentResult(
        answer="",
        messages=history,
        tool_calls=tool_trail,
        iterations=max_iterations,
        error=f"max_iterations 耗尽 ({max_iterations})",
        mode=MODE_FUNCTION_CALLING,
    )


# ── react 模式 (Thought/Action/Observation) ─────────────────────────

_REACT_SYSTEM = """You operate in a loop of Thought / Action / Action Input / Observation.

- Thought: your reasoning about the current state.
- Action: the tool name to use (one of: {tools}).
- Action Input: JSON arguments for the tool.
- Observation: the tool result (provided to you).

End the loop with a final Answer when the task is complete.
"""

_ACTION_RE = re.compile(
    r"Thought:\s*(.*?)\s*Action:\s*(\w+)\s*Action Input:\s*(\{.*?\})",
    re.DOTALL,
)


def run_react(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    llm: LlmFn,
    tool_executor: ToolExecutor,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> AgentResult:
    """react (CoT) 模式: Thought/Action/Action Input/Observation 循环。

    Args:
        messages: 初始消息。
        tools: 工具 (名称注入提示)。
        llm: LLM 调用 (无 tools 参数, 文本输出)。
        tool_executor: 工具执行。
        max_iterations: 最大迭代。

    Returns:
        AgentResult。
    """
    tool_names = ", ".join(t.get("function", {}).get("name", "") for t in tools)
    history = [
        {"role": "system", "content": _REACT_SYSTEM.format(tools=tool_names or "(none)")},
        *messages,
    ]
    tool_trail: list[tuple[str, dict[str, Any], Any]] = []
    for iteration in range(max_iterations):
        response = llm(history, {})
        content = _content_of(response)
        history.append({"role": "assistant", "content": content})
        match = _ACTION_RE.search(content)
        if not match:
            return AgentResult(
                answer=content.strip(),
                messages=history,
                tool_calls=tool_trail,
                iterations=iteration + 1,
                mode=MODE_REACT,
            )
        action_name = match.group(2)
        args = _parse_arguments(match.group(3))
        try:
            result = tool_executor(action_name, args)
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{exc.__class__.__name__}: {exc}"}
        tool_trail.append((action_name, args, result))
        history.append(
            {
                "role": "user",
                "content": f"Observation: {_json_trunc(result)}",
            }
        )
    return AgentResult(
        answer="",
        messages=history,
        tool_calls=tool_trail,
        iterations=max_iterations,
        error=f"max_iterations 耗尽 ({max_iterations})",
        mode=MODE_REACT,
    )


# ── plan 模式 (计划器) ──────────────────────────────────────────────

_PLAN_SYSTEM = """You are a planner. First produce a numbered plan of steps to
complete the task. Then execute each step; after each tool result, continue to
the next step. When all steps are done, give a final Answer.
Tools available: {tools}
"""

# plan 模式宽松 Action 解析 (无 Thought 前缀要求)
_PLAN_ACTION_RE = re.compile(
    r"Action:\s*(\w+)\s*Action Input:\s*(\{.*?\})",
    re.DOTALL,
)


def run_plan(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    llm: LlmFn,
    tool_executor: ToolExecutor,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> AgentResult:
    """plan 模式: 生成计划 → 逐步执行 → 汇总。

    Args:
        messages: 初始消息。
        tools: 工具。
        llm: LLM 调用。
        tool_executor: 工具执行。
        max_iterations: 最大迭代。

    Returns:
        AgentResult。
    """
    tool_names = ", ".join(t.get("function", {}).get("name", "") for t in tools)
    history = [
        {"role": "system", "content": _PLAN_SYSTEM.format(tools=tool_names or "(none)")},
        *messages,
    ]
    tool_trail: list[tuple[str, dict[str, Any], Any]] = []
    for iteration in range(max_iterations):
        response = llm(history, {})
        content = _content_of(response)
        history.append({"role": "assistant", "content": content})
        match = _PLAN_ACTION_RE.search(content)
        if not match:
            return AgentResult(
                answer=content.strip(),
                messages=history,
                tool_calls=tool_trail,
                iterations=iteration + 1,
                mode=MODE_PLAN,
            )
        action_name = match.group(1)
        args = _parse_arguments(match.group(2))
        try:
            result = tool_executor(action_name, args)
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{exc.__class__.__name__}: {exc}"}
        tool_trail.append((action_name, args, result))
        history.append(
            {
                "role": "user",
                "content": f"Observation (step {iteration + 1}): {_json_trunc(result)}",
            }
        )
    return AgentResult(
        answer="",
        messages=history,
        tool_calls=tool_trail,
        iterations=max_iterations,
        error=f"max_iterations 耗尽 ({max_iterations})",
        mode=MODE_PLAN,
    )


# ── 统一入口 ─────────────────────────────────────────────────────────


def run_agent(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]],
    mode: str = MODE_FUNCTION_CALLING,
    llm: LlmFn,
    tool_executor: ToolExecutor,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> AgentResult:
    """统一 Agent 编排入口 (按模式分派)。

    Args:
        messages: 初始消息。
        tools: OpenAI 格式工具。
        mode: function-calling / react / plan。
        llm: LLM 调用。
        tool_executor: 工具执行。
        max_iterations: 最大迭代。

    Returns:
        AgentResult。

    Raises:
        ValueError: 未知模式。

    Example:
        >>> r = run_agent([{"role": "user", "content": "hi"}], tools=[],
        ...               llm=lambda m, k: {"choices": [{"message": {"content": "ok"}}]},
        ...               tool_executor=lambda n, a: "x")
        >>> r.answer
        'ok'
    """
    if mode == MODE_FUNCTION_CALLING:
        return run_function_calling(
            messages,
            tools=tools,
            llm=llm,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )
    if mode == MODE_REACT:
        return run_react(
            messages,
            tools=tools,
            llm=llm,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )
    if mode == MODE_PLAN:
        return run_plan(
            messages,
            tools=tools,
            llm=llm,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
        )
    raise ValueError(f"unknown mode: {mode!r}; expected {MODES}")


__all__ = [
    "AgentResult",
    "DEFAULT_MAX_ITERATIONS",
    "MODE_FUNCTION_CALLING",
    "MODE_PLAN",
    "MODE_REACT",
    "MODES",
    "run_agent",
    "run_function_calling",
    "run_plan",
    "run_react",
]
