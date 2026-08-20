"""isolation_policy is a pure table."""

from __future__ import annotations

from oskill._isolation_policy import isolation_policy


def test_chat_verify_is_honest_process() -> None:
    rec = isolation_policy("chat_verify")
    assert rec["ok"] is True
    assert rec["isolation"] == "process"
    assert rec["block_network"] is False
    assert "NOT blocked" in rec["note"]


def test_pytest_eval_wants_docker() -> None:
    rec = isolation_policy("pytest_eval")
    assert rec["isolation"] == "docker"
    assert rec["block_network"] is True


def test_unknown_purpose_fails() -> None:
    rec = isolation_policy("quantum_jail")
    assert rec["ok"] is False
    assert "unknown purpose" in rec["error"]


def test_harness_host_is_process_with_network() -> None:
    rec = isolation_policy("harness_host")
    assert rec["ok"] is True
    assert rec["isolation"] == "process"
    assert rec["block_network"] is False
    assert "not deleted" in rec["note"]


def test_hosted_chat_verify_is_opensandbox() -> None:
    rec = isolation_policy("chat_verify", profile="hosted")
    assert rec["ok"] is True
    assert rec["isolation"] == "opensandbox"
    assert rec["block_network"] is True
    assert rec["profile"] == "hosted"


def test_hosted_hicode_workspace_is_opensandbox() -> None:
    rec = isolation_policy("hicode_workspace", profile="hosted")
    assert rec["isolation"] == "opensandbox"
    assert rec["block_network"] is True


def test_local_default_unchanged() -> None:
    rec = isolation_policy("chat_verify", profile="local")
    assert rec["isolation"] == "process"
    assert rec["block_network"] is False
