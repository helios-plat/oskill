"""3O 范式 Phase 3 — oskill 与大模型解耦协议 (规范 §4.3).

oskill 作为纯算法层, 不知道底下是 Anthropic 还是 OpenAI,
LLM 能力一律经本 Protocol 由上层 (oservi) 注入。
"""

from __future__ import annotations

from typing import Any, Protocol


class LLMCaller(Protocol):
    """
    规范 §4.3: LLM 依赖注入协议。
    oskill 作为纯算法层，不知道底下是 Anthropic 还是 OpenAI。
    """

    async def __call__(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]: ...
