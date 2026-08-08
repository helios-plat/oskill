"""oskill.health_score — 四层客户健康分 + 预警干预 (FDE 书第5章 3O 内化)。

源自《前线部署工程师》附录 A 的指标框架:
  * **四层指标** — delivery (项目做得对不对) / customer (客户活得怎么样) /
    business (生意值不值) / org (团队能不能走远);
  * **加权健康分** — 每项指标 (权重/阈值/方向) 归一化打分 → 加权合成 0-100
    → 分档 (healthy / at_risk / critical);
  * **预警干预** — 阈值触发预警 + 干预建议 (可接 notification_center);
  * **watchdog** — 周期性评估 → 预警 → 干预动作 (确定性轮询)。

零 veya 反向依赖: 指标值由调用方注入 (可接 operator_ledger/审计); 纯计算。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

LAYER_DELIVERY = "delivery"
LAYER_CUSTOMER = "customer"
LAYER_BUSINESS = "business"
LAYER_ORG = "org"
LAYERS = (LAYER_DELIVERY, LAYER_CUSTOMER, LAYER_BUSINESS, LAYER_ORG)

GRADE_HEALTHY = "healthy"
GRADE_AT_RISK = "at_risk"
GRADE_CRITICAL = "critical"


@dataclass(frozen=True)
class Metric:
    """一项健康指标。

    Attributes:
        name: 指标名。
        layer: 所属层 (delivery/customer/business/org)。
        weight: 层内权重 (同层归一化)。
        threshold: 健康阈值 (0-100; 低于该值触发预警)。
        direction: high_better (值越高越好) / low_better。
        description: 指标说明。
    """

    name: str
    layer: str
    weight: float = 1.0
    threshold: float = 60.0
    direction: str = "high_better"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "layer": self.layer,
            "weight": self.weight,
            "threshold": self.threshold,
            "direction": self.direction,
            "description": self.description,
        }


@dataclass
class HealthAlert:
    """一次预警 (阈值触发)。

    Attributes:
        metric: 触发的指标。
        value: 当前值。
        layer: 所属层。
        intervention: 干预建议。
        ts: 触发时间。
    """

    metric: str
    value: float
    layer: str
    intervention: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "layer": self.layer,
            "intervention": self.intervention,
            "ts": self.ts,
        }


@dataclass
class HealthReport:
    """健康分总报告。

    Attributes:
        score: 综合健康分 0-100。
        grade: healthy / at_risk / critical。
        layer_scores: 各层得分。
        alerts: 触发的预警。
        details: 各指标 {name: {value, normalized, status}}。
    """

    score: float
    grade: str
    layer_scores: dict[str, float] = field(default_factory=dict)
    alerts: list[HealthAlert] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "grade": self.grade,
            "layer_scores": self.layer_scores,
            "alerts": [a.to_dict() for a in self.alerts],
            "details": self.details,
        }


# ── 归一化 ───────────────────────────────────────────────────────────


def normalize(value: float, *, direction: str = "high_better") -> float:
    """指标值 → 0-100 归一化 (high_better: 值越高越好, 上限 100)。

    Args:
        value: 原始指标值 (假定已归一化到 0-100 或百分率)。
        direction: high_better / low_better。

    Returns:
        0-100 归一化值。
    """
    v = max(0.0, min(100.0, float(value)))
    return v if direction == "high_better" else 100.0 - v


# ── 健康分计算 ───────────────────────────────────────────────────────


def compute_health(
    metrics: list[Metric],
    values: dict[str, float],
    *,
    interventions: dict[str, str] | None = None,
) -> HealthReport:
    """计算四层加权健康分 + 触发预警。

    Args:
        metrics: 指标定义。
        values: 指标名 → 原始值。
        interventions: 指标名 → 干预建议 (默认按层给通用建议)。
        values: 注入的指标值。

    Returns:
        HealthReport (score/grade/layer_scores/alerts/details)。

    Example:
        >>> m = [Metric("deploy_success", "delivery", weight=1.0, threshold=70)]
        >>> r = compute_health(m, {"deploy_success": 95})
        >>> r.grade
        'healthy'
    """
    # 每层独立加权
    layer_weights: dict[str, float] = {}
    layer_weighted: dict[str, float] = {}
    details: dict[str, Any] = {}
    alerts: list[HealthAlert] = []
    for metric in metrics:
        raw = values.get(metric.name, 0.0)
        normalized = normalize(raw, direction=metric.direction)
        layer_weights[metric.layer] = layer_weights.get(metric.layer, 0.0) + metric.weight
        layer_weighted[metric.layer] = (
            layer_weighted.get(metric.layer, 0.0) + normalized * metric.weight
        )
        status = "ok" if normalized >= metric.threshold else "alert"
        details[metric.name] = {
            "value": raw,
            "normalized": normalized,
            "layer": metric.layer,
            "status": status,
        }
        if status == "alert":
            intervention = (interventions or {}).get(
                metric.name,
                _default_intervention(metric.layer),
            )
            alerts.append(
                HealthAlert(
                    metric=metric.name,
                    value=normalized,
                    layer=metric.layer,
                    intervention=intervention,
                )
            )
    layer_scores = {layer: layer_weighted[layer] / layer_weights[layer] for layer in layer_weights}
    if not layer_scores:
        return HealthReport(score=0.0, grade=GRADE_CRITICAL)
    score = sum(layer_scores.values()) / len(layer_scores)
    grade = _grade(score, alerts)
    return HealthReport(
        score=round(score, 1),
        grade=grade,
        layer_scores={k: round(v, 1) for k, v in layer_scores.items()},
        alerts=alerts,
        details=details,
    )


def _grade(score: float, alerts: list[HealthAlert]) -> str:
    """分档: critical 有预警且低分; at_risk 有预警; 其余 healthy。"""
    if alerts:
        if score < 50 or any(a.layer == LAYER_BUSINESS for a in alerts):
            return GRADE_CRITICAL
        return GRADE_AT_RISK
    return GRADE_HEALTHY


def _default_intervention(layer: str) -> str:
    """按层给通用干预建议。"""
    return {
        LAYER_DELIVERY: "检查部署成功率/交付质量, 修复 pipeline",
        LAYER_CUSTOMER: "客户活跃度下降, 安排回访/引导上手",
        LAYER_BUSINESS: "商业指标告警, 复查收入/续约风险",
        LAYER_ORG: "团队承压, 检查资源与排期",
    }.get(layer, "人工介入复核")


# ── Watchdog: 周期性评估 → 预警 → 干预 ──────────────────────────────

InterveneFn = Callable[[list[HealthAlert]], list[dict[str, Any]]]
"""干预执行函数: (预警列表) → 干预结果。"""


def watchdog(
    metrics: list[Metric],
    values_fn: Callable[[], dict[str, float]],
    *,
    interval_s: float = 60.0,
    max_runs: int | None = None,
    intervene: InterveneFn | None = None,
    run_fn: Callable[[HealthReport], None] | None = None,
) -> list[HealthReport]:
    """周期性评估: 采样 → 算健康分 → 触发预警 → (可选) 执行干预。

    Args:
        metrics: 指标定义。
        values_fn: 采样函数 (每次运行调用, 注入真实指标值)。
        interval_s: 轮询间隔秒数。
        max_runs: 最大运行次数; None 无限 (测试传小值)。
        intervene: 干预执行函数 (收到预警时调用)。
        run_fn: 每次运行的回调 (报告观测/记录)。

    Returns:
        全部运行报告 (同步执行; 用 run_fn 做异步观测)。
    """
    reports: list[HealthReport] = []
    runs = 0
    while max_runs is None or runs < max_runs:
        values = values_fn()
        report = compute_health(metrics, values)
        reports.append(report)
        if run_fn is not None:
            run_fn(report)
        if report.alerts and intervene is not None:
            intervene(report.alerts)
        runs += 1
        if max_runs is None:
            time.sleep(interval_s)
    return reports


__all__ = [
    "GRADE_AT_RISK",
    "GRADE_CRITICAL",
    "GRADE_HEALTHY",
    "HealthAlert",
    "HealthReport",
    "LAYERS",
    "LAYER_BUSINESS",
    "LAYER_CUSTOMER",
    "LAYER_DELIVERY",
    "LAYER_ORG",
    "Metric",
    "compute_health",
    "normalize",
    "watchdog",
]
