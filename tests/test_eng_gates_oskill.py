"""Tests for S1–S5 engineering skills."""

from __future__ import annotations

from pathlib import Path

from oskill.archive_agent_notes import archive_agent_notes
from oskill.code_review import code_review
from oskill.find_simplifications import find_simplifications
from oskill.pre_push_checks import pre_push_checks
from oskill.record_browser_gif import record_browser_gif


def test_pre_push_checks_writes_report_and_skips_empty(tmp_path: Path) -> None:
    rec = pre_push_checks(
        str(tmp_path),
        files=[],
        diff_since_fn=lambda **k: {"ok": True, "changed": [], "files": [], "diff": ""},
        run_checks_fn=lambda **k: {
            "ok": True,
            "skipped": True,
            "reason": "no changes",
            "commands": [],
        },
    )
    assert rec["ok"] is True
    assert rec["skipped"] is True
    assert rec["report_path"]
    assert Path(rec["report_path"]).is_file()


def test_pre_push_checks_fail_when_checks_fail(tmp_path: Path) -> None:
    rec = pre_push_checks(
        str(tmp_path),
        files=["foo.py"],
        run_checks_fn=lambda **k: {
            "ok": False,
            "skipped": False,
            "reason": "pytest failed",
            "commands": [
                {
                    "name": "pytest_related",
                    "ran": True,
                    "code": 1,
                    "cmd": ["pytest", "tests/test_foo.py"],
                }
            ],
        },
    )
    assert rec["ok"] is False
    assert "pytest failed" in rec["reason"]


def test_code_review_heuristic_security_and_mock_llm(tmp_path: Path) -> None:
    src = tmp_path / "app.py"
    src.write_text("def f():\n    return eval(user)\n", encoding="utf-8")

    rec = code_review(
        str(tmp_path),
        files=["app.py"],
        diff="eval",
        llm_call=lambda prompt: (
            '[{"file":"app.py","line":2,"severity":"medium",'
            '"category":"lifecycle","message":"no test"}]'
        ),
        diff_since_fn=lambda **k: {"ok": True, "changed": ["app.py"], "diff": "eval"},
    )
    assert rec["verdict"] == "fail"
    cats = {f["category"] for f in rec["findings"]}
    assert "security" in cats
    assert "lifecycle" in cats
    assert Path(rec["report_path"]).is_file()


def test_find_simplifications_never_writes_business_source(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def helper():\n    return 2\n", encoding="utf-8")
    rec = find_simplifications(str(tmp_path), files=["a.py", "b.py"])
    assert rec["ok"] is True
    assert rec["written_business_source"] == []
    assert rec["proposal_paths"]
    for path in rec["proposal_paths"]:
        assert "/.veya-project/engineering/" in path.replace("\\", "/")
    kinds = {p["kind"] for p in rec["proposals"]}
    assert "duplication" in kinds


def test_archive_agent_notes_promotes_high_value(tmp_path: Path) -> None:
    inbox = tmp_path / ".veya-project" / "engineering" / "notes-inbox"
    inbox.mkdir(parents=True)
    (inbox / "host.md").write_text("# GPU\n\nNever reboot this shared host.\n", encoding="utf-8")
    (inbox / "chat.md").write_text("today i poked the logs lol\n", encoding="utf-8")
    rec = archive_agent_notes(str(tmp_path))
    titles_p = {x["title"] for x in rec["promoted"]}
    titles_s = {x["title"] for x in rec["suppressed"]}
    assert "GPU" in titles_p
    assert any("chat" in t.lower() or "today" in t.lower() or t == "chat" for t in titles_s)
    assert rec["written_business_source"] == []


def test_record_browser_gif_blocked_reason(tmp_path: Path) -> None:
    rec = record_browser_gif(
        str(tmp_path),
        url="http://127.0.0.1:9/",
        capture_fn=lambda **k: {
            "ok": False,
            "reason": "playwright not installed; will not fabricate a clip",
        },
    )
    assert rec["ok"] is False
    assert "playwright" in rec["reason"]
    assert rec["path"] == ""
    assert Path(rec["note_path"]).is_file()
    assert "not" in Path(rec["note_path"]).read_text(encoding="utf-8").lower()
