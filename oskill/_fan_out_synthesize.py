"""oskill.fan_out_synthesize — best-of-N / leader-synthesizer 共识 (orca / Grok-Heavy 范式内化)。

把"同一任务扇给 N 个候选 → 比对 → 合并/择优"内化为**任务无关的纯异步编排**原语:

  * ``generate``   async (task, i) -> candidate     注入的候选生成器 (通常绑 LLM, 靠 i/温度制造多样性);
  * ``synthesize`` async (task, candidates) -> merged  leader 综合 (有则优先, = Grok leader-synthesizer);
  * ``judge``      (task, candidates) -> best_index    打分择优 (synthesize 缺省时用);
  * 二者都缺 → 退化为多数票 (相同候选票高者胜), 再退化为首个。

纯编排: 无自有 I/O, 全部注入, ``asyncio.gather`` 并发。与 ``llm_factor_debate`` 同风格但
可复用、任务无关。**selective by design**: 何时启用由调用方决定 (只有高歧义/高影响任务
才值得多花算力扇出), 原语本身不做该判断。
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

Candidate = Any


async def fan_out_and_synthesize(
    task: str,
    *,
    generate: Callable[[str, int], Awaitable[Candidate]],
    n: int = 3,
    synthesize: Callable[[str, list[Candidate]], Awaitable[Candidate]] | None = None,
    judge: Callable[[str, list[Candidate]], int] | None = None,
    concurrency: int | None = None,
) -> dict[str, Any]:
    """扇出 n 个候选并收敛。返回 {chosen, candidates, n, method, errors}。

    generate 抛异常的分支被丢弃 (记入 errors); 全失败 → chosen=None (调用方回退)。
    n<=1 或只剩一个候选 → 直接返回该候选 (不浪费 synthesize/judge)。
    """
    n = max(1, int(n))
    sem = asyncio.Semaphore(concurrency) if concurrency and concurrency > 0 else None

    async def _one(i: int) -> Candidate:
        if sem is None:
            return await generate(task, i)
        async with sem:
            return await generate(task, i)

    results = await asyncio.gather(*[_one(i) for i in range(n)], return_exceptions=True)
    candidates = [r for r in results if not isinstance(r, BaseException)]
    errors = [f"{type(r).__name__}: {r}" for r in results if isinstance(r, BaseException)]

    if not candidates:
        return {"chosen": None, "candidates": [], "n": n, "method": "none", "errors": errors}
    if len(candidates) == 1:
        return {
            "chosen": candidates[0],
            "candidates": candidates,
            "n": n,
            "method": "single",
            "errors": errors,
        }
    if synthesize is not None:
        merged = await synthesize(task, candidates)
        return {
            "chosen": merged,
            "candidates": candidates,
            "n": n,
            "method": "synthesize",
            "errors": errors,
        }
    if judge is not None:
        idx = judge(task, candidates)
        idx = idx if isinstance(idx, int) and 0 <= idx < len(candidates) else 0
        return {
            "chosen": candidates[idx],
            "candidates": candidates,
            "n": n,
            "method": "judge",
            "errors": errors,
        }
    # 无 synthesize/judge → 多数票 (相同候选票高者胜), 平票取首个。
    keyed = [_key(c) for c in candidates]
    best_key, count = Counter(keyed).most_common(1)[0]
    if count > 1:
        chosen = candidates[keyed.index(best_key)]
        method = "majority"
    else:
        chosen = candidates[0]
        method = "first"
    return {"chosen": chosen, "candidates": candidates, "n": n, "method": method, "errors": errors}


def _key(candidate: Candidate) -> str:
    """把候选归一化成可比较的键 (多数票用)。"""
    if isinstance(candidate, str):
        return candidate.strip()
    try:
        import json

        return json.dumps(candidate, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(candidate)
