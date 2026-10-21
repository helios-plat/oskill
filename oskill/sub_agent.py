"""oskill.sub_agent — headless worker node for swarm orchestration.

3O layer: oskill (composite skill over an injected LLM caller).
A stateless, role-masked pure LLM wrapper: global project context + role
system prompt + single task instruction. Low temperature for deterministic
swarm output; transient failures retried with exponential backoff;
errors returned as strings (master synthesis handles them) — never raised.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

_log = logging.getLogger(__name__)


class SubAgentError(RuntimeError):
    """Raised when a required llm_caller is missing."""


class SubAgent:
    """Swarm worker node: role mask + project context + single task."""

    def __init__(
        self,
        role: str,
        context: str,
        llm_caller: Callable | None = None,
        *,
        temperature: float = 0.2,
        timeout: float = 240.0,
        max_retries: int = 3,
    ):
        """
        Args:
            role: Role name (e.g. 'React Frontend Engineer').
            context: Global project context (what the whole project is about).
            llm_caller: Host-injected LLM function
                (async (messages, **kwargs) -> OpenAI-format dict).
                Required at execution time; None makes execute() report an error.
            temperature: Determinism control for swarm work.
            timeout: Per-call LLM timeout in seconds.
            max_retries: Transient failure retry count.
        """
        self.role = role
        self.context = context
        self._llm_caller = llm_caller
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

    def get_system_prompt(self) -> str:
        """Role mask: hyper-focused, technical output only."""
        return f"""You are a specialized AI Agent acting as the '{self.role}'.
Your ONLY goal is to complete your specific task perfectly.

PROJECT CONTEXT:
{self.context}

RULES:
1. Do not worry about other parts of the project unless explicitly told to.
2. Output ONLY the code or technical specification required. No conversational filler.
3. If you generate code, ensure it is robust, production-ready, and well-commented.
"""

    async def execute(self, task_instruction: str) -> str:
        """Execute the sub-task (smallest concurrent unit of swarm work)."""
        if self._llm_caller is None:
            return f"Error executing task for {self.role}: llm_caller 未注入(宿主装配缺失)"
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"YOUR SPECIFIC TASK:\n{task_instruction}"},
        ]
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._llm_caller(
                    messages,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    max_tokens=4096,
                )
                content = (
                    (response.get("choices") or [{}])[0].get("message") or {}
                ).get("content") or ""
                return content
            except Exception as exc:  # noqa: BLE001 — one worker's failure must not kill the swarm
                last_exc = exc
                _log.warning(
                    "sub_agent [%s] attempt %d/%d failed: %s",
                    self.role,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)  # exponential backoff (429 is transient)
        return f"Error executing task for {self.role}: {type(last_exc).__name__}: {last_exc}"
