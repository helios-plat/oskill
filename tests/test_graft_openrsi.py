"""3O 范式内化 — oskill 技能测试 (Graft 摘要 / OpenRSI 算子 / 经验归纳)."""

from __future__ import annotations

from oskill import induce_experience, summarize_symbol
from oskill.evo_crossover import evo_crossover
from oskill.evo_debug import evo_debug
from oskill.evo_draft import evo_draft
from oskill.evo_improve import evo_improve


class _FakeLLM:
    """按 LLMCaller 协议的假 LLM: 按序返回预设回复, 并记录收到的提示。"""

    def __init__(self, replies: list[str]):
        self.replies = replies
        self.calls = 0
        self.prompts: list[str] = []

    async def __call__(self, *, messages, tools=None, max_tokens=4096):
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        self.prompts.append(messages[0]["content"])
        return {"content": reply}


async def test_summarize_symbol():
    llm = _FakeLLM(["Handles JWT auth and token refresh."])
    summary = await summarize_symbol("auth_service", code="def f(): pass", llm=llm)
    assert summary == "Handles JWT auth and token refresh."


async def test_evo_draft_extracts_fenced_code():
    llm = _FakeLLM(["```python\nprint('draft')\n```"])
    code = await evo_draft("print hello", llm=llm)
    assert code == "print('draft')"


async def test_evo_draft_with_constraints():
    llm = _FakeLLM(["```python\nx = 1\n```"])
    code = await evo_draft("task", llm=llm, constraints=["no recursion", "pure function"])
    assert "no recursion" in llm.prompts[0]
    assert "pure function" in llm.prompts[0]
    assert code == "x = 1"


async def test_evo_improve():
    llm = _FakeLLM(["```python\ndef f():\n    return 1\n```"])
    code = await evo_improve("def f(): pass", feedback="tests failed: 1", llm=llm)
    assert "return 1" in code


async def test_evo_debug():
    llm = _FakeLLM(["```python\ndef f():\n    return 2\n```"])
    code = await evo_debug(
        "def f(): pass",
        error_trace="AssertionError at line 3: expected 200 got 500",
        llm=llm,
    )
    assert "return 2" in code


async def test_evo_crossover():
    llm = _FakeLLM(["```python\nmerged\n```"])
    code = await evo_crossover("def a(): pass", code_b="def b(): pass", llm=llm)
    assert code == "merged"


async def test_induce_experience_returns_triple():
    llm = _FakeLLM(
        [
            "```json\n"
            '{"context_description": "高并发 MySQL 死锁", '
            '"failed_attempt": {"action": "事务内 HTTP", "reason": "持锁过长"}, '
            '"successful_strategy": {"action": "先 HTTP 后事务", "reason": "缩短持锁"}}\n'
            "```"
        ]
    )
    result = await induce_experience(
        {"branch_id": "b1", "error_trace": "timeout"},
        successful_trajectory={"branch_id": "b2", "output_code": "ok"},
        llm=llm,
    )
    assert result["context_description"] == "高并发 MySQL 死锁"
    assert result["failed_attempt"]["action"] == "事务内 HTTP"
    assert result["successful_strategy"]["reason"] == "缩短持锁"
