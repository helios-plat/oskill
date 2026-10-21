"""oskill: 具身运动学计算与硬件协议序列化 (无状态纯数学).

纯数学与协议算法: 笛卡尔坐标 → 逆运动学 → 关节参数 → 字节流.
处理万向节死锁 (gimbal lock) 和边界限幅。

遵循 oskill 红线: 零外部依赖，纯函数.
"""

from __future__ import annotations

import json
import math
from typing import Any


def _embodied_kinematics_serialize(
    target_xyz: tuple[float, float, float],
    max_radius: float = 1.0,
) -> dict[str, Any]:
    """纯数学计算：坐标校验、逆运动学、关节参数转换与字节序列化.

    算法:
    1. 笛卡尔坐标 (x, y, z) → 球坐标 (r, θ, φ)
    2. 边界限幅检查 (软限位)
    3. 万向节死锁处理 (r≈0 或 z≈r 时 atan2/acos 不稳定)
    4. 关节参数 → JSON → bytes

    Args:
        target_xyz: 目标笛卡尔坐标 (x, y, z) 单位: 米
        max_radius: 最大工作半径 (米)

    Returns:
        {
            "valid": bool,
            "raw_dict": dict | None,
            "payload_bytes": bytes | None,
            "error": str | None,
            "gimbal_lock_detected": bool,
        }
    """
    x, y, z = target_xyz

    # 输入有效性校验
    if not all(math.isfinite(v) for v in target_xyz):
        return {
            "valid": False,
            "raw_dict": None,
            "payload_bytes": None,
            "error": "坐标包含非有限值 (inf/nan)",
            "gimbal_lock_detected": False,
        }

    # 欧氏距离
    distance = math.sqrt(x * x + y * y + z * z)

    # 物理边界限幅 (软限位)
    if distance > max_radius:
        return {
            "valid": False,
            "raw_dict": None,
            "payload_bytes": None,
            "error": f"目标坐标超限: distance={distance:.4f} > max_radius={max_radius}",
            "gimbal_lock_detected": False,
        }

    # 万向节死锁检测与处理
    gimbal_lock = False

    # θ = atan2(y, x) — 在 (0,0) 处无定义 (万向节死锁)
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        theta = 0.0
        gimbal_lock = True  # 万向节死锁: 无法确定水平方向
    else:
        theta = math.atan2(y, x)

    # φ = acos(z/r) — 在 r=0 或 z≈±r 时数值不稳定
    if distance < 1e-12:
        phi = 0.0
        gimbal_lock = True  # 原点死锁
    elif abs(z - distance) < 1e-12:
        phi = 0.0  # 正上方
    elif abs(z + distance) < 1e-12:
        phi = math.pi  # 正下方
    else:
        # 钳制 z/distance 在 [-1, 1] 防止 acos 越界
        ratio = max(-1.0, min(1.0, z / distance))
        phi = math.acos(ratio)

    # 组装符合边缘微控制器的协议格式
    command_dict = {
        "joint_1_rad": round(theta, 6),
        "joint_2_rad": round(phi, 6),
        "extension_m": round(distance, 6),
        "timestamp_sync": True,
        "gimbal_lock": gimbal_lock,
    }

    # 转化为物理层传输的字节流 (紧凑 JSON)
    payload_bytes = json.dumps(command_dict, separators=(",", ":")).encode("utf-8")

    return {
        "valid": True,
        "raw_dict": command_dict,
        "payload_bytes": payload_bytes,
        "error": None,
        "gimbal_lock_detected": gimbal_lock,
    }
