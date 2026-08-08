"""Tests for daemon_runtime / embedding_service / browser_runner / secure_store
(第七批: computerd/embedding/browser/加密存储)。"""

from __future__ import annotations

import time

import pytest

from oskill.browser_runner import (
    BrowserRunner,
    run_browser_test,
)
from oskill.daemon_runtime import (
    DaemonLifecycle,
    DirWatcher,
    SyncSession,
)
from oskill.embedding_service import (
    EmbeddingProvider,
    EmbeddingService,
)
from oskill.secure_store import (
    SecureStore,
    SecureStoreError,
)

# ── daemon_runtime (computerd 机制) ─────────────────────────────────


def test_daemon_lifecycle_start_stop():
    calls = {"n": 0}

    def worker():
        calls["n"] += 1

    daemon = DaemonLifecycle("test", worker, heartbeat_interval_s=0.01)
    daemon.start()
    assert daemon.state.status == "running"
    time.sleep(0.05)
    assert calls["n"] >= 1
    health = daemon.health()
    assert health["ok"] is True
    daemon.stop()
    assert daemon.state.status == "stopped"


def test_daemon_health_stopped():
    daemon = DaemonLifecycle("x", lambda: None)
    assert daemon.health()["ok"] is False


def test_dir_watcher_changes(tmp_path):
    (tmp_path / "a.txt").write_text("v1", encoding="utf-8")
    watcher = DirWatcher(tmp_path)
    watcher.snapshot()
    (tmp_path / "b.txt").write_text("new", encoding="utf-8")
    (tmp_path / "a.txt").write_text("v2", encoding="utf-8")
    changes = watcher.changes_since()
    assert "b.txt" in changes["added"]
    assert "a.txt" in changes["changed"]
    assert changes["total"] == 2


def test_sync_session_push_pull(tmp_path):
    (tmp_path / "a.txt").write_text("v1", encoding="utf-8")
    watcher = DirWatcher(tmp_path)
    applied: list[str] = []
    session = SyncSession(watcher, lambda rel, kind: applied.append(f"{kind}:{rel}"))
    # 模拟工作区变更
    (tmp_path / "b.txt").write_text("x", encoding="utf-8")
    session.push()
    assert any("added:b.txt" in a for a in applied)
    pulled = session.pull({"changed": ["a.txt"]})
    assert pulled == 1


# ── embedding_service (Dify) ────────────────────────────────────────


def test_embedding_service_cache():
    calls = {"n": 0}
    service = EmbeddingService()
    service.register(
        EmbeddingProvider(
            "local",
            lambda t: calls.__setitem__("n", calls["n"] + 1) or [1.0, 0.0],
        )
    )
    v1 = service.embed("hello")
    v2 = service.embed("hello")  # 缓存命中
    assert v1 == v2
    assert calls["n"] == 1
    assert service.stats()["cached_vectors"] == 1


def test_embedding_batch_respects_batch_size():
    calls: list[list[str]] = []
    service = EmbeddingService()
    service.register(
        EmbeddingProvider(
            "local",
            lambda t: calls.append([t]) or [1.0],
            batch_size=2,
        )
    )
    vectors = service.embed_batch(["a", "b", "c"])
    assert len(vectors) == 3
    assert len(calls) == 3  # 每条单独 (注入函数单条)


def test_embedding_unknown_provider():
    service = EmbeddingService()
    service.register(EmbeddingProvider("a", lambda t: [1.0]))
    with pytest.raises(ValueError, match="provider not found"):
        service.embed("x", provider_id="nope")


# ── browser_runner (Cypress) ────────────────────────────────────────


def test_browser_runner_available_requires_driver():
    runner = BrowserRunner()
    assert runner.available() is False
    result = runner.run_steps([{"command": "visit", "args": {"url": "/"}}])
    assert result["ok"] is False
    assert "driver" in result["error"]


def test_browser_runner_steps_and_failure():
    def driver(command, args):
        if command == "assert_text":
            return "needle" in "some text"
        return True

    runner = BrowserRunner(driver)
    result = runner.run_steps(
        [
            {"command": "visit", "args": {"url": "/"}},
            {"command": "assert_text", "args": {"selector": "p", "contains": "missing"}},
        ]
    )
    assert result["ok"] is False
    assert result["failed_at"] == "assert_text"
    assert len(result["results"]) == 2


def test_run_browser_test_all_pass():
    result = run_browser_test(
        "t1",
        [
            {"command": "visit", "args": {"url": "/"}},
        ],
        driver=lambda c, a: True,
    )
    assert result["ok"] is True
    assert result["name"] == "t1"


# ── secure_store (freellmapi 加密存储) ─────────────────────────────


def test_secure_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("VEYA_MASTER_KEY", "test-master-key")
    store = SecureStore(tmp_path / "keys.json")
    store.put("openai", "sk-secret-123")
    assert store.get("openai") == "sk-secret-123"
    assert store.has("openai")
    # 持久化后新实例可读
    store2 = SecureStore(tmp_path / "keys.json")
    assert store2.get("openai") == "sk-secret-123"


def test_secure_store_master_key_required(tmp_path, monkeypatch):
    monkeypatch.delenv("VEYA_MASTER_KEY", raising=False)
    with pytest.raises(SecureStoreError, match="master key"):
        SecureStore(tmp_path / "keys.json")


def test_secure_store_wrong_key_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("VEYA_MASTER_KEY", "key-a")
    store = SecureStore(tmp_path / "keys.json")
    store.put("deepseek", "sk-x")
    monkeypatch.setenv("VEYA_MASTER_KEY", "key-b")
    store2 = SecureStore(tmp_path / "keys.json")
    with pytest.raises(SecureStoreError):
        store2.get("deepseek")


def test_secure_store_audit(tmp_path, monkeypatch):
    monkeypatch.setenv("VEYA_MASTER_KEY", "k")
    store = SecureStore(tmp_path / "keys.json")
    store.put("zhipu", "sk-z")
    store.get("zhipu", actor="agent-1")
    assert len(store.audit_log()) == 1
    assert store.audit_log()[0]["actor"] == "agent-1"
