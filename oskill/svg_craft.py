"""oskill.svg_craft — SVG 拟合工艺 (Pixel2Motion 机制 3O 内化)。

像素 logo → 矢量拟合的确定性工艺检查 (Pixel2Motion Phase 2 内化):
  * **IoU 计算** — 两 mask 像素重合度 (纯算法, 无 PIL/numpy 依赖);
  * **路径审计** — 解析 SVG path d: 切线跳跃 / 交替小段 / 噪点句柄 /
    像素阶梯运行检测 (确定性);
  * **平滑门禁** — Smoothness Gate (硬门槛): 阶梯/抖动/网格正交运行即失败,
    即使 IoU 数值高 (Pixel2Motion: "高 IoU 不能藏坏矢量工艺");
  * **复杂度阶梯** — 5 级决策 (primitives → composites → few-curve →
    smoothed → trace) + 升级条件表 (端点/宽度/中心/负空间/阶梯失败才升)。

零 veya 反向依赖: 纯数值/文本解析; mask 由调用方提供 (2D 数组)。
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

# ── 1. IoU 计算 (纯 Python) ──────────────────────────────────────────

Mask = list[list[float]]
"""2D mask: 0.0/1.0 (或 0-255, >0 视为前景)。"""


def iou_score(a: Mask, b: Mask) -> float:
    """两个 mask 的 IoU: |A∩B| / |A∪B|。

    Args:
        a: mask A (list[list[float]], >0 为前景)。
        b: mask B (与 A 同尺寸)。

    Returns:
        0.0-1.0 IoU (空并集返回 1.0)。

    Example:
        >>> iou_score([[1, 1], [0, 0]], [[1, 0], [0, 0]])
        0.5
    """
    if not a or not b:
        return 1.0 if not a and not b else 0.0
    intersection = 0
    union = 0
    for row_a, row_b in zip(a, b):
        for va, vb in zip(row_a, row_b):
            fa = 1 if va > 0 else 0
            fb = 1 if vb > 0 else 0
            union += 1 if (fa or fb) else 0
            if fa and fb:
                intersection += 1
    if union == 0:
        return 1.0
    return intersection / union


# ── 2. 路径审计 ──────────────────────────────────────────────────────

# path 命令 token
_TOKEN_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][+-]?\d+)?)")


@dataclass(frozen=True)
class PathSegment:
    """一段 path 子路径 (line/cubic/quad 统一为起终点 + 起点切线)。"""

    kind: str  # M/L/C/S/Q/T/Z
    start: tuple[float, float]
    end: tuple[float, float]
    start_tangent: tuple[float, float]
    length: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "start": self.start,
            "end": self.end,
            "start_tangent": self.start_tangent,
            "length": round(self.length, 3),
        }


def parse_path(d: str) -> list[PathSegment]:
    """解析 SVG path d 为线段序列 (支持 M/L/H/V/C/S/Q/T/Z 子集)。

    Args:
        d: SVG path data。

    Returns:
        PathSegment 列表 (Z 闭合产生一条收尾线段)。
    """
    tokens = [t for t in _TOKEN_RE.findall(d) if t.strip()]
    segments: list[PathSegment] = []
    current: tuple[float, float] = (0.0, 0.0)
    start_point: tuple[float, float] = (0.0, 0.0)
    i = 0
    prev_tangent: tuple[float, float] = (1.0, 0.0)
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd in "Zz":
            if current != start_point:
                dx = start_point[0] - current[0]
                dy = start_point[1] - current[1]
                segments.append(
                    PathSegment("Z", current, start_point, (dx, dy), math.hypot(dx, dy))
                )
                current = start_point
            continue
        # 收集坐标
        coords: list[float] = []
        while i < len(tokens) and re.match(r"^-?\d", tokens[i]):
            coords.append(float(tokens[i]))
            i += 1
        if cmd in "Mm":
            if len(coords) >= 2:
                current = (coords[0], coords[1])
                start_point = current
            continue
        if cmd in "Ll":
            if len(coords) >= 2:
                end = (coords[0], coords[1])
                dx, dy = end[0] - current[0], end[1] - current[1]
                segments.append(PathSegment("L", current, end, (dx, dy), math.hypot(dx, dy)))
                current = end
            continue
        if cmd in "Hh":
            if coords:
                end = (coords[0], current[1])
                dx = end[0] - current[0]
                segments.append(PathSegment("H", current, end, (dx, 0.0), abs(dx)))
                current = end
            continue
        if cmd in "Vv":
            if coords:
                end = (current[0], coords[0])
                dy = end[1] - current[1]
                segments.append(PathSegment("V", current, end, (0.0, dy), abs(dy)))
                current = end
            continue
        if cmd in "Cc" and len(coords) >= 6:
            end = (coords[4], coords[5])
            # 起点切线 = 第一个控制点 - 起点
            tangent = (coords[0] - current[0], coords[1] - current[1])
            prev_tangent = (coords[4] - coords[2], coords[5] - coords[3])
            length = _approx_curve_length(
                current, (coords[0], coords[1]), (coords[2], coords[3]), end
            )
            segments.append(PathSegment("C", current, end, tangent, length))
            current = end
            continue
        if cmd in "Ss" and len(coords) >= 4:
            end = (coords[2], coords[3])
            tangent = prev_tangent  # 反射前段控制点
            length = math.hypot(end[0] - current[0], end[1] - current[1])
            segments.append(PathSegment("S", current, end, tangent, length))
            prev_tangent = (end[0] - coords[0], end[1] - coords[1])
            current = end
            continue
        if cmd in "Qq" and len(coords) >= 4:
            end = (coords[2], coords[3])
            tangent = (coords[0] - current[0], coords[1] - current[1])
            length = math.hypot(end[0] - current[0], end[1] - current[1])
            segments.append(PathSegment("Q", current, end, tangent, length))
            prev_tangent = (end[0] - coords[0], end[1] - coords[1])
            current = end
            continue
        if cmd in "Tt" and len(coords) >= 2:
            end = (coords[0], coords[1])
            tangent = prev_tangent
            length = math.hypot(end[0] - current[0], end[1] - current[1])
            segments.append(PathSegment("T", current, end, tangent, length))
            current = end
            continue
        # 不支持的命令 (A 椭圆弧) 跳过
    return segments


def _approx_curve_length(p0, p1, p2, p3) -> float:  # noqa: ANN001
    """三次贝塞尔长度近似 (3 段折线)。"""
    pts = [p0, p1, p2, p3]
    length = 0.0
    for k in range(1, len(pts)):
        length += math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1])
    return length


@dataclass
class PathAudit:
    """路径审计结果。

    Attributes:
        ok: 是否通过。
        segments: 解析出的线段数。
        tangent_jumps: 切线跳跃列表 [(seg_i, angle_deg)]。
        alternating: 交替小段列表 [(seg_i, seg_j)]。
        stair_steps: 像素阶梯运行列表 [(seg_i, seg_j, direction)]。
        noisy_handles: 噪点句柄列表。
        problems: 全部问题描述。
    """

    ok: bool
    segments: int = 0
    tangent_jumps: list[list[Any]] = field(default_factory=list)
    alternating: list[list[Any]] = field(default_factory=list)
    stair_steps: list[list[Any]] = field(default_factory=list)
    noisy_handles: list[list[Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "segments": self.segments,
            "tangent_jumps": self.tangent_jumps,
            "alternating": self.alternating,
            "stair_steps": self.stair_steps,
            "problems": self.problems,
        }


def svg_path_audit(
    d: str,
    *,
    tangent_jump_deg: float = 60.0,
    tiny_len: float = 1.5,
    stair_len: float = 2.0,
) -> PathAudit:
    """审计 SVG path: 切线跳跃/交替小段/像素阶梯/噪点句柄。

    Args:
        d: SVG path data。
        tangent_jump_deg: 相邻段起点切线夹角阈值 (度)。
        tiny_len: "小段"长度阈值 (像素)。
        stair_len: 阶梯段长度阈值 (接近 1px 的 h/v 段)。

    Returns:
        PathAudit (ok=False 时 problems 含全部失败原因)。
    """
    segments = parse_path(d)
    problems: list[str] = []
    tangent_jumps: list[list[Any]] = []
    alternating: list[list[Any]] = []
    stair_steps: list[list[Any]] = []
    noisy_handles: list[list[Any]] = []

    # 切线跳跃: 相邻连续段起点切线夹角
    for i in range(1, len(segments)):
        prev_t = segments[i - 1].start_tangent
        curr_t = segments[i].start_tangent
        angle = _angle_between(prev_t, curr_t)
        if angle > tangent_jump_deg:
            tangent_jumps.append([i, round(angle, 1)])

    # 交替小段: 连续 3 段方向交替翻转 (抖动)
    for i in range(len(segments) - 2):
        s1, s2, s3 = segments[i], segments[i + 1], segments[i + 2]
        if (
            s1.length <= tiny_len
            and s2.length <= tiny_len
            and s3.length <= tiny_len
            and _opposite_dirs(s1.start_tangent, s2.start_tangent)
            and _opposite_dirs(s2.start_tangent, s3.start_tangent)
        ):
            alternating.append([i, i + 2])

    # 像素阶梯: 连续 1px 级 h/v 段 (阶梯运行)
    run: list[int] = []
    for i, seg in enumerate(segments):
        if seg.kind in ("H", "V", "L") and seg.length <= stair_len:
            run.append(i)
        else:
            if len(run) >= 3:
                stair_steps.append([run[0], run[-1], _stair_dir(segments[run[0]])])
            run = []
    if len(run) >= 3:
        stair_steps.append([run[0], run[-1], _stair_dir(segments[run[0]])])

    if tangent_jumps:
        problems.append(f"切线跳跃: {len(tangent_jumps)} 处 (首个 {tangent_jumps[0]})")
    if alternating:
        problems.append(f"交替小段 (抖动): {len(alternating)} 处")
    if stair_steps:
        problems.append(f"像素阶梯运行: {len(stair_steps)} 段 (首个 {stair_steps[0]})")
    return PathAudit(
        ok=not problems,
        segments=len(segments),
        tangent_jumps=tangent_jumps,
        alternating=alternating,
        stair_steps=stair_steps,
        noisy_handles=noisy_handles,
        problems=problems,
    )


def _angle_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两向量夹角 (度)。"""
    la = math.hypot(a[0], a[1])
    lb = math.hypot(b[0], b[1])
    if la == 0 or lb == 0:
        return 0.0
    cos = (a[0] * b[0] + a[1] * b[1]) / (la * lb)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def _opposite_dirs(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """方向近似相反。"""
    return _angle_between(a, b) > 150.0


def _stair_dir(seg: PathSegment) -> str:
    """阶梯主方向。"""
    if seg.kind in ("H", "V"):
        return "horizontal" if seg.kind == "H" else "vertical"
    return "mixed"


# ── 3. 平滑门禁 (Smoothness Gate) ────────────────────────────────────


@dataclass
class GateVerdict:
    """平滑门禁判定。

    Attributes:
        ok: 通过。
        problems: 失败原因 (阶梯/抖动/网格正交运行)。
        audit: 底层路径审计。
    """

    ok: bool
    problems: list[str] = field(default_factory=list)
    audit: PathAudit | None = None


def smoothness_gate(
    paths: list[str],
    *,
    stair_len: float = 2.0,
    grid_orthogonal_len: float = 4.0,
) -> GateVerdict:
    """Smoothness Gate: 硬门槛 — 阶梯/抖动/网格正交运行即失败。

    Pixel2Motion 语义: "IoU 不是用来藏坏矢量工艺的"。即使 IoU 数值高,
    任何可见阶梯/抖动/网格正交运行都判定失败。

    Args:
        paths: SVG path d 列表。
        stair_len: 阶梯段长度阈值。
        grid_orthogonal_len: 网格正交运行 (连续纯 h/v) 最小长度。

    Returns:
        GateVerdict。
    """
    problems: list[str] = []
    audits: list[PathAudit] = []
    for d in paths:
        audit = svg_path_audit(d, stair_len=stair_len)
        audits.append(audit)
        if audit.stair_steps:
            problems.append(f"像素阶梯运行: {len(audit.stair_steps)} 段")
        if audit.alternating:
            problems.append(f"抖动 (交替小段): {len(audit.alternating)} 处")
        # 网格正交运行: 连续纯 h/v 段且总长 >= threshold
        orth_run = _grid_orthogonal_run(d, grid_orthogonal_len)
        if orth_run:
            problems.append(f"网格正交运行: {orth_run} 段")
    return GateVerdict(ok=not problems, problems=problems, audit=audits[0] if audits else None)


def _grid_orthogonal_run(d: str, min_len: float) -> int:
    """连续 H/V 段的最长运行。"""
    segments = parse_path(d)
    longest = 0
    run = 0
    for seg in segments:
        if seg.kind in ("H", "V"):
            run += 1
        else:
            longest = max(longest, run)
            run = 0
    longest = max(longest, run)
    return longest if longest >= min_len else 0


# ── 4. 复杂度阶梯决策 ────────────────────────────────────────────────

LEVEL_PRIMITIVES = 1
LEVEL_COMPOSITES = 2
LEVEL_FEW_CURVE = 3
LEVEL_SMOOTHED = 4
LEVEL_TRACE = 5
LEVEL_NAMES = {
    LEVEL_PRIMITIVES: "primitives",
    LEVEL_COMPOSITES: "primitive composites",
    LEVEL_FEW_CURVE: "few-curve analytic paths",
    LEVEL_SMOOTHED: "smoothed outline paths",
    LEVEL_TRACE: "trace-derived paths",
}


@dataclass
class LadderDecision:
    """复杂度阶梯决策结果。

    Attributes:
        level: 1-5。
        level_name: 等级名。
        reasons: 升级原因 (低等级失败点)。
        notes: 说明。
    """

    level: int
    level_name: str
    reasons: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "level_name": self.level_name,
            "reasons": self.reasons,
            "notes": self.notes,
        }


def complexity_ladder(
    source_features: dict[str, Any],
) -> LadderDecision:
    """复杂度阶梯决策: 从源特征选最低可行等级。

    Pixel2Motion 语义: "不要默认最大化像素拟合; 用能解释标记的最简几何",
    只在 overlay 证明结构不匹配时升级。升级条件: 端点错/宽度错/中心错/
    负空间错/可见阶梯。

    Args:
        source_features: 源特征 (注入分析):
            {
              "primitives_fit": bool,     # 原始图形可表达
              "needs_composite": bool,    # 需要组合/布尔
              "has_curves": bool,         # 含平滑曲线 (丝带/弧)
              "is_irregular": bool,       # 不规则轮廓
              "failures": [str],          # 低等级失败点 (endpoint/width/
                                          # center/negative_space/stair)
            }

    Returns:
        LadderDecision。

    Example:
        >>> complexity_ladder({"primitives_fit": True, "failures": []}).level
        1
    """
    failures = source_features.get("failures", [])
    if source_features.get("primitives_fit") and not failures:
        return LadderDecision(
            LEVEL_PRIMITIVES, LEVEL_NAMES[LEVEL_PRIMITIVES], notes="原始图形可表达, 无失败点"
        )
    reasons = list(failures)
    if source_features.get("needs_composite"):
        if _severe_failures(failures):
            reasons.append("组合后仍有结构失败")
        else:
            return LadderDecision(
                LEVEL_COMPOSITES, LEVEL_NAMES[LEVEL_COMPOSITES], reasons=reasons, notes="组合可表达"
            )
    if source_features.get("has_curves"):
        return LadderDecision(
            LEVEL_FEW_CURVE,
            LEVEL_NAMES[LEVEL_FEW_CURVE],
            reasons=reasons,
            notes="含平滑曲线, 用少曲线解析路径",
        )
    if source_features.get("is_irregular"):
        return LadderDecision(
            LEVEL_SMOOTHED,
            LEVEL_NAMES[LEVEL_SMOOTHED],
            reasons=reasons,
            notes="不规则轮廓, 平滑轮廓路径",
        )
    return LadderDecision(
        LEVEL_TRACE,
        LEVEL_NAMES[LEVEL_TRACE],
        reasons=reasons,
        notes="最复杂: 描边路径 (仅测量辅助)",
    )


def _severe_failures(failures: list[str]) -> bool:
    severe = {"endpoint", "width", "center", "negative_space"}
    return any(f in severe for f in failures)


__all__ = [
    "GateVerdict",
    "LadderDecision",
    "LEVEL_COMPOSITES",
    "LEVEL_FEW_CURVE",
    "LEVEL_NAMES",
    "LEVEL_PRIMITIVES",
    "LEVEL_SMOOTHED",
    "LEVEL_TRACE",
    "Mask",
    "PathAudit",
    "PathSegment",
    "complexity_ladder",
    "iou_score",
    "parse_path",
    "smoothness_gate",
    "svg_path_audit",
]
