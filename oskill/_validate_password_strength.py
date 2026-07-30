"""oskill.validate_password_strength — 密码强度校验(纯规则,不涉及哈希/存储)。

策略(SPEC 未给出精确规则,本次自由裁量设计):长度 >= 8,且同时含大写、
小写、数字、特殊字符各至少一个——常见的"强密码"四要素策略。
"""

from __future__ import annotations

import re

_MIN_LENGTH = 8
_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_DIGIT = re.compile(r"\d")
_HAS_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def validate_password_strength(pwd: str) -> bool:
    """校验密码是否满足强密码四要素:长度 >= 8 + 大写 + 小写 + 数字 + 特殊字符。

    Args:
        pwd: 待校验的明文密码。

    Returns:
        全部四项都满足则 True,否则 False。不抛异常(弱密码是正常业务
        结果,不是异常输入)。
    """
    if len(pwd) < _MIN_LENGTH:
        return False
    return bool(
        _HAS_UPPER.search(pwd)
        and _HAS_LOWER.search(pwd)
        and _HAS_DIGIT.search(pwd)
        and _HAS_SPECIAL.search(pwd)
    )
