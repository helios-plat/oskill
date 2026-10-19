"""3O 范式全栈 — oskill 新增技能测试 (元素 13-19)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from oskill import (
    apply_unified_diff,
    evaluate_stop_condition,
    parse_imports,
    parse_tool_call_json,
    translate_tool_calls,
    truncate_history,
    validate_tool_args,
)


class ShellCmd(BaseModel):
    command: str
    timeout: int = 30


def test_parse_tool_call_json_valid():
    parsed = parse_tool_call_json('{"tool_name": "shell_exec", "args": {"command": "ls"}}')
    assert parsed["tool_name"] == "shell_exec"


def test_parse_tool_call_json_invalid():
    with pytest.raises(ValueError, match="Invalid Tool JSON"):
        parse_tool_call_json("{not json}")


def test_validate_tool_args_valid():
    model = validate_tool_args(ShellCmd, {"command": "ls"})
    assert isinstance(model, ShellCmd)
    assert model.command == "ls"


def test_validate_tool_args_rejects_wrong_type():
    with pytest.raises(ValueError, match="Schema violation"):
        validate_tool_args(ShellCmd, {"command": 123})  # 类型不符


def test_validate_tool_args_rejects_extra_when_forbidden():
    class StrictShellCmd(BaseModel):
        model_config = {"extra": "forbid"}
        command: str

    with pytest.raises(ValueError, match="Schema violation"):
        validate_tool_args(StrictShellCmd, {"command": "ls", "bogus": 1})


def test_parse_imports():
    code = "import os\nimport sys\nfrom pathlib import Path\n\ndef f():\n    import json\n"
    imports = parse_imports(code)
    assert "os" in imports and "sys" in imports and "json" in imports
    assert "pathlib" not in imports  # from-import 不在提取范围


def test_truncate_history_within_window():
    history = [{"role": "system"}, {"role": "user"}]
    assert truncate_history(history, max_turns=10) is history


def test_truncate_history_sliding_window():
    history = [{"role": "system"}] + [{"role": "user", "i": i} for i in range(12)]
    kept = truncate_history(history, max_turns=5)
    assert kept[0] == {"role": "system"}
    assert len(kept) == 5
    assert kept[-1] == {"role": "user", "i": 11}  # 保留最近回合


def test_evaluate_stop_condition():
    assert evaluate_stop_condition({"tool_name": "final_answer"}, 3, max_turns=15) is True
    assert evaluate_stop_condition({"tool_name": "shell_exec"}, 3, max_turns=15) is False
    assert evaluate_stop_condition({"tool_name": "shell_exec"}, 15, max_turns=15) is True


def test_apply_unified_diff():
    result = apply_unified_diff(
        "a\nb\n",
        diff="@@ -1,2 +1,2 @@\n a\n-b\n+B\n",
    )
    assert result.content == "a\nB\n"
    assert result.applied == 1


def test_translate_openai_to_anthropic():
    calls = [{"name": "shell_exec", "arguments": {"command": "ls"}}]
    translated = translate_tool_calls(calls, target="anthropic")
    assert translated == [{"name": "shell_exec", "input": {"command": "ls"}}]


def test_translate_anthropic_to_openai():
    calls = [{"name": "shell_exec", "input": {"command": "ls"}}]
    translated = translate_tool_calls(calls, target="openai")
    assert translated == [{"name": "shell_exec", "arguments": {"command": "ls"}}]


def test_translate_string_arguments():
    calls = [{"name": "x", "arguments": '{"a": 1}'}]
    translated = translate_tool_calls(calls, target="anthropic")
    assert translated == [{"name": "x", "input": {"a": 1}}]


def test_translate_unsupported_target():
    with pytest.raises(ValueError, match="Unsupported target"):
        translate_tool_calls([], target="gemini")
