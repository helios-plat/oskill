"""oskill.formal_code_proof — 代码生成与定理自动证明 (ATP) 复合技能.

组合 LLM（生成 Lean 4 证明代码）+ LeanProver Protocol（验证证明）。
stateless，全注入。

Example:
    >>> r = formal_code_proof("∀x, x = x", lean_prover=lean, llm_caller=llm)
    >>> "proven" in r
    True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class LeanProverProtocol(Protocol):
    """Lean 证明器协议（对齐 obase.lean_formal_prover.LeanFormalProver）。"""

    def verify_lean_code(self, code_snippet: str, *, timeout_sec: float) -> dict[str, Any]: ...


def formal_code_proof(
    code_spec: str,
    *,
    lean_prover: LeanProverProtocol,
    llm_caller: Any,
) -> dict[str, Any]:
    """生成 Lean 4 代码并验证其形式化定理证明。

    Args:
        code_spec: 规格/定理描述。
        lean_prover: Lean 证明器（注入）。
        llm_caller: LLM 调用器（注入，prompt 风格协议）。

    Returns:
        {"proven": bool, "generated_lean_code": str,
         "verification_details": dict}

    Raises:
        OskillError: code_spec 为空 / 依赖未注入。
    """
    if not code_spec or not code_spec.strip():
        raise OskillError("formal_code_proof: code_spec must not be empty")
    if lean_prover is None:
        raise OskillError("formal_code_proof: lean_prover must be injected")
    if llm_caller is None:
        raise OskillError("formal_code_proof: llm_caller must be injected")

    prompt = (
        "Write a Lean 4 formal proof for the following specification:\n"
        f"{code_spec}\nOutput Lean 4 code only."
    )
    try:
        lean_code = llm_caller(prompt, temperature=0.0)
    except Exception as exc:
        raise OskillError(f"formal_code_proof: LLM call failed: {exc}") from exc

    proof_res = lean_prover.verify_lean_code(lean_code, timeout_sec=15.0)

    return {
        "proven": bool(proof_res.get("valid", False)),
        "generated_lean_code": str(lean_code),
        "verification_details": proof_res,
    }
