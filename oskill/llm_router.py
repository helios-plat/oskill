"""oskill.llm_router — LLM 智能路由技能 (RouteLLM 3O 内化, 技能层)。

组合 oprim 两原语 (路由决策 / 并行分派) 为可用技能:
  route(messages, tools)      → 决策 + 审计
  dispatch_long(prompt, caller) → 长文并行快速回答 (切分+gather+聚合)
  call_aliased(messages, tools, caller) → 别名入口: 决策 → 单发/并行 → 审计

零 veya 反向依赖: 网络调用由装配层注入 caller。
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from oprim._llm_router import load_matrix, route_decision
from oprim._parallel_llm import dispatch_parallel, split_prompt
from oprim._quality_gate import quality_check

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
              tools: list | None = None, *,
              priority: str = "normal",
              budget: float | None = None) -> dict[str, Any]:
        """路由决策 (成本阈值/优先级感知) + 审计。"""
        matrix = load_matrix(self.matrix_path)
        decision = route_decision(messages, tools, matrix,
                                  priority=priority, budget=budget)
        decision["alias"] = matrix.get("alias", "veya1.1")
        decision["priority"] = priority
        decision["budget"] = budget
        decision["ts"] = time.time()
        decision["audit_id"] = f"lr_{uuid.uuid4().hex[:10]}"
        self._audit_write(decision)
        return decision

    async def dispatch_long(self, prompt: str,
                            caller: Callable[[str, int], Awaitable[dict[str, Any]]],
                            *, max_parallel: int | None = None,
                            title: str = "",
                            planner: Callable[[str, str], Awaitable[dict[str, Any]]] | None = None,
                            ) -> dict[str, Any]:
        """长程任务深度规划链: 强模型规划 → flash 并行执行 → 强模型聚合。"""
        matrix = load_matrix(self.matrix_path)
        parallelism = max_parallel or int(matrix.get("parallelism", 4))

        plan: list[str] | None = None
        if planner is not None:
            # ① 深度理解 + 规划 (强模型)
            plan_result = await planner(prompt, "plan")
            plan_text = str(plan_result.get("output", "") or "")
            if plan_text:
                import re as _re

                plan = [t.strip() for t in _re.split(r"[\n\n]+", plan_text)
                        if t.strip() and not t.strip().startswith(("#", "- 概述", "概要"))]
                plan = plan[:parallelism * 2]
            self._audit_write({"action": "long_plan", "ts": time.time(),
                               "plan_items": len(plan or [])})

        if plan:
            # ② flash 并行执行规划项
            t0 = time.time()
            results = await asyncio.gather(
                *[caller(item, i) for i, item in enumerate(plan)],
                return_exceptions=True,
            )
            normalized = [
                {"ok": True, "output": str(r)} if isinstance(r, Exception)
                else (r if isinstance(r, dict) else {"ok": False, "error": str(r)})
                for r in results
            ]
            elapsed = round(time.time() - t0, 3)
            # ③ 强模型聚合 (深度综合)
            aggregate_text = ""
            if planner is not None:
                agg_input = "\n\n".join(
                    f"[部分{i+1}]\n{str(r.get('output', ''))[:1500]}"
                    for i, r in enumerate(normalized) if r.get("ok"))
                agg = await planner(agg_input, "aggregate")
                aggregate_text = str(agg.get("output", "") or "")
            return {
                "parallel": True,
                "planner": True,
                "chunks": len(plan),
                "elapsed_s": elapsed,
                "ok": any(r.get("ok") for r in normalized),
                "output": aggregate_text or "\n\n".join(
                    f"[部分{i+1}]\n{str(r.get('output', ''))[:800]}"
                    for i, r in enumerate(normalized)),
                "aggregated": aggregate_text,
                "plan": plan,
            }

        # 无规划器 → 原规则切分并行
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
        priority: str = "normal",
        budget: float | None = None,
    ) -> dict[str, Any]:
        """别名入口: 决策 → 单发/并行 → 质量闸门 (低质量升级重试 1 次)。

        caller: 装配层注入的单次调用函数, 接收 {"provider", "model", "messages", "tools"}
        """
        decision = self.route(messages, tools, priority=priority, budget=budget)
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

            planner_caller = None
            if "planner" in load_matrix(self.matrix_path):
                matrix_p = load_matrix(self.matrix_path)["planner"]

                async def _planner(input_text: str, phase: str) -> dict[str, Any]:
                    res = await caller({
                        "provider": matrix_p["provider"],
                        "model": matrix_p["model"],
                        "endpoint": matrix_p.get("endpoint"),
                        "messages": [{"role": "user",
                                      "content": (
                                          "深度理解以下长文并给出任务拆解规划, \n"
                                          "输出编号任务列表(每行一个):\n"
                                          if phase == "plan" else
                                          "综合以下各部分结果, 给出完整一致的最终回答:\n"
                                      ) + input_text}],
                        "tools": None,
                    })
                    content = ""
                    try:
                        content = str(res["choices"][0]["message"].get("content", ""))
                    except (KeyError, IndexError, TypeError):
                        content = str(res.get("output", ""))
                    return {"ok": bool(content), "output": content}

            return await self.dispatch_long(prompt, _chunk_caller,
                                            title="长文并行回答",
                                            planner=planner_caller)
        result = await caller({
            "provider": decision["provider"],
            "model": decision["model"],
            "messages": messages,
            "tools": tools,
        })
        # 质量闸门: 低质量 → 升级 frontier/upgrade_target 重试 1 次
        gate = quality_check(result)
        result["route"] = decision["route"]
        result["alias"] = decision["alias"]
        result["gate"] = gate
        if not gate["ok"]:
            matrix = load_matrix(self.matrix_path)
            upgrade = matrix.get("upgrade_target") or matrix.get("frontier")
            if upgrade and upgrade.get("model") != decision["model"]:
                retry = await caller({
                    "provider": upgrade["provider"],
                    "model": upgrade["model"],
                    "messages": messages,
                    "tools": tools,
                })
                retry["route"] = decision["route"]
                retry["alias"] = decision["alias"]
                retry["gate"] = {"ok": True, "reason": "upgraded",
                                 "from": decision["model"], "to": upgrade["model"]}
                self._audit_write({"action": "gate_upgrade", "ts": time.time(),
                                   "route": decision["route"],
                                   "from": decision["model"], "to": upgrade["model"],
                                   "reason": gate["reason"]})
                return retry
        return result


llm_router = LLMRouter()


__all__ = ["LLMRouter", "llm_router", "split_prompt"]
