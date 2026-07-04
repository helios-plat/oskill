"""Tests for oskill.compose_drift_detect (aegis DESIGN §3.7)."""

from __future__ import annotations

from oskill.compose_drift_detect import Drift, ServiceDrift, compose_drift_detect


class TestComposeDriftDetect:
    def test_in_sync(self):
        declared = {"web": {"image": "nginx:1.2"}, "db": {"image": "pg:16"}}
        running = {"web": {"image": "nginx:1.2"}, "db": {"image": "pg:16"}}
        r = compose_drift_detect(declared=declared, running=running)
        assert isinstance(r, Drift)
        assert r.in_sync is True
        assert r.added == [] and r.removed == [] and r.changed == []

    def test_added_declared_not_running(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx"}, "cache": {"image": "redis"}},
            running={"web": {"image": "nginx"}},
        )
        assert r.added == ["cache"]
        assert r.in_sync is False

    def test_removed_running_not_declared(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx"}},
            running={"web": {"image": "nginx"}, "orphan": {"image": "x"}},
        )
        assert r.removed == ["orphan"]
        assert r.in_sync is False

    def test_changed_image(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx:1.3"}},
            running={"web": {"image": "nginx:1.2"}},
        )
        assert len(r.changed) == 1
        d = r.changed[0]
        assert isinstance(d, ServiceDrift)
        assert d.service == "web" and d.field == "image"
        assert d.declared == "nginx:1.3" and d.running == "nginx:1.2"
        assert r.in_sync is False

    def test_running_as_list_normalized(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx"}},
            running=[{"name": "web", "image": "nginx"}],
        )
        assert r.in_sync is True

    def test_running_list_capital_name_key(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx"}},
            running=[{"Name": "web", "image": "nginx"}],
        )
        assert r.in_sync is True

    def test_custom_compare_fields(self):
        r = compose_drift_detect(
            declared={"web": {"image": "nginx", "restart": "always"}},
            running={"web": {"image": "nginx", "restart": "no"}},
            compare_fields=["image", "restart"],
        )
        assert len(r.changed) == 1
        assert r.changed[0].field == "restart"
