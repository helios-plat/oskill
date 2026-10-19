"""Tests for oskill.evaluate_rbac_permissions."""

from __future__ import annotations

from oskill._evaluate_rbac_permissions import evaluate_rbac_permissions


class TestEvaluateRbacPermissions:
    def test_exact_match_allowed(self):
        roles = [{"name": "editor", "permissions": ["products:read"]}]
        assert evaluate_rbac_permissions(roles, resource="products:read") is True

    def test_no_match_denied(self):
        roles = [{"name": "editor", "permissions": ["products:read"]}]
        assert evaluate_rbac_permissions(roles, resource="orders:delete") is False

    def test_wildcard_star_allows_everything(self):
        roles = [{"name": "admin", "permissions": ["*"]}]
        assert evaluate_rbac_permissions(roles, resource="orders:delete") is True

    def test_prefix_wildcard_matches_scoped_resource(self):
        roles = [{"name": "order_manager", "permissions": ["orders:*"]}]
        assert evaluate_rbac_permissions(roles, resource="orders:delete") is True

    def test_prefix_wildcard_does_not_leak_to_other_resources(self):
        roles = [{"name": "order_manager", "permissions": ["orders:*"]}]
        assert evaluate_rbac_permissions(roles, resource="products:delete") is False

    def test_multiple_roles_any_match_allows(self):
        roles = [
            {"name": "viewer", "permissions": ["products:read"]},
            {"name": "order_manager", "permissions": ["orders:*"]},
        ]
        assert evaluate_rbac_permissions(roles, resource="orders:delete") is True

    def test_empty_roles_denied(self):
        assert evaluate_rbac_permissions([], resource="orders:read") is False

    def test_role_missing_permissions_key_denied(self):
        roles = [{"name": "empty_role"}]
        assert evaluate_rbac_permissions(roles, resource="orders:read") is False
