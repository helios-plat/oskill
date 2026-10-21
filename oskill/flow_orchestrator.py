"""oskill.flow_orchestrator — 动态流程编排 (Auto-Deep-Research flow 3O 内化)。

workflows 注册 + broker 分发 + 动态流程 (运行时变更步骤):
  * **FlowRegistry** — 流程注册/查找 (递归扫描/显式注册);
  * **FlowBroker** — 按条件分发到流程 (路由);
  * **FlowRunner** — 步骤序列执行: 顺序/条件跳转/动态插入步骤
    (AutoAgent flow broker/dynamic 的机制层);
  * 步骤错误可配置 (fail-fast / 跳过 / 重试)。

零 veya 反向依赖: 步骤执行函数由调用方注入; 纯编排。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

StepFn = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
"""步骤执行: (inputs, context) → 输出 (并入 context)。"""


@dataclass
class FlowStep:
    """一个流程步骤。

    Attributes:
        id: 步骤 id。
        name: 步骤名。
        fn: 执行函数 (注入)。
        on_error: fail / skip / retry (默认 fail)。
        retries: on_error=retry 时的重试次数。
        jump_to: 执行后跳转的步骤 id (None = 顺序下一个)。
    """

    id: str
    name: str
    fn: StepFn
    on_error: str = "fail"
    retries: int = 0
    jump_to: str | None = None


@dataclass
class FlowResult:
    """流程执行结果。"""

    ok: bool
    steps_run: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class FlowRegistry:
    """流程注册表 (workflows 递归注册模式)。"""

    def __init__(self) -> None:
        self.flows: dict[str, list[FlowStep]] = {}

    def register(self, name: str, steps: list[FlowStep]) -> None:
        """注册流程 (幂等覆盖)。"""
        self.flows[name] = list(steps)

    def get(self, name: str) -> list[FlowStep] | None:
        return self.flows.get(name)

    def list_flows(self) -> list[str]:
        return sorted(self.flows)


class FlowBroker:
    """流程分发器: 按条件选流程。"""

    def __init__(self, registry: FlowRegistry | None = None) -> None:
        self.registry = registry or FlowRegistry()
        self.routes: list[tuple[Callable[[dict[str, Any]], str], str]] = []

    def add_route(self, condition: Callable[[dict[str, Any]], str], flow: str) -> None:
        """添加路由: 条件函数返回 flow 名 (返回空串不匹配)。"""
        self.routes.append((condition, flow))

    def dispatch(self, inputs: dict[str, Any]) -> str | None:
        """按条件分发 (首个匹配)。"""
        for condition, flow in self.routes:
            if condition(inputs):
                return flow
        return None


class FlowRunner:
    """步骤序列执行器 (顺序/条件跳转/动态插入)。"""

    def run(
        self,
        steps: list[FlowStep],
        inputs: dict[str, Any],
        *,
        insert_steps: list[FlowStep] | None = None,
    ) -> FlowResult:
        """执行步骤序列。

        Args:
            steps: 步骤列表。
            inputs: 输入变量。
            insert_steps: 动态插入的步骤 (追加到末尾前, 对应 dynamic flow)。

        Returns:
            FlowResult。
        """
        context: dict[str, Any] = dict(inputs)
        steps_run: list[str] = []
        by_id = {step.id: step for step in steps}
        order = list(steps)
        index = 0
        while index < len(order):
            step = order[index]
            steps_run.append(step.id)
            try:
                output = step.fn(inputs, context)
                if output:
                    context.update(output)
            except Exception as exc:  # noqa: BLE001
                if step.on_error == "skip":
                    context[f"{step.id}.error"] = f"{exc.__class__.__name__}: {exc}"
                elif step.on_error == "retry":
                    for attempt in range(step.retries):
                        try:
                            output = step.fn(inputs, context)
                            if output:
                                context.update(output)
                            break
                        except Exception:  # noqa: BLE001
                            if attempt == step.retries - 1:
                                return FlowResult(
                                    False, steps_run, context, error=f"{step.id}: retry exhausted"
                                )
                else:
                    return FlowResult(False, steps_run, context, error=f"{step.id}: {exc}")
            if step.jump_to and step.jump_to in by_id:
                index = order.index(by_id[step.jump_to])
                continue
            index += 1
        if insert_steps:
            for step in insert_steps:
                steps_run.append(f"insert:{step.id}")
                try:
                    output = step.fn(inputs, context)
                    if output:
                        context.update(output)
                except Exception as exc:  # noqa: BLE001
                    return FlowResult(False, steps_run, context, error=f"insert:{step.id}: {exc}")
        return FlowResult(True, steps_run, context)


__all__ = ["FlowBroker", "FlowRegistry", "FlowResult", "FlowRunner", "FlowStep"]
