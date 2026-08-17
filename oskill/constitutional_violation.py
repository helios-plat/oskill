"""oskill.constitutional_violation — heuristic ban-token check. Pure."""

from __future__ import annotations

import re

_BAN = re.compile(
    r"(?:do\s+not\s+use|don't\s+use|never\s+use|forbidden|禁止(?:使用)?|不得使用|不准用)\s+([A-Za-z0-9_@./+-]+)",
    re.I,
)
_MUST = re.compile(
    r"(?:must\s+use|use\s+only|只能用|必须使用)\s+([A-Za-z0-9_@./+-]+)",
    re.I,
)


def constitution_rules(constitution_text: str) -> list[str]:
    return [ln.strip() for ln in constitution_text.splitlines() if ln.strip()]


def detect_constitution_violation(
    execution_log: str,
    *,
    constitution_rules: list[str] | str,
) -> str | None:
    rules = (
        constitution_rules
        if isinstance(constitution_rules, list)
        else constitution_rules.splitlines()
    )
    log = execution_log.lower()
    banned: list[str] = []
    required: list[str] = []
    for rule in rules:
        for match in _BAN.finditer(rule):
            banned.append(match.group(1))
        for match in _MUST.finditer(rule):
            required.append(match.group(1))
    for token in banned:
        if token.lower() in log:
            return f"forbidden {token} appeared in execution log"
    for token in required:
        if token.lower() not in log and _competing_tool(token, log):
            return f"required {token} missing; competing tool used"
    return None


def _competing_tool(required: str, log: str) -> bool:
    rivals = {
        "fetch": ("axios", "npm i axios", "xmlhttprequest"),
        "pnpm": ("npm i ", "yarn add"),
        "ruff": ("pylint", "flake8"),
    }
    for rival in rivals.get(required.lower(), ()):
        if rival.lower() in log:
            return True
    return False
