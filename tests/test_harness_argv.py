"""harness_argv snapshots — no I/O."""

from __future__ import annotations

from oskill._harness_argv import harness_argv


def test_claude_streaming_and_model() -> None:
    rec = harness_argv("claude", "fix it", model="sonnet", streaming=True)
    assert rec["ok"] is True
    assert rec["argv"][:3] == ["claude", "-p", "fix it"]
    assert "--output-format" in rec["argv"]
    assert rec["argv"][-2:] == ["--model", "sonnet"]


def test_codex_default() -> None:
    rec = harness_argv("codex", "hi")
    assert rec["argv"] == [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "hi",
    ]


def test_master_rejected() -> None:
    rec = harness_argv("master", "hi")
    assert rec["ok"] is False
    assert "not a harness" in rec["error"]


def test_extra_and_bin() -> None:
    rec = harness_argv("pi", "hi", bin="/opt/pi", extra=["--quiet"])
    assert rec["argv"][0] == "/opt/pi"
    assert rec["argv"][-1] == "--quiet"


def test_package_export_is_the_function() -> None:
    import oskill

    assert callable(oskill.harness_argv)
    assert oskill.harness_argv("master", "x")["ok"] is False
