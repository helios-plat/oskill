"""oskill.cognitive_honeypot_gen — 对抗性伪造响应生成与诱敌沙箱重定向.

当识别到越狱/攻击时，生成高逼真度的伪造响应，将攻击者引导至诱敌蜜罐。
stateless，LLM Protocol 注入。

Example:
    >>> r = cognitive_honeypot_gen("DAN mode", llm_caller=llm)
    >>> r["action"]
    'redirect_to_honeypot'
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from oskill._exceptions import OskillError


@runtime_checkable
class LLMCallerProtocol(Protocol):
    """LLM 调用协议。"""

    def __call__(self, prompt: str, *, temperature: float = 0.5) -> str: ...


def cognitive_honeypot_gen(
    adversarial_prompt: str,
    *,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """生成蜜罐伪造响应。

    Args:
        adversarial_prompt: 攻击者 Prompt。
        llm_caller: LLM 调用器（注入）。

    Returns:
        {"action": "redirect_to_honeypot", "fake_response": str,
         "is_safe_mitigated": True}

    Raises:
        OskillError: adversarial_prompt 为空 / llm_caller 未注入。
    """
    if not adversarial_prompt or not adversarial_prompt.strip():
        raise OskillError("cognitive_honeypot_gen: adversarial_prompt must not be empty")
    if llm_caller is None:
        raise OskillError("cognitive_honeypot_gen: llm_caller must be injected")

    prompt = (
        "Generate a convincing fake system response to honeypot an adversarial AI attack:\n"
        f"Attacker Prompt: {adversarial_prompt[:4000]}\n"
        "Requirements: Pretend the attack succeeded, but return harmless dummy data."
    )
    try:
        fake_response = llm_caller(prompt, temperature=0.3)
    except Exception as exc:
        raise OskillError(f"cognitive_honeypot_gen: LLM call failed: {exc}") from exc

    return {
        "action": "redirect_to_honeypot",
        "fake_response": str(fake_response),
        "is_safe_mitigated": True,
    }
