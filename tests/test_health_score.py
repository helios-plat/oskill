"""Tests for health_score (FDE 书第5章 3O 内化)。"""

from __future__ import annotations

from oskill.health_score import (
    GRADE_AT_RISK,
    GRADE_CRITICAL,
    GRADE_HEALTHY,
    LAYER_BUSINESS,
    LAYER_CUSTOMER,
    LAYER_DELIVERY,
    LAYER_ORG,
    Metric,
    compute_health,
    normalize,
    watchdog,
)


def _four_layer_metrics() -> list[Metric]:
    return [
        Metric("deploy_success", LAYER_DELIVERY, weight=1.0, threshold=70),
        Metric("active_users", LAYER_CUSTOMER, weight=1.0, threshold=60),
        Metric("revenue_growth", LAYER_BUSINESS, weight=1.0, threshold=50),
        Metric("team_load", LAYER_ORG, weight=1.0, threshold=60, direction="low_better"),
    ]


def test_normalize_high_low():
    assert normalize(95) == 95
    assert normalize(120) == 100  # 封顶
    assert normalize(30, direction="low_better") == 70  # 低值反向


def test_healthy_all_good():
    metrics = _four_layer_metrics()
    report = compute_health(
        metrics,
        {
            "deploy_success": 95,
            "active_users": 90,
            "revenue_growth": 80,
            "team_load": 20,  # 低负载好
        },
    )
    assert report.grade == GRADE_HEALTHY
    assert report.score >= 70
    assert report.alerts == []
    assert report.layer_scores[LAYER_DELIVERY] >= 70


def test_at_risk_with_alert():
    metrics = _four_layer_metrics()
    report = compute_health(
        metrics,
        {
            "deploy_success": 95,
            "active_users": 30,  # 低活跃 → 预警
            "revenue_growth": 80,
            "team_load": 20,
        },
    )
    assert report.grade == GRADE_AT_RISK
    assert len(report.alerts) == 1
    assert report.alerts[0].metric == "active_users"
    assert report.alerts[0].layer == LAYER_CUSTOMER
    assert "回访" in report.alerts[0].intervention


def test_critical_low_score():
    metrics = _four_layer_metrics()
    report = compute_health(
        metrics,
        {
            "deploy_success": 10,
            "active_users": 5,
            "revenue_growth": 2,
            "team_load": 95,
        },
    )
    assert report.grade == GRADE_CRITICAL
    assert report.score < 50


def test_critical_business_alert():
    metrics = _four_layer_metrics()
    report = compute_health(
        metrics,
        {
            "deploy_success": 95,
            "active_users": 90,
            "revenue_growth": 10,  # 商业层预警 → critical
            "team_load": 20,
        },
    )
    assert report.grade == GRADE_CRITICAL
    assert any(a.layer == LAYER_BUSINESS for a in report.alerts)


def test_custom_intervention():
    metrics = [Metric("deploy_success", LAYER_DELIVERY, threshold=80)]
    report = compute_health(
        metrics,
        {"deploy_success": 50},
        interventions={"deploy_success": "重启发布管道并回滚"},
    )
    assert report.alerts[0].intervention == "重启发布管道并回滚"


def test_layer_independent_weighting():
    """各层独立加权: 一层异常不影响其他层得分。"""
    metrics = [
        Metric("a1", LAYER_DELIVERY, weight=1.0, threshold=70),
        Metric("a2", LAYER_DELIVERY, weight=3.0, threshold=70),
        Metric("c1", LAYER_CUSTOMER, weight=1.0, threshold=60),
    ]
    report = compute_health(metrics, {"a1": 10, "a2": 90, "c1": 90})
    # delivery 层: (10*1 + 90*3)/4 = 70; customer: 90
    assert report.layer_scores[LAYER_DELIVERY] == 70
    assert report.layer_scores[LAYER_CUSTOMER] == 90
    assert report.alerts and report.alerts[0].metric == "a1"


def test_watchdog_runs_and_intervenes():
    metrics = _four_layer_metrics()
    values = {"deploy_success": 95, "active_users": 90, "revenue_growth": 80, "team_load": 20}
    interventions: list[list] = []

    def values_fn():
        return dict(values)

    def intervene(alerts):
        interventions.append(alerts)

    reports = watchdog(metrics, values_fn, max_runs=2, intervene=intervene)
    assert len(reports) == 2
    assert reports[0].grade == GRADE_HEALTHY
    assert interventions == []  # 无预警 → 无干预

    # 触发预警的场景
    bad_values = {"deploy_success": 95, "active_users": 20, "revenue_growth": 80, "team_load": 20}
    reports2 = watchdog(metrics, lambda: dict(bad_values), max_runs=1, intervene=intervene)
    assert reports2[0].alerts
    assert len(interventions) == 1


def test_watchdog_run_callback():
    metrics = [Metric("m", LAYER_DELIVERY, threshold=50)]
    seen: list[float] = []

    def run_fn(report):
        seen.append(report.score)

    watchdog(metrics, lambda: {"m": 80}, max_runs=3, run_fn=run_fn)
    assert len(seen) == 3
    assert seen[0] == 80
