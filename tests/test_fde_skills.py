"""Tests for mvd / playbook / productization_gate (FDE 书 3O 内化)。"""

from __future__ import annotations

from oskill.mvd import (
    PHASE_DAY1,
    PHASE_DAY4_5,
    RULE_DEADLINE,
    RULE_REAL_DATA,
    RULE_SCOPE_NOT_VALUE,
    MvdPipeline,
    mvd_check,
)
from oskill.playbook import (
    SECTION_DUE_DILIGENCE,
    SECTION_LESSONS,
    SECTION_METRICS,
    SECTION_PAIN_POINTS,
    PlaybookLibrary,
    ScenarioPlaybook,
)
from oskill.productization_gate import (
    DECISION_COMPONENTS,
    DECISION_KEEP_FIELD,
    DECISION_PRODUCTIZE,
    evaluate_productization,
)

# ── MVD 三军规 ───────────────────────────────────────────────────────


def test_mvd_check_all_pass():
    verdict = mvd_check(
        data_source="客户真实业务数据",
        scope_depth_kept=True,
        deadline_weeks=4,
    )
    assert verdict.ok is True
    assert verdict.violations == []


def test_mvd_check_fake_data_violates():
    verdict = mvd_check(
        data_source="脱敏样例数据",
        scope_depth_kept=True,
        deadline_weeks=4,
    )
    assert verdict.ok is False
    assert RULE_REAL_DATA in verdict.violations
    assert "坟墓" in verdict.details[RULE_REAL_DATA]["note"]


def test_mvd_check_scope_violation():
    verdict = mvd_check(
        data_source="客户真实业务数据",
        scope_depth_kept=False,
        deadline_weeks=4,
    )
    assert RULE_SCOPE_NOT_VALUE in verdict.violations


def test_mvd_check_deadline_violation():
    # 6 个月 = 概念验证坟墓再开工
    verdict = mvd_check(
        data_source="客户真实业务数据",
        scope_depth_kept=True,
        deadline_weeks=26,
    )
    assert RULE_DEADLINE in verdict.violations
    assert "坟墓" in verdict.details[RULE_DEADLINE]["note"]


# ── MVD 五步流水线 ──────────────────────────────────────────────────


def test_pipeline_advance_to_done():
    pipeline = MvdPipeline()
    assert pipeline.phase == "day0_prep"
    assert "筹备" in pipeline.current()
    pipeline.advance()  # day1
    pipeline.advance()  # day2_3
    pipeline.advance()  # day4_5
    assert pipeline.phase == PHASE_DAY4_5
    pipeline.advance()  # done
    assert pipeline.is_done() is True
    assert len(pipeline.log) == 4


def test_pipeline_advance_after_done_raises():
    import pytest

    pipeline = MvdPipeline()
    for _ in range(4):  # 4 次 → done
        pipeline.advance()
    with pytest.raises(RuntimeError, match="already done"):
        pipeline.advance()


def test_pipeline_summary():
    pipeline = MvdPipeline()
    pipeline.advance()
    summary = pipeline.summary()
    assert summary["phase"] == PHASE_DAY1
    assert summary["max_days"] == 5


# ── 打法手册七件套 ──────────────────────────────────────────────────


def test_playbook_sections_completeness():
    playbook = ScenarioPlaybook(scenario="金融反洗钱场景", owner="团队A")
    assert playbook.completeness()["complete"] is False
    playbook.set_section(SECTION_PAIN_POINTS, ["痛点1"])
    playbook.set_section(SECTION_DUE_DILIGENCE, ["高危信号1"])
    playbook.set_section(SECTION_METRICS, ["指标1"])
    assert playbook.completeness()["filled"] == 3
    assert "landmines" in playbook.completeness()["missing"]


def test_playbook_invalid_section_raises():
    import pytest

    playbook = ScenarioPlaybook(scenario="x")
    with pytest.raises(ValueError, match="invalid section"):
        playbook.set_section("nope", [])


def test_playbook_library_lifecycle():
    library = PlaybookLibrary()
    playbook = ScenarioPlaybook(scenario="律所知识库场景", owner="团队B")
    playbook.set_section(SECTION_PAIN_POINTS, ["痛点点"])
    library.register(playbook)
    assert library.list_scenarios() == ["律所知识库场景"]

    # 复盘强制更新 (硬关卡)
    library.mandatory_update("律所知识库场景", SECTION_LESSONS, "客户 X 的教训")
    assert library.get("律所知识库场景").sections[SECTION_LESSONS] == ["客户 X 的教训"]

    # 版本自增
    library.register(ScenarioPlaybook(scenario="律所知识库场景", owner="团队C"))
    assert library.get("律所知识库场景").version == 2

    # 折旧后不可取
    library.deprecate("律所知识库场景")
    assert library.get("律所知识库场景") is None


def test_playbook_review_prunes_deprecated():
    library = PlaybookLibrary()
    library.register(ScenarioPlaybook(scenario="场景1", owner="a"))
    library.deprecate("场景1")
    # 模拟折旧已超过半年
    library.playbooks["场景1"].deprecated_ts = 0.0
    report = library.review(now=100 * 86400)
    assert "场景1" in report["removed"]


# ── 产品化四问 ──────────────────────────────────────────────────────


def test_productize_when_all_pass():
    verdict = evaluate_productization(
        independent_customers=5,
        generalization_cost=2.0,
        expected_customers=10,
        per_customer_savings=4.0,
        usable_by_non_coders=True,
        field_room=True,
    )
    assert verdict.decision == DECISION_PRODUCTIZE
    assert verdict.answers["q1_commonality"]["ok"] is True


def test_keep_field_when_commonality_low():
    verdict = evaluate_productization(
        independent_customers=1,
        generalization_cost=2.0,
        expected_customers=10,
        per_customer_savings=4.0,
        usable_by_non_coders=True,
        field_room=True,
    )
    assert verdict.decision == DECISION_KEEP_FIELD
    assert "共性不足" in verdict.reasons[0]


def test_components_when_common_and_worth_but_not_usable():
    verdict = evaluate_productization(
        independent_customers=4,
        generalization_cost=2.0,
        expected_customers=10,
        per_customer_savings=4.0,
        usable_by_non_coders=False,
        field_room=False,
    )
    assert verdict.decision == DECISION_COMPONENTS
    assert any("组件层" in r for r in verdict.reasons)


def test_keep_field_when_generalization_not_worth():
    verdict = evaluate_productization(
        independent_customers=4,
        generalization_cost=50.0,
        expected_customers=2,
        per_customer_savings=1.0,
        usable_by_non_coders=True,
        field_room=True,
    )
    assert verdict.decision == DECISION_KEEP_FIELD
    assert "泛化不值" in verdict.reasons[0]
