"""Tests for reflection_agent / context_engineering / agent_messaging
(hello-agents 三机制 3O 内化)。"""

from __future__ import annotations

from oskill.agent_messaging import (
    MSG_STATUS_ERROR,
    MSG_STATUS_SUCCESS,
    A2AProtocol,
    AgentBus,
)
from oskill.context_engineering import (
    ROLE_SYSTEM,
    ROLE_USER,
    ContextBudget,
    ContextEngine,
    ContextMessage,
    messages_from_dicts,
)
from oskill.reflection_agent import ReflectionLoop

# ── Reflection 范式 ─────────────────────────────────────────────────


def test_reflection_pass_first():
    result = ReflectionLoop(max_rounds=3).run(
        "t",
        generate=lambda t: "完整回答",
        critique=lambda a: [],
        revise=lambda a, c: a,
    )
    assert result.stopped_reason == "critique_passed"
    assert result.rounds == 0
    assert result.answer == "完整回答"


def test_reflection_revises_until_pass():
    calls = {"revise": 0}
    result = ReflectionLoop(max_rounds=3).run(
        "t",
        generate=lambda t: "短",
        critique=lambda a: [] if len(a) >= 10 else ["不够详细"],
        revise=lambda a, c: calls.__setitem__("revise", calls["revise"] + 1) or a + " 补充内容",
    )
    assert result.stopped_reason == "critique_passed"
    assert result.rounds == 2  # "短"→6 字符→11 字符, 两轮修正后达标
    assert calls["revise"] == 2
    assert len(result.answer) >= 10


def test_reflection_no_improvement_stops():
    result = ReflectionLoop(max_rounds=5).run(
        "t",
        generate=lambda t: "v1",
        critique=lambda a: ["有问题"],
        revise=lambda a, c: a,  # 修正无变化
    )
    assert result.stopped_reason == "no_improvement"
    assert result.rounds == 1


def test_reflection_max_rounds():
    result = ReflectionLoop(max_rounds=2).run(
        "t",
        generate=lambda t: "v1",
        critique=lambda a: ["总有问题"],
        revise=lambda a, c: a + "x",
    )
    assert result.stopped_reason == "max_rounds"
    assert result.rounds == 2
    assert len(result.critiques) == 2


def test_reflection_result_to_dict():
    result = ReflectionLoop().run(
        "t", generate=lambda t: "ok", critique=lambda a: [], revise=lambda a, c: a
    )
    data = result.to_dict()
    assert data["stopped_reason"] == "critique_passed"


# ── 上下文工程 ──────────────────────────────────────────────────────


def _messages() -> list[ContextMessage]:
    return [
        ContextMessage(role=ROLE_SYSTEM, content="system", priority=0),
        ContextMessage(role=ROLE_USER, content="q1", priority=1, ts=1),
        ContextMessage(role=ROLE_USER, content="q2", priority=3, ts=2),
        ContextMessage(role=ROLE_USER, content="q3", priority=3, ts=3),
    ]


def test_trim_keeps_system_and_drops_low_priority():
    engine = ContextEngine()
    result = engine.trim(
        _messages(),
        ContextBudget(max_tokens=30, keep_roles=(ROLE_SYSTEM,)),
    )
    # 默认 token 计数 len/4: system(6)+q1(2)+q2(2)+q3(2)=12 tokens, 不超 30
    assert result.total_tokens <= 30
    assert any(m.role == ROLE_SYSTEM for m in result.messages)


def test_trim_summarizes_low_priority():
    engine = ContextEngine()
    result = engine.trim(
        _messages(),
        ContextBudget(max_tokens=20, keep_roles=(ROLE_SYSTEM,), summarize_below_priority=2),
        summarize_fn=lambda t: "S",
    )
    assert result.summarized >= 1  # q2/q3 低优先级被摘要
    assert any(m.summary == "S" for m in result.messages)


def test_trim_drops_overflow():
    engine = ContextEngine()
    messages = [
        ContextMessage(role=ROLE_USER, content="x" * 40, priority=1, ts=1),
        ContextMessage(role=ROLE_USER, content="y" * 40, priority=1, ts=2),
    ]
    result = engine.trim(messages, ContextBudget(max_tokens=15))
    assert result.dropped >= 1
    assert result.total_tokens <= 15


def test_messages_from_dicts():
    messages = messages_from_dicts(
        [
            {"role": "user", "content": "hi"},
            {"role": "user", "content": "hi2", "priority": 5},
        ]
    )
    assert messages[0].role == ROLE_USER
    assert messages[1].priority == 5


# ── A2A 协议 ────────────────────────────────────────────────────────


def test_a2a_send_reply():
    protocol = A2AProtocol()
    request = protocol.send("a", "b", "查数据", payload={"q": "x"})
    assert request.status == "request"
    reply = protocol.reply(request, status=MSG_STATUS_SUCCESS, payload=[1, 2])
    assert reply.to_agent == "a"
    assert reply.reply_to == request.message_id
    assert protocol.replies_to(request.message_id)[0].payload == [1, 2]


def test_agent_bus_dispatch_by_capability():
    bus = AgentBus()
    bus.register("planner", ["plan"], lambda m: "plan done")
    bus.register("coder", ["code"], lambda m: "code done")
    reply = bus.dispatch("user", "写代码", require_capability="code")
    assert reply.status == MSG_STATUS_SUCCESS
    assert reply.payload == "code done"


def test_agent_bus_no_capable_agent():
    bus = AgentBus()
    bus.register("coder", ["code"], lambda m: "x")
    reply = bus.dispatch("user", "画画", require_capability="art")
    assert reply.status == MSG_STATUS_ERROR
    assert "no capable agent" in reply.payload


def test_agent_bus_handler_error():
    bus = AgentBus()

    def boom(m):
        raise RuntimeError("fail")

    bus.register("worker", ["work"], boom)
    reply = bus.dispatch("user", "干重活", to_agent="worker")
    assert reply.status == MSG_STATUS_ERROR
    assert "fail" in reply.payload


def test_agent_bus_summary():
    bus = AgentBus()
    bus.register("a", ["x"], lambda m: None)
    assert bus.summary()["agents"] == {"a": ["x"]}
