"""oskill.agent_discovery — Discovery-First 资源目录 + Anti-Noise 决策验证 (md2wechat 3O 内化)。

两项机制:
  1. **Discovery-First** — 声明式资源目录 (providers/themes/prompts/layouts/
     skills...), Agent 面对不确定先 discover() 而不是猜; 资源只暴露路由字段
     (name/kind/description), 详情按需 show()。
  2. **Anti-Noise 决策验证器** — 5 条确定性检查 (源自 md2wechat AGENTS.md):
     可观察 / 确定性 / 可解释 / 无副作用 / 防真实错误。验证一个 agent 决策
     是否 pass, 返回结构化报告 (不靠主观质量启发式)。

零 veya 反向依赖: 纯数据结构 + 规则检查。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── 1. Discovery-First 资源目录 ──────────────────────────────────────

# 主观/不可观察信号词 (用于反噪声检查)
_SUBJECTIVE_WORDS = (
    "好", "美", "优雅", "自然", "生动", "高级", "简洁", "易读", "专业",
    "nice", "beautiful", "elegant", "polished", "professional", "great",
    "高质量", "优质", "awesome", "clean",
)
_ACTION_WORDS = ("写入", "发布", "上传", "删除", "发送", "write", "publish",
                 "upload", "delete", "send", "commit", "push")


@dataclass(frozen=True)
class Resource:
    """一个可发现资源 (路由元数据)。

    Attributes:
        name: 资源名。
        kind: 资源类型 (provider/theme/prompt/layout/skill/...)。
        description: 路由提示。
        loadable: 是否可按需加载详情。
    """

    name: str
    kind: str
    description: str = ""
    loadable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind,
                "description": self.description, "loadable": self.loadable}


class ResourceCatalog:
    """声明式资源目录: 注册 → discover 路由 → show 详情。"""

    def __init__(self) -> None:
        self._resources: dict[tuple[str, str], Resource] = {}  # (kind, name)
        self._details: dict[tuple[str, str], Any] = {}

    def register(self, resource: Resource, *, detail: Any = None) -> None:
        """注册一个资源 (幂等覆盖)。detail 为可选详情负载。"""
        self._resources[(resource.kind, resource.name)] = resource
        if detail is not None:
            self._details[(resource.kind, resource.name)] = detail

    def register_many(
        self, resources: list[Resource], *, details: dict[str, Any] | None = None
    ) -> None:
        """批量注册。details 键为 "kind:name"。"""
        for resource in resources:
            detail = (details or {}).get(f"{resource.kind}:{resource.name}")
            self.register(resource, detail=detail)

    def discover(self, kind: str | None = None) -> list[Resource]:
        """列出资源 (Discovery-First 统一入口)。

        Args:
            kind: 按类型过滤; None 返回全部。

        Returns:
            资源列表 (kind, name 排序)。
        """
        items = [
            r for (k, _), r in self._resources.items()
            if kind is None or k == kind
        ]
        items.sort(key=lambda r: (r.kind, r.name))
        return items

    def kinds(self) -> list[str]:
        """已注册资源类型。"""
        return sorted({k for k, _ in self._resources})

    def show(self, kind: str, name: str) -> Resource:
        """取资源; 不存在抛 KeyError。"""
        key = (kind, name)
        if key not in self._resources:
            raise KeyError(f"unknown resource {kind}:{name!r}; "
                           f"available: {[r.name for r in self.discover(kind)]}")
        return self._resources[key]

    def detail(self, kind: str, name: str) -> Any:
        """取资源详情 (未注册详情返回 None)。"""
        return self._details.get((kind, name))

    def capabilities(self) -> dict[str, Any]:
        """capabilities 聚合视图 (Agent 开场发现用)。"""
        return {
            "kinds": self.kinds(),
            "counts": {kind: len([r for r in self.discover(kind)]) for kind in self.kinds()},
            "resources": [r.to_dict() for r in self.discover()],
        }


# ── 2. Anti-Noise 决策验证器 ─────────────────────────────────────────

@dataclass
class DecisionVerdict:
    """一次决策验证的结论。"""

    decision: str
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def to_dict(self) -> dict[str, Any]:
        return {"decision": self.decision, "checks": self.checks,
                "failures": self.failures, "ok": self.ok}


class AntiNoiseValidator:
    """md2wechat 5 条反噪声检查: 可观察/确定性/可解释/无副作用/防真实错误。"""

    def validate(self, decision: str, *, evidence: list[str] | None = None) -> DecisionVerdict:
        """验证一个 agent 决策是否 pass anti-noise。

        Args:
            decision: 决策描述 (如 "建议把标题改成 X")。
            evidence: 支撑证据 (可观察信号)。

        Returns:
            DecisionVerdict (checks + failures)。
        """
        checks = {
            "observable": self.is_observable(decision),
            "no_side_effect": self.no_side_effect(decision),
        }
        checks["deterministic"] = self.is_deterministic(decision, evidence)
        checks["explainable"] = self.is_explainable(decision, evidence)
        checks["prevents_real_error"] = self.prevents_real_error(decision, evidence)
        failures = [name for name, ok in checks.items() if not ok]
        return DecisionVerdict(decision=decision, checks=checks, failures=failures)

    # 1. 可观察: 决策不含主观质量词
    def is_observable(self, decision: str) -> bool:
        lowered = decision.lower()
        return not any(word in lowered for word in _SUBJECTIVE_WORDS)

    # 2. 确定性: 相同输入 → 相同决策 (规则可复现)
    def is_deterministic(self, decision: str, evidence: list[str] | None) -> bool:
        if not evidence:
            return True  # 无证据依赖 → 纯规则决策, 确定
        # 证据必须含可观察信号 (数字/路径/枚举值), 不能全是主观描述
        observable_signals = 0
        for item in evidence:
            if re.search(r"\d|[\w./-]+\.(md|json|ts|py|html)|--\w+|=|ready|blocker", item):
                observable_signals += 1
        return observable_signals >= 1

    # 3. 可解释: 决策能由证据支撑 (有证据时)
    def is_explainable(self, decision: str, evidence: list[str] | None) -> bool:
        if not evidence:
            return True  # 纯规则建议 (如 lint 规则) 自身可解释
        return bool(evidence) and any(len(e) > 3 for e in evidence)

    # 4. 无副作用: 决策不含写/发/删等隐含副作用
    def no_side_effect(self, decision: str) -> bool:
        lowered = decision.lower()
        return not any(word in lowered for word in _ACTION_WORDS)

    # 5. 防真实错误: 决策指向真实的错误下一步 (可观察阻断)
    def prevents_real_error(self, decision: str, evidence: list[str] | None) -> bool:
        if not evidence:
            return True
        # 有证据说明确实存在障碍/风险 → 防真实错误; 无实质证据 → 锦上添花
        return any(
            re.search(r"(fail|block|error|missing|invalid|limit|"
                      r"超限|缺失|失败|越界|超过|超出)", item, re.I)
            for item in evidence
        )
