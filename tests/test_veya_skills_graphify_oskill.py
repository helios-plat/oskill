"""Tests for oskill skills."""

from __future__ import annotations

from unittest.mock import MagicMock

from oskill._skills_dynamic_inject import skills_dynamic_inject


def _make_llm(return_value: str):
    mock = MagicMock()
    mock.return_value = return_value
    return mock


# ============================================================================
# skills_dynamic_inject
# ============================================================================


class TestSkillsDynamicInject:
    def test_matches_python_rules(self):
        registry = MagicMock()
        registry.match_rules.return_value = [
            "Follow PEP8. Use explicit type hints.",
        ]
        llm = _make_llm("Use PEP8. Add type hints. Write docstrings.")

        result = skills_dynamic_inject("main.py", registry=registry, llm_caller=llm)
        assert result["matched_count"] == 1
        assert len(result["rules"]) == 1
        assert len(result["injected_prompt_prefix"]) > 0

    def test_no_rules_matched(self):
        registry = MagicMock()
        registry.match_rules.return_value = []
        llm = _make_llm("")

        result = skills_dynamic_inject("unknown.xyz", registry=registry, llm_caller=llm)
        assert result["matched_count"] == 0
        assert result["injected_prompt_prefix"] == ""

    def test_llm_failure_fallback(self):
        registry = MagicMock()
        registry.match_rules.return_value = ["Rule A", "Rule B"]

        def raise_llm(prompt, **kwargs):
            raise RuntimeError("LLM down")

        result = skills_dynamic_inject("test.py", registry=registry, llm_caller=raise_llm)
        assert result["matched_count"] == 2
        # Should produce a fallback prefix
        assert "AUTO-RULES" in result["injected_prompt_prefix"]

    def test_llm_called_with_rules(self):
        registry = MagicMock()
        registry.match_rules.return_value = ["Rule X"]
        llm = _make_llm("SYNTHESIZED PROMPT PREFIX")

        result = skills_dynamic_inject("file.rs", registry=registry, llm_caller=llm)
        call_arg = result["rules"][0] if result["rules"] else ""
        assert "Rule X" in call_arg

    def test_multiple_rules(self):
        registry = MagicMock()
        registry.match_rules.return_value = ["R1", "R2", "R3"]
