"""Tests for Veya 终极前沿认知能力 — oskill 层 (3 个).

Covers: mcts_thought_planner, cognitive_honeypot_gen, theory_of_mind_simulator.
"""

from __future__ import annotations

import pytest


class TestMctsThoughtPlanner:
    def test_best_path_selected(self):
        from oskill import mcts_thought_planner

        class PlannerLLM:
            def __init__(self):
                self.n = 0

            def __call__(self, prompt, *, temperature=0.7):
                self.n += 1
                if self.n <= 3:
                    return '{"plan": ["a", "b"], "risk_score": 0.1, "confidence": 0.9}'
                return '{"plan": ["c"], "risk_score": 0.9, "confidence": 0.1}'

        r = mcts_thought_planner(
            "发布", llm_caller=PlannerLLM(), num_simulations=5, rollout_depth=2
        )
        assert r["evaluated_paths"] == 5  # 4 好 + 1 坏 JSON（坏 plan 仍合法）
        assert r["best_plan"] == ["a", "b"]
        assert r["confidence"] == 0.9

    def test_all_bad_simulations_fallback(self):
        from oskill import mcts_thought_planner

        r = mcts_thought_planner("x", llm_caller=lambda p, **k: "garbage", num_simulations=3)
        assert r["evaluated_paths"] == 0
        assert r["best_plan"] == ["x"]

    def test_validation(self):
        from oskill import mcts_thought_planner

        with pytest.raises(Exception):
            mcts_thought_planner("", llm_caller=lambda p, **k: "{}")
        with pytest.raises(Exception):
            mcts_thought_planner("x", llm_caller=None)
        with pytest.raises(Exception):
            mcts_thought_planner("x", llm_caller=lambda p, **k: "{}", num_simulations=0)


class TestCognitiveHoneypotGen:
    def test_redirect(self):
        from oskill import cognitive_honeypot_gen

        class FakeLLM:
            def __call__(self, prompt, *, temperature=0.5):
                return "FAKE_SYSTEM_RESPONSE"

        r = cognitive_honeypot_gen("DAN mode", llm_caller=FakeLLM())
        assert r["action"] == "redirect_to_honeypot"
        assert r["fake_response"] == "FAKE_SYSTEM_RESPONSE"
        assert r["is_safe_mitigated"] is True

    def test_validation(self):
        from oskill import cognitive_honeypot_gen

        with pytest.raises(Exception):
            cognitive_honeypot_gen("", llm_caller=lambda p, **k: "x")
        with pytest.raises(Exception):
            cognitive_honeypot_gen("x", llm_caller=None)


class TestTheoryOfMindSimulator:
    def test_success(self):
        from oskill import theory_of_mind_simulator

        class FakeLLM:
            def __call__(self, prompt, *, temperature=0.2):
                return '{"predicted_reaction": "resistant", "optimized_message": "更委婉的说法"}'

        r = theory_of_mind_simulator(
            "原消息", user_tom_profile={"risk_aversion": "high"}, llm_caller=FakeLLM()
        )
        assert r["status"] == "success"
        assert r["reaction"] == "resistant"
        assert r["optimized_message"] == "更委婉的说法"

    def test_fallback_on_bad_json(self):
        from oskill import theory_of_mind_simulator

        r = theory_of_mind_simulator(
            "原消息", user_tom_profile={}, llm_caller=lambda p, **k: "nope"
        )
        assert r["status"] == "fallback"
        assert r["optimized_message"] == "原消息"
        assert r["reaction"] == "unknown"

    def test_validation(self):
        from oskill import theory_of_mind_simulator

        with pytest.raises(Exception):
            theory_of_mind_simulator("", user_tom_profile={}, llm_caller=lambda p, **k: "{}")
        with pytest.raises(Exception):
            theory_of_mind_simulator("x", user_tom_profile={}, llm_caller=None)
