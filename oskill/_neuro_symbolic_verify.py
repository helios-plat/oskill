"""oskill.neuro_symbolic_verify — 神经符号逻辑复合验证算法.

组合 LLM 自然语言转换（FOLTranslator Protocol）+ SMT 求解器
（SMTSolver Protocol）的硬性符号逻辑验证。stateless，全注入。

Example:
    >>> r = neuro_symbolic_verify(
    ...     "p 蕴含 q 且 q 为真", fol_translator=fol_fn, smt_solver=z3_adapter, llm_caller=llm,
    ... )
    >>> "is_valid" in r
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class SMTSolverProtocol(Protocol):
    """SMT 求解器协议（对齐 obase.smt_solver_adapter.SMTSolverAdapter）。"""

    def check_satisfiability(self, declarations: Any, constraints: Any) -> dict[str, Any]: ...


@runtime_checkable
class FOLTranslatorProtocol(Protocol):
    """FOL 转换协议（对齐 oprim.fol_translate）。"""

    def __call__(self, sentence: str, *, llm_caller: Any) -> dict[str, Any]: ...


def neuro_symbolic_verify(
    natural_hypothesis: str,
    *,
    fol_translator: FOLTranslatorProtocol,
    smt_solver: SMTSolverProtocol,
    llm_caller: Any,
) -> dict[str, Any]:
    """神经符号验证：自然语言 → FOL → SMT 可满足性判定。

    Args:
        natural_hypothesis: 自然语言假说。
        fol_translator: FOL 转换器（注入）。
        smt_solver: SMT 求解器（注入）。
        llm_caller: LLM 调用器（透传给 fol_translator）。

    Returns:
        {"is_valid": bool, "status": str, "model": dict|None,
         "fol_representation": dict, "reason": str|None}

    Raises:
        OskillError: natural_hypothesis 为空 / 依赖未注入。
    """
    if not natural_hypothesis or not natural_hypothesis.strip():
        raise OskillError("neuro_symbolic_verify: natural_hypothesis must not be empty")
    if fol_translator is None or smt_solver is None:
        raise OskillError("neuro_symbolic_verify: fol_translator and smt_solver must be injected")

    # 1. 将假说转化为 FOL 逻辑表达式
    fol_res = fol_translator(natural_hypothesis, llm_caller=llm_caller)
    if fol_res.get("status") != "success":
        return {
            "is_valid": False,
            "status": "translate_failed",
            "model": None,
            "fol_representation": fol_res,
            "reason": "Failed to translate statement to FOL logic.",
        }

    # 2. 调用 SMT 求解器校验硬约束
    smt_res = smt_solver.check_satisfiability(
        declarations=fol_res["declarations"],
        constraints=fol_res["constraints"],
    )

    return {
        "is_valid": bool(smt_res.get("satisfiable", False)),
        "status": smt_res.get("status"),
        "model": smt_res.get("model"),
        "fol_representation": fol_res,
        "reason": None,
    }
