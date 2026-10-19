"""oskill.content_moderation — 内容审核 (Dify moderation 机制 3O 内化)。

输入/输出审核管道: 规则审核 (确定性) + LLM 审核 (注入):
  * **ModerationRule** — keyword (敏感词) / length (长度上限) / repeat
    (重复检测) 三类规则;
  * **moderate** — 规则命中 → blocked (可配置拒绝/替换);
  * **LlmModeration** — 输出阶段 LLM 审核注入 (需要人工判断的场景)。
零 veya 反向依赖: 纯规则 + 注入。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

RULE_KEYWORD = "keyword"
RULE_LENGTH = "length"
RULE_REPEAT = "repeat"
RULE_TYPES = (RULE_KEYWORD, RULE_LENGTH, RULE_REPEAT)

ACTION_BLOCK = "block"
ACTION_REPLACE = "replace"


@dataclass(frozen=True)
class ModerationRule:
    """一条审核规则。

    Attributes:
        name: 规则名。
        kind: keyword / length / repeat。
        pattern: keyword 的敏感词列表或正则。
        limit: length 上限 / repeat 阈值。
        action: block / replace。
        replacement: replace 时的替换文本。
    """

    name: str
    kind: str
    pattern: list[str] | None = None
    limit: int | None = None
    action: str = ACTION_BLOCK
    replacement: str = "[已过滤]"


@dataclass
class ModerationVerdict:
    """审核结果。"""

    passed: bool
    blocked_rules: list[str] = field(default_factory=list)
    text: str = ""  # replace 后的文本

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "blocked_rules": self.blocked_rules}


def moderate(text: str, rules: list[ModerationRule]) -> ModerationVerdict:
    """规则审核: 命中 block 规则 → 拒绝; replace 规则 → 替换。

    Args:
        text: 待审核文本。
        rules: 规则列表。

    Returns:
        ModerationVerdict。

    Example:
        >>> v = moderate("badword here", [ModerationRule("k", "keyword", pattern=["badword"])])
        >>> v.passed
        False
    """
    result_text = text
    blocked: list[str] = []
    for rule in rules:
        hit = _rule_hit(rule, result_text)
        if not hit:
            continue
        if rule.action == ACTION_REPLACE:
            result_text = _apply_replace(rule, result_text)
        else:
            blocked.append(rule.name)
    return ModerationVerdict(passed=not blocked, blocked_rules=blocked, text=result_text)


def _rule_hit(rule: ModerationRule, text: str) -> bool:
    if rule.kind == RULE_KEYWORD:
        lowered = text.lower()
        return any(k.lower() in lowered for k in (rule.pattern or []))
    if rule.kind == RULE_LENGTH:
        return rule.limit is not None and len(text) > rule.limit
    if rule.kind == RULE_REPEAT:
        # 连续重复字符检测 (如 aaaa)
        if rule.limit is None:
            return False
        return any(len(m.group(0)) >= rule.limit for m in re.finditer(r"(.)\1*", text))
    return False


def _apply_replace(rule: ModerationRule, text: str) -> str:
    for keyword in rule.pattern or []:
        text = re.sub(re.escape(keyword), rule.replacement, text, flags=re.IGNORECASE)
    return text


LlmModerator = Callable[[str], dict[str, Any]]
"""LLM 审核: (text) → {"passed": bool, "reason": str}。"""


def moderate_with_llm(
    text: str,
    llm_moderator: LlmModerator,
    rules: list[ModerationRule] | None = None,
) -> ModerationVerdict:
    """规则 + LLM 双层审核: 先规则 (快), 通过后 LLM (深度)。

    Args:
        text: 待审核文本。
        llm_moderator: LLM 审核函数。
        rules: 前置规则 (None 跳过)。

    Returns:
        ModerationVerdict。
    """
    if rules:
        verdict = moderate(text, rules)
        if not verdict.passed:
            return verdict
    try:
        result = llm_moderator(text)
        if not result.get("passed", True):
            return ModerationVerdict(passed=False, blocked_rules=["llm"])
    except Exception:  # noqa: BLE001
        pass  # LLM 审核失败不阻断 (规则已过)
    return ModerationVerdict(passed=True)


__all__ = [
    "ACTION_BLOCK",
    "ACTION_REPLACE",
    "ModerationRule",
    "ModerationVerdict",
    "RULE_KEYWORD",
    "RULE_LENGTH",
    "RULE_REPEAT",
    "RULE_TYPES",
    "moderate",
    "moderate_with_llm",
]
