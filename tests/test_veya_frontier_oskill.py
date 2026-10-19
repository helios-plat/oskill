"""Tests for Veya 前沿探索元素 — oskill 层 (3 个).

Covers: neuro_symbolic_verify, counterfactual_reasoning, formal_code_proof.
"""

from __future__ import annotations

import pytest


class FakeFOL:
    def __call__(self, sentence, *, llm_caller):
        return {
            "status": "success",
            "declarations": [{"name": "p", "type": "Bool"}],
            "constraints": ["p"],
        }


class BadFOL:
    def __call__(self, sentence, *, llm_caller):
        return {"status": "error", "error": "translate failed"}


class FakeSMT:
    def check_satisfiability(self, declarations, constraints):
        return {"status": "sat", "satisfiable": True, "model": {"p": "True"}}


class UnsatisfiableSMT:
    def check_satisfiability(self, declarations, constraints):
        return {"status": "unsat", "satisfiable": False, "model": None}


class CFLM:
    def __call__(self, prompt, *, temperature=0.1):
        return '{"would_succeed": true, "root_cause": "缺判空", "explanation": "补判空即可"}'


class CodeLLM:
    def __call__(self, prompt, *, temperature=0.0):
        return "theorem t : True := by trivial"


class FakeLean:
    def verify_lean_code(self, code_snippet, *, timeout_sec):
        return {"valid": True, "returncode": 0, "stdout": "", "stderr": ""}


class TestNeuroSymbolicVerify:
    def test_valid_hypothesis(self):
        from oskill import neuro_symbolic_verify

        r = neuro_symbolic_verify(
            "p", fol_translator=FakeFOL(), smt_solver=FakeSMT(), llm_caller=object()
        )
        assert r["is_valid"] is True
        assert r["status"] == "sat"
        assert r["model"] == {"p": "True"}
        assert r["fol_representation"]["constraints"] == ["p"]

    def test_translate_failure(self):
        from oskill import neuro_symbolic_verify

        r = neuro_symbolic_verify(
            "q", fol_translator=BadFOL(), smt_solver=FakeSMT(), llm_caller=object()
        )
        assert r["is_valid"] is False
        assert r["status"] == "translate_failed"

    def test_unsat(self):
        from oskill import neuro_symbolic_verify

        r = neuro_symbolic_verify(
            "p", fol_translator=FakeFOL(), smt_solver=UnsatisfiableSMT(), llm_caller=object()
        )
        assert r["is_valid"] is False and r["status"] == "unsat"

    def test_validation(self):
        from oskill import neuro_symbolic_verify

        with pytest.raises(Exception):
            neuro_symbolic_verify(
                "", fol_translator=FakeFOL(), smt_solver=FakeSMT(), llm_caller=object()
            )
        with pytest.raises(Exception):
            neuro_symbolic_verify(
                "p", fol_translator=None, smt_solver=FakeSMT(), llm_caller=object()
            )


class TestCounterfactualReasoning:
    def test_success(self):
        from oskill import counterfactual_reasoning

        r = counterfactual_reasoning(
            {"nodes": [{"id": "n1"}]}, "step_1", llm_caller=CFLM(), alternative_action="加判空"
        )
        assert r["status"] == "success"
        assert r["would_succeed"] is True
        assert r["root_cause"] == "缺判空"
        assert r["explanation"] == "补判空即可"

    def test_invalid_llm_output(self):
        from oskill import counterfactual_reasoning

        class BadLLM:
            def __call__(self, prompt, *, temperature=0.1):
                return "garbage"

        r = counterfactual_reasoning({"nodes": []}, "s1", llm_caller=BadLLM())
        assert r["status"] == "failed" and r["would_succeed"] is False

    def test_validation(self):
        from oskill import counterfactual_reasoning

        with pytest.raises(Exception):
            counterfactual_reasoning({}, "s1", llm_caller=CFLM())
        with pytest.raises(Exception):
            counterfactual_reasoning({"nodes": []}, "", llm_caller=CFLM())


class TestFormalCodeProof:
    def test_proven(self):
        from oskill import formal_code_proof

        r = formal_code_proof("True", lean_prover=FakeLean(), llm_caller=CodeLLM())
        assert r["proven"] is True
        assert "theorem" in r["generated_lean_code"]
        assert r["verification_details"]["valid"] is True

    def test_not_proven(self):
        from oskill import formal_code_proof

        class BadLean:
            def verify_lean_code(self, code_snippet, *, timeout_sec):
                return {"valid": False, "returncode": 1, "stdout": "", "stderr": "error: x"}

        r = formal_code_proof("False", lean_prover=BadLean(), llm_caller=CodeLLM())
        assert r["proven"] is False

    def test_validation(self):
        from oskill import formal_code_proof

        with pytest.raises(Exception):
            formal_code_proof("", lean_prover=FakeLean(), llm_caller=CodeLLM())
        with pytest.raises(Exception):
            formal_code_proof("x", lean_prover=None, llm_caller=CodeLLM())
