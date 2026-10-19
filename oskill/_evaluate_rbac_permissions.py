"""oskill.evaluate_rbac_permissions — 基于角色的资源访问判定。

权限字符串约定(SPEC 未给出精确格式,本次自由裁量设计):`"resource:action"`
形式的冒号分段字符串(如 ``"orders:read"``)。支持两种通配:
``"*"`` 匹配任意资源;``"orders:*"`` 匹配 ``orders:`` 前缀下的任意 action。
"""

from __future__ import annotations


def evaluate_rbac_permissions(roles: list, *, resource: str) -> bool:
    """判断 `roles` 中是否有任一角色的权限列表覆盖 `resource`。

    Args:
        roles: 角色列表,每项须含 ``permissions``(权限字符串列表)。
        resource: 待校验的资源标识(如 ``"orders:read"``)。

    Returns:
        任一角色的任一权限项精确匹配、或为 ``"*"``、或为
        ``"{prefix}:*"`` 且 resource 以 ``"{prefix}:"`` 开头,则返回 True。
    """
    for role in roles:
        for perm in role.get("permissions", []):
            if perm == "*" or perm == resource:
                return True
            if perm.endswith(":*") and resource.startswith(perm[:-1]):
                return True
    return False
