"""Tests for agentic_rl / agent_frameworks (hello-agents 第11/5-6章 3O 内化)。"""

from __future__ import annotations

import pytest

from oskill.agent_frameworks import (
    FRAMEWORK_AUTOGEN,
    FRAMEWORK_LANGGRAPH,
    FRAMEWORK_N8N,
    FrameworkRegistry,
    dsl_to_framework,
)
from oskill.agentic_rl import (
    RULE_CONTAINS,
    RULE_EXACT,
    RULE_FORMAT,
    RULE_LENGTH,
    STAGE_EVAL,
    STAGE_RL,
    STAGE_RM,
    STAGE_SFT,
    RewardRule,
    TrainPipeline,
    compute_reward,
    grpo_advantages,
)

# ── agentic_rl (第 11 章) ──────────────────────────────────────────


def test_reward_exact_match():
    reward = compute_reward("42", [RewardRule(RULE_EXACT, expected="42")])
    assert reward == 1.0
    assert compute_reward("43", [RewardRule(RULE_EXACT, expected="42")]) == 0.0


def test_reward_contains_and_format():
    reward = compute_reward(
        "答案是 42",
        [
            RewardRule(RULE_CONTAINS, expected="42", reward=0.5),
            RewardRule(RULE_FORMAT, pattern=r"^答案是", reward=0.5),
        ],
    )
    assert reward == 1.0


def test_reward_length():
    reward = compute_reward("short", [RewardRule(RULE_LENGTH, min_len=10)])
    assert reward == 0.0
    assert compute_reward("long enough text", [RewardRule(RULE_LENGTH, min_len=10)]) == 1.0


def test_grpo_advantages_normalized():
    advantages = grpo_advantages([1.0, 0.0, 1.0])
    assert len(advantages) == 3
    assert abs(sum(advantages)) < 1e-9  # 均值为 0
    assert advantages[0] > 0  # 高分正优势


def test_grpo_advantages_zero_std():
    advantages = grpo_advantages([1.0, 1.0, 1.0])
    assert advantages == [0.0, 0.0, 0.0]
    assert grpo_advantages([]) == []


def test_train_pipeline_advance():
    pipeline = TrainPipeline(eval_threshold=0.7)
    assert pipeline.current() == STAGE_SFT
    pipeline.advance()  # SFT → RM
    assert pipeline.current() == STAGE_RM
    pipeline.advance()  # RM → RL
    assert pipeline.current() == STAGE_RL
    pipeline.advance()  # RL → EVAL
    assert pipeline.current() == STAGE_EVAL
    # EVAL 推进需评估门
    with pytest.raises(ValueError, match="eval_score required"):
        pipeline.advance()
    result = pipeline.advance(eval_score=0.8)
    assert result["ok"] is True
    assert pipeline.summary()["stage"] == STAGE_EVAL  # 终态 (无 next)


def test_train_pipeline_eval_gate_blocks():
    pipeline = TrainPipeline(eval_threshold=0.7)
    for _ in range(3):
        pipeline.advance()  # 到 EVAL
    result = pipeline.advance(eval_score=0.5)  # 未达阈值
    assert result["ok"] is False
    assert "threshold" in result["reason"]
    assert pipeline.current() == STAGE_EVAL  # 未推进


# ── agent_frameworks (第 5/6 章) ────────────────────────────────────


def _dsl() -> dict:
    return {
        "nodes": [
            {"id": "start", "type": "start", "config": {}, "outputs": []},
            {"id": "llm1", "type": "llm", "config": {"prompt": "分析"}, "outputs": ["answer"]},
            {"id": "tool1", "type": "tool", "config": {}, "outputs": ["data"]},
            {"id": "end", "type": "end", "config": {}, "outputs": []},
        ],
        "edges": [["start", "llm1"], ["llm1", "tool1"], ["tool1", "end"]],
        "variables": {},
        "entry": "start",
    }


def test_framework_registry_defaults():
    registry = FrameworkRegistry()
    assert set(registry.list_frameworks()) == {"autogen", "agentscope", "langgraph", "n8n"}
    assert "multi_agent" in registry.get(FRAMEWORK_AUTOGEN).capabilities
    assert registry.find_by_capability("lowcode") == [FRAMEWORK_N8N]


def test_framework_registry_unknown():
    registry = FrameworkRegistry()
    with pytest.raises(ValueError, match="unknown framework"):
        registry.get("nope")


def test_dsl_to_autogen():
    code = dsl_to_framework(_dsl(), FRAMEWORK_AUTOGEN)
    assert "from autogen import ConversableAgent" in code
    assert 'name="llm1"' in code
    assert 'system_message="分析"' in code


def test_dsl_to_langgraph():
    code = dsl_to_framework(_dsl(), FRAMEWORK_LANGGRAPH)
    assert "from langgraph.graph import StateGraph, END" in code
    assert 'graph.add_node("llm1"' in code
    assert 'graph.add_edge("llm1", "tool1")' in code


def test_dsl_to_framework_unsupported():
    with pytest.raises(ValueError, match="codegen not supported"):
        dsl_to_framework(_dsl(), FRAMEWORK_N8N)
