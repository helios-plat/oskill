"""oskill.llm_router — LLM 智能路由技能 (RouteLLM 3O 内化, 技能层)。

组合 oprim 两原语 (路由决策 / 并行分派) 为可用技能:
  route(messages, tools)      → 决策 + 审计
  dispatch_long(prompt, caller) → 长文并行快速回答 (切分+gather+聚合)
  call_aliased(messages, tools, caller) → 别名入口: 决策 → 单发/并行 → 审计

零 veya 反向依赖: 网络调用由装配层注入 caller。
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from oprim._llm_router import load_matrix, route_decision
from oprim._parallel_llm import dispatch_parallel, split_prompt

AUDIT_FILE = Path.home() / ".veya" / "audit" / "llm-router.jsonl"


class LLMRouter:
    """路由技能: 决策 + 并行编排 + 审计。"""

    def __init__(self, matrix_path: str = "", audit_path: str = "") -> None:
        self.matrix_path = matrix_path
        self._audit = Path(audit_path or AUDIT_FILE)

    def _audit_write(self, entry: dict[str, Any]) -> None:
        try:
            self._audit.parent.mkdir(parents=True, exist_ok=True)
            with open(self._audit, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def route(self, messages: list[dict[str, Any]],
              tools: list | None = None) -> dict[str, Any]:
        """路由决策 + 审计。"""
        matrix = load_matrix(self.matrix_path)
        decision = route_decision(messages, tools, matrix)
        decision["alias"] = matrix.get("alias", "veya1.1")
        decision["ts"] = time.time()
        decision["audit_id"] = f"lr_{uuid.uuid4().hex[:10]}"
        self._audit_write(decision)
        return decision

    async def dispatch_long(self, prompt: str,
                            caller: Callable[[str, int], Awaitable[dict[str, Any]]],
                            *, max_parallel: int | None = None,
                            title: str = "") -> dict[str, Any]:
        """长文并行快速回答 (切分 → gather → 聚合)。"""
        matrix = load_matrix(self.matrix_path)
        parallelism = max_parallel or int(matrix.get("parallelism", 4))
        result = await dispatch_parallel(prompt, caller, max_parallel=parallelism,
                                         title=title)
        result["alias"] = matrix.get("alias", "veya1.1")
        self._audit_write({"action": "dispatch_long", "ts": time.time(),
                           **{k: v for k, v in result.items()
                              if k in ("parallel", "chunks", "elapsed_s")}})
        return result

    async def call_aliased(
        self,
        messages: list[dict[str, Any]],
        caller: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        *,
        tools: list | None = None,
    ) -> dict[str, Any]:
        """别名入口: 决策 → 单发 (short) / 并行 (long) → 结果。

        caller: 装配层注入的单次调用函数, 接收 {"provider", "model", "messages", "tools"}
        """
        decision = self.route(messages, tools)
        if decision["route"] == "long":
            prompt = " ".join(
                str(m.get("content", "")) for m in messages
                if isinstance(m.get("content"), str))

            async def _chunk_caller(chunk: str, idx: int) -> dict[str, Any]:
                res = await caller({
                    "provider": decision["provider"],
                    "model": decision["model"],
                    "messages": [{"role": "user", "content": chunk}],
                    "tools": None,
                })
                content = ""
                try:
                    content = str(res["choices"][0]["message"].get("content", ""))
                except (KeyError, IndexError, TypeError):
                    content = str(res.get("output", ""))
                return {"ok": bool(content), "output": content}

            return await self.dispatch_long(prompt, _chunk_caller,
                                            title="长文并行回答")
        result = await caller({
            "provider": decision["provider"],
            "model": decision["model"],
            "messages": messages,
            "tools": tools,
        })
        result["route"] = decision["route"]
        result["alias"] = decision["alias"]
        return result


llm_router = LLMRouter()


__all__ = ["LLMRouter", "llm_router", "split_prompt"]
