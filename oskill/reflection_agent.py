"""oskill.reflection_agent — Reflection 范式 (hello-agents 第4章 3O 内化)。

生成 → 自我反思 → 修正 循环 (AI 原生 Agent 经典范式, 补 agent_orchestrator
的 fc/react/plan 之外的第四范式):
  * **generate** — LLM 初版回答 (注入);
  * **critique** — 自我反思: 找缺点/漏洞 (注入, 或规则检查);
  * **revise** — 基于反思修正 (注入);
  * **ReflectionLoop** — 循环编排: 生成 → 反思 → 修正, 反思通过或无改善
    时停止, 最多 N 轮。
零 veya 反向依赖: 生成/反思/修正函数注入; 纯编排。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

GenerateFn = Callable[[str], str]
"""生成: (任务) → 初版回答。"""

CritiqueFn = Callable[[str], list[str]]
"""反思: (回答) → 问题列表 (空 = 通过)。"""

ReviseFn = Callable[[str, list[str]], str]
"""修正: (原回答, 问题列表) → 修正后回答。"""


@dataclass
class ReflectionResult:
    """Reflection 循环结果。

    Attributes:
        answer: 最终回答。
        rounds: 反思轮数。
        critiques: 每轮反思问题。
        stopped_reason: 停止原因 (critique_passed / no_improvement / max_rounds)。
    """

    answer: str
    rounds: int = 0
    critiques: list[list[str]] = field(default_factory=list)
    stopped_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer[:500],
            "rounds": self.rounds,
            "critiques": self.critiques,
            "stopped_reason": self.stopped_reason,
        }


class ReflectionLoop:
    """生成 → 反思 → 修正 循环编排。"""

    def __init__(self, *, max_rounds: int = 3) -> None:
        self.max_rounds = max_rounds

    def run(
        self,
        task: str,
        *,
        generate: GenerateFn,
        critique: CritiqueFn,
        revise: ReviseFn,
    ) -> ReflectionResult:
        """执行 Reflection 循环。

        Args:
            task: 任务。
            generate: 生成函数。
            critique: 反思函数 (空列表 = 通过)。
            revise: 修正函数。

        Returns:
            ReflectionResult。

        Example:
            >>> r = ReflectionLoop(max_rounds=2).run(
            ...     "t", generate=lambda t: "v1",
            ...     critique=lambda a: ["不够详细"] if len(a) < 10 else [],
            ...     revise=lambda a, c: a + " 补充")
            >>> r.answer
            'v1 补充'
        """
        answer = generate(task)
        critiques_log: list[list[str]] = []
        for round_num in range(self.max_rounds):
            problems = critique(answer)
            if not problems:
                return ReflectionResult(
                    answer=answer,
                    rounds=round_num,
                    critiques=critiques_log,
                    stopped_reason="critique_passed",
                )
            critiques_log.append(problems)
            revised = revise(answer, problems)
            if revised == answer:
                return ReflectionResult(
                    answer=answer,
                    rounds=round_num + 1,
                    critiques=critiques_log,
                    stopped_reason="no_improvement",
                )
            answer = revised
        return ReflectionResult(
            answer=answer,
            rounds=self.max_rounds,
            critiques=critiques_log,
            stopped_reason="max_rounds",
        )


__all__ = ["ReflectionLoop", "ReflectionResult"]
