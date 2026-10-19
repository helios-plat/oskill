"""oskill.skills_dynamic_inject — 上下文匹配动态注入 Rules 算子.

Stateless 纯算法。依赖 SkillsRegistry + LLMCallerProtocol 注入.

组合: SkillsRegistry (依赖注入) + LLM caller (依赖注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

from typing import Any, Protocol


class SkillsRegistryProtocol(Protocol):
    """Skills 注册表 Protocol — 不 import obase，由调用方注入."""

    def match_rules(self, context_key: str) -> list[str]: ...
    def list_rules(self) -> dict[str, str]: ...


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol — 不 import oprim，由调用方注入."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def skills_dynamic_inject(
    context_filename: str,
    *,
    registry: SkillsRegistryProtocol,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """结合依赖文件扩展名从 Registry 动态匹配 Rules 并合成最佳 System Prompt.

    流程:
    1. 从 registry 匹配适用的规则
    2. 用 LLM 将多条规则合成为一个紧凑的 System Prompt 前缀

    Args:
        context_filename: 上下文文件名（如 "main.py", "contract.rs"）
        registry: Skills 注册表（注入）
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "matched_count": int,
            "rules": list[str],
            "injected_prompt_prefix": str,
        }
    """
    matched_rules = registry.match_rules(context_filename) if registry else []

    if not matched_rules:
        return {
            "matched_count": 0,
            "rules": [],
            "injected_prompt_prefix": "",
        }

    rules_text = "\n".join([f"- {r}" for r in matched_rules])

    prompt = (
        f"Target File Context: {context_filename}\n"
        f"Matched Coding Rules:\n{rules_text}\n\n"
        f"Synthesize these rules into a concise SYSTEM PROMPT prefix "
        f"(2-4 sentences) that an LLM can prepend to guide code generation. "
        f"Reply with ONLY the prompt prefix text, no extra commentary."
    )

    try:
        prefix = llm_caller(prompt, temperature=0.0)
        prefix = prefix.strip()
    except Exception:
        prefix = f"[AUTO-RULES for {context_filename}]: " + "; ".join(r[:80] for r in matched_rules)

    return {
        "matched_count": len(matched_rules),
        "rules": matched_rules,
        "injected_prompt_prefix": prefix,
    }
