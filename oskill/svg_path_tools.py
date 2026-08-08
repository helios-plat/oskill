"""oskill.svg_path_tools — SVG 路径生成辅助 (Pixel2Motion 机制 3O 内化)。

在 svg_craft 工艺检查之上补生成辅助:
  * **path_bbox** — path d 的包围盒 (解析后计算);
  * **path_center** — 几何中心 (transform-origin 依据);
  * **simplify_line** — 折线简化 (Douglas-Peucker, 降噪点);
  * **fit_smooth_cubic** — 点列 → 平滑三次贝塞尔 (Catmull-Rom → 贝塞尔,
    G1 连续, Pixel2Motion few-curve 拟合基础)。
零 veya 反向依赖: 纯几何。
"""

from __future__ import annotations

import math
from typing import Any

from oskill.svg_craft import parse_path


def path_bbox(d: str) -> dict[str, float] | None:
    """path d 的包围盒。

    Args:
        d: SVG path data。

    Returns:
        {x, y, width, height} 或 None (空路径)。

    Example:
        >>> b = path_bbox("M0 0 L10 0 L10 10 Z")
        >>> b["width"]
        10.0
    """
    segments = parse_path(d)
    if not segments:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for seg in segments:
        xs.extend([seg.start[0], seg.end[0]])
        ys.extend([seg.start[1], seg.end[1]])
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {"x": min_x, "y": min_y, "width": max_x - min_x, "height": max_y - min_y}


def path_center(d: str) -> tuple[float, float] | None:
    """path d 的几何中心 (transform-origin: center 依据)。

    Returns:
        (cx, cy) 或 None。
    """
    bbox = path_bbox(d)
    if bbox is None:
        return None
    return (bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)


def simplify_line(
    points: list[tuple[float, float]], epsilon: float = 1.0
) -> list[tuple[float, float]]:
    """Douglas-Peucker 折线简化 (去噪点, Pixel2Motion 降 knots)。"""
    if len(points) <= 2:
        return list(points)

    def distance(point, start, end):  # noqa: ANN001
        x0, y0 = point
        x1, y1 = start
        x2, y2 = end
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x0 - x1, y0 - y1)
        t = max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)))
        px, py = x1 + t * dx, y1 + t * dy
        return math.hypot(x0 - px, y0 - py)

    def dp(indices: list[int]) -> list[int]:
        if len(indices) <= 2:
            return indices
        start, end = points[indices[0]], points[indices[-1]]
        max_dist = 0.0
        max_idx = -1
        for idx in indices[1:-1]:
            dist = distance(points[idx], start, end)
            if dist > max_dist:
                max_dist = dist
                max_idx = idx
        if max_dist > epsilon and max_idx != -1:
            left = dp(indices[: indices.index(max_idx) + 1])
            right = dp(indices[indices.index(max_idx) :])
            return left[:-1] + right
        return [indices[0], indices[-1]]

    kept = dp(list(range(len(points))))
    return [points[idx] for idx in kept]


def fit_smooth_cubic(
    points: list[tuple[float, float]],
    *,
    tension: float = 0.5,
) -> list[dict[str, Any]]:
    """点列 → 平滑三次贝塞尔 (Catmull-Rom → 贝塞尔, G1 连续)。

    Pixel2Motion few-curve 拟合基础: 用少曲线解析路径表达平滑轮廓。

    Args:
        points: 控制点列。
        tension: 张力 (0.5 标准)。

    Returns:
        [{control1, control2, end}] 贝塞尔段列表。

    Example:
        >>> segs = fit_smooth_cubic([(0, 0), (10, 5), (20, 0)])
        >>> len(segs)
        2
    """
    if len(points) < 2:
        return []
    segments: list[dict[str, Any]] = []
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (
            p1[0] + (p2[0] - p0[0]) * tension / 6,
            p1[1] + (p2[1] - p0[1]) * tension / 6,
        )
        c2 = (
            p2[0] - (p3[0] - p1[0]) * tension / 6,
            p2[1] - (p3[1] - p1[1]) * tension / 6,
        )
        segments.append({"control1": c1, "control2": c2, "end": p2})
    return segments


def render_cubic_path(points: list[tuple[float, float]], *, tension: float = 0.5) -> str:
    """点列 → SVG path d (M + C 段, 平滑拟合)。"""
    if not points:
        return ""
    segments = fit_smooth_cubic(points, tension=tension)
    parts = [f"M{points[0][0]} {points[0][1]}"]
    for seg in segments:
        c1 = seg["control1"]
        c2 = seg["control2"]
        end = seg["end"]
        parts.append(f"C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {end[0]} {end[1]}")
    return " ".join(parts)


__all__ = ["fit_smooth_cubic", "path_bbox", "path_center", "render_cubic_path", "simplify_line"]
