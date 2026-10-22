"""Natural-language Gloom 3O command routing with an optional injected LLM.

The router never creates missing command parameters from defaults. With no
explicit LLM key it uses deterministic keyword/argument rules and returns a
structured route (or an explicit unmatched result). Gloomberb
(https://github.com/gloom-sh/gloomberb, MIT) was reviewed as requested; no
Gloomberb source code is copied into this router.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

GLOOM3O_COMMANDS = ("QUOTE", "DES", "GP", "OPX", "KELLY", "RISK", "PORT", "FUSION", "HELP")

_SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2,10}(?:-[A-Za-z0-9]{2,10})?)(?![A-Za-z0-9])")
_NUMBER_RE = r"\d+(?:\.\d+)?"


class LLMCaller(Protocol):
    def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        stop_sequences: list[str] | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CommandRoute:
    """A command route without a dependency on the service-layer package."""

    command: str | None
    arguments: tuple[str, ...] = ()
    options: dict[str, str] = field(default_factory=dict)
    source: str = "rules"
    reason: str = ""


def _symbol_from_query(query: str) -> str | None:
    ignored = {
        "USD", "USDT", "USDC", "THE", "AND", "FOR", "WITH", "FUSION", "SCORE",
        "OPTIONS", "OPTION", "QUOTE", "PRICE", "KELLY", "RISK", "PROFILE",
        "DERIVATIVES", "SUMMARY", "PORTFOLIO", "HELP", "WHAT", "IS", "HOW", "MUCH",
        "CURRENT", "NOW", "SHOW", "ME", "MY", "OF", "ON", "CAN", "YOU", "PLEASE",
    }
    candidates = [match.group(1).upper() for match in _SYMBOL_RE.finditer(query)]
    return next((value for value in candidates if value not in ignored), None)


def _explicit_number(query: str, aliases: tuple[str, ...]) -> str | None:
    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    number_pattern = rf"(?:{alias_pattern})\s*[=:：]?\s*({_NUMBER_RE})\s*(%)?"
    match = re.search(number_pattern, query, re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    if match.group(2) or ("胜率" in aliases and number > 1.0):
        number /= 100.0
    return str(number)


def _rule_route(query: str, *, reason: str = "keyword rule match") -> CommandRoute:
    lowered = query.casefold()
    if any(token in lowered for token in ("help", "帮助", "命令列表", "指令列表")):
        return CommandRoute("HELP", reason=reason)

    symbol = _symbol_from_query(query)
    if any(token in lowered for token in ("kelly", "凯利")):
        options: dict[str, str] = {}
        probability = _explicit_number(query, ("p", "probability", "win_probability", "胜率"))
        odds = _explicit_number(query, ("b", "odds", "win_loss_ratio", "赔率"))
        fraction = _explicit_number(query, ("fraction", "kelly_fraction", "凯利比例"))
        if probability is not None:
            options["p"] = probability
        if odds is not None:
            options["b"] = odds
        if fraction is not None:
            options["fraction"] = fraction
        return CommandRoute("KELLY", options=options, reason=reason)

    option_intents = ("期权", "option", "max pain", "put/call", "pcr", "gex", "隐含波动")
    if any(token in lowered for token in option_intents):
        options = {"underlying": symbol} if symbol else {}
        exchange = re.search(r"\b(deribit|okx)\b", lowered)
        if exchange:
            options["exchange"] = exchange.group(1)
        return CommandRoute("OPX", (symbol,) if symbol else (), options, reason=reason)

    if any(token in lowered for token in ("var", "cvar", "风险", "回撤", "risk")):
        options = {}
        returns = re.search(r"(?:returns|收益)\s*[=:：]\s*([+\-0-9., ]+)", query, re.IGNORECASE)
        if returns:
            observations = (part.strip() for part in returns.group(1).split(","))
            options["returns"] = ",".join(part for part in observations if part)
        return CommandRoute("RISK", options=options, reason=reason)

    if any(token in lowered for token in ("持仓", "portfolio", "position", "账户")):
        return CommandRoute("PORT", reason=reason)
    if "fusion" in lowered or "融合分" in lowered:
        return CommandRoute("FUSION", (symbol,) if symbol else (), reason=reason)
    if any(token in lowered for token in ("衍生品统计", "衍生品摘要", "derivatives summary")):
        return CommandRoute("DES", (symbol,) if symbol else (), reason=reason)
    if any(token in lowered for token in ("gloom profile", "gloom profile", "gp ")):
        return CommandRoute("GP", (symbol,) if symbol else (), reason=reason)
    if any(token in lowered for token in ("报价", "价格", "quote", "price")):
        return CommandRoute("QUOTE", (symbol,) if symbol else (), reason=reason)
    return CommandRoute(None, reason="no deterministic command rule matched")


def _llm_route_payload(response: dict[str, Any]) -> dict[str, Any] | None:
    calls = response.get("tool_calls")
    if calls is None:
        choices = response.get("choices") or []
        if choices:
            message = choices[0].get("message", {})
            calls = message.get("tool_calls")
            if not calls and message.get("content"):
                calls = [{"function": {"arguments": message["content"]}}]
    if calls:
        first = calls[0]
        function = first.get("function", first)
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return None
        return arguments if isinstance(arguments, dict) else None
    content = response.get("content")
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None
    return None


def _validated_llm_route(payload: dict[str, Any]) -> CommandRoute | None:
    command = payload.get("command")
    if not isinstance(command, str) or command.upper() not in GLOOM3O_COMMANDS:
        return None
    raw_arguments = payload.get("arguments", [])
    raw_options = payload.get("options", {})
    if not isinstance(raw_arguments, list) or not all(
        isinstance(item, str) for item in raw_arguments
    ):
        return None
    if not isinstance(raw_options, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw_options.items()
    ):
        return None
    return CommandRoute(
        command=command.upper(),
        arguments=tuple(raw_arguments),
        options={key.lower().replace("-", "_"): value for key, value in raw_options.items()},
        source="llm",
        reason="LLM structured route",
    )


def route_gloom3o_command(
    query: str,
    *,
    llm_caller: LLMCaller | None = None,
    api_key: str | None = None,
) -> CommandRoute:
    """Route natural language to a supported command, using rules without an LLM key.

    The LLM is called only when both a caller and an explicit key (argument or
    ``GLOOM3O_LLM_API_KEY``) are present. Any LLM error or invalid route falls
    back to deterministic rules; no argument values are invented.
    """
    if not isinstance(query, str) or not query.strip():
        return CommandRoute(None, source="rules", reason="query is empty")
    key_present = bool(
        api_key
        or os.environ.get("GLOOM3O_LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DASHSCOPE_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
    )
    if llm_caller is not None and key_present:
        tool = {
            "type": "function",
            "function": {
                "name": "route_gloom3o_command",
                "description": "Choose one command and pass only explicitly stated arguments.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "enum": list(GLOOM3O_COMMANDS)},
                        "arguments": {"type": "array", "items": {"type": "string"}},
                        "options": {"type": "object", "additionalProperties": {"type": "string"}},
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        }
        try:
            response = llm_caller(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Route the request to one supported Gloom 3O command. Never invent "
                            "symbols, prices, balances, returns, or numeric arguments. Return the "
                            "route_gloom3o_command tool call."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                tools=[tool],
                max_tokens=256,
            )
            payload = _llm_route_payload(response)
            if payload is not None:
                routed = _validated_llm_route(payload)
                if routed is not None:
                    return routed
        except Exception:
            pass
    return _rule_route(query, reason="rules fallback (LLM key unavailable or route invalid)")
