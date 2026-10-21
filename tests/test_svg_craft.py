"""Tests for svg_craft (Pixel2Motion 3O 内化)。"""

from __future__ import annotations

from oskill.svg_craft import (
    LEVEL_FEW_CURVE,
    LEVEL_PRIMITIVES,
    LEVEL_TRACE,
    complexity_ladder,
    iou_score,
    parse_path,
    smoothness_gate,
    svg_path_audit,
)

# ── IoU ──────────────────────────────────────────────────────────────


def test_iou_basic():
    assert iou_score([[1, 1], [0, 0]], [[1, 0], [0, 0]]) == 0.5
    assert iou_score([[1, 1], [1, 1]], [[1, 1], [1, 1]]) == 1.0
    assert iou_score([[1, 0], [0, 0]], [[0, 1], [0, 0]]) == 0.0


def test_iou_empty():
    assert iou_score([], []) == 1.0
    assert iou_score([], [[1]]) == 0.0


def test_iou_threshold_values():
    # >0 视为前景 (0-255 mask 兼容)
    a = [[255, 255], [0, 0]]
    b = [[200, 0], [0, 0]]
    assert iou_score(a, b) == 0.5


# ── 路径审计 ─────────────────────────────────────────────────────────


def test_parse_path_lines():
    segments = parse_path("M0 0 L10 0 L10 10 Z")
    assert len(segments) == 3
    assert segments[0].kind == "L"
    assert segments[0].end == (10.0, 0.0)
    assert segments[2].kind == "Z"  # 闭合线段


def test_parse_path_cubic():
    segments = parse_path("M0 0 C10 0 20 10 30 10")
    assert len(segments) == 1
    assert segments[0].kind == "C"
    assert segments[0].start_tangent == (10.0, 0.0)
    assert segments[0].length > 0


def test_path_audit_stair_step_detected():
    # 像素阶梯: 连续 1px 级 h/v 段
    d = "M0 0 H1 V1 H2 V2 H3 V3"
    audit = svg_path_audit(d, stair_len=2.0)
    assert audit.ok is False
    assert audit.stair_steps
    assert any("像素阶梯" in p for p in audit.problems)


def test_path_audit_smooth_passes():
    d = "M0 0 C30 0 60 10 90 10"
    audit = svg_path_audit(d)
    assert audit.ok is True


def test_path_audit_alternating_detected():
    # 交替小段: 方向来回翻转
    d = "M0 0 L0.5 0 L0 0.5 L0.5 0 L0 0.5"
    audit = svg_path_audit(d, tiny_len=1.0)
    assert audit.alternating


# ── 平滑门禁 ─────────────────────────────────────────────────────────


def test_smoothness_gate_ok():
    verdict = smoothness_gate(["M0 0 C30 0 60 10 90 10"])
    assert verdict.ok is True
    assert verdict.problems == []


def test_smoothness_gate_fails_on_stair():
    verdict = smoothness_gate(["M0 0 H1 V1 H2 V2 H3 V3"])
    assert verdict.ok is False
    assert any("阶梯" in p for p in verdict.problems)


def test_smoothness_gate_fails_on_grid_orthogonal():
    # 连续纯 h/v 运行 (网格正交)
    verdict = smoothness_gate(["M0 0 H10 V1 H20 V2"], grid_orthogonal_len=3)
    assert verdict.ok is False
    assert any("网格正交" in p for p in verdict.problems)


# ── 复杂度阶梯 ───────────────────────────────────────────────────────


def test_ladder_primitives_when_fit():
    decision = complexity_ladder({"primitives_fit": True, "failures": []})
    assert decision.level == LEVEL_PRIMITIVES
    assert decision.level_name == "primitives"


def test_ladder_escalates_on_failures():
    decision = complexity_ladder(
        {
            "primitives_fit": True,
            "failures": ["endpoint", "width"],
            "has_curves": True,
        }
    )
    assert decision.level >= LEVEL_FEW_CURVE
    assert "endpoint" in decision.reasons


def test_ladder_composites():
    decision = complexity_ladder(
        {
            "primitives_fit": False,
            "needs_composite": True,
            "failures": [],
        }
    )
    assert decision.level == 2
    assert decision.level_name == "primitive composites"


def test_ladder_trace_fallback():
    decision = complexity_ladder(
        {
            "primitives_fit": False,
            "needs_composite": True,
            "failures": ["endpoint", "width", "center"],
            "has_curves": False,
            "is_irregular": False,
        }
    )
    assert decision.level == LEVEL_TRACE


def test_ladder_to_dict():
    decision = complexity_ladder({"primitives_fit": True, "failures": []})
    data = decision.to_dict()
    assert data["level"] == LEVEL_PRIMITIVES
    assert data["level_name"] == "primitives"
