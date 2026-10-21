"""oskill: 张量内存步长与偏移量计算 (无状态纯数学).

针对视觉（视频帧 HWC）或音频，计算物理内存中的偏移量和总字节数。

遵循 oskill 红线: 纯算法，零外部依赖.
"""

from __future__ import annotations

from typing import Any


def _buffer_stride_alignment(
    shape: tuple[int, ...],
    dtype_size: int,
) -> dict[str, Any]:
    """根据数据维度和类型大小，计算总分配字节数与步长 (Strides).

    行优先 (C-order) 布局:
        strides[i] = dtype_size * prod(shape[i+1:])
        total_bytes = strides[0] * shape[0]

    Args:
        shape: 张量形状，如 (H, W, C) 或 (Batch, Seq, Hidden)
        dtype_size: 每个元素的字节数 (float32=4, uint8=1, float64=8)

    Returns:
        {
            "valid": bool,
            "total_bytes": int,
            "strides": tuple[int, ...],
            "shape": tuple[int, ...],
        }
    """
    if not shape or any(d <= 0 for d in shape) or dtype_size <= 0:
        return {
            "valid": False,
            "total_bytes": 0,
            "strides": (),
            "shape": shape,
            "error": "无效的 shape 或 dtype_size",
        }

    # 计算 strides: C-order
    strides: list[int] = []
    current_stride = dtype_size
    for dim in reversed(shape):
        strides.append(current_stride)
        current_stride *= dim
    strides.reverse()
    total_bytes = current_stride

    return {
        "valid": True,
        "total_bytes": total_bytes,
        "strides": tuple(strides),
        "shape": shape,
    }
