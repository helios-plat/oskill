"""Tests for shared_language (mattpocock CONTEXT.md / domain-modeling 3O 内化)."""

from __future__ import annotations

from pathlib import Path

from oskill.shared_language import (
    AdrDraft,
    read_glossary,
    should_write_adr,
    upsert_term,
    write_adr,
)


class TestGlossary:
    def test_read_list_format(self, tmp_path: Path) -> None:
        path = tmp_path / "CONTEXT.md"
        path.write_text(
            "# 项目\n\n## Glossary\n\n"
            "- **materialization cascade** — 内容实体落盘连锁\n\n## Other\n",
            encoding="utf-8",
        )
        glossary = read_glossary(path)
        assert glossary["materialization cascade"] == "内容实体落盘连锁"

    def test_upsert_new_term(self, tmp_path: Path) -> None:
        path = tmp_path / "CONTEXT.md"
        path.write_text("# 项目\n", encoding="utf-8")
        result = upsert_term(path, "tracer bullet", "能贯穿全链的最小实现")
        assert result["created"] is True
        assert result["total_terms"] == 1
        text = path.read_text(encoding="utf-8")
        assert "## Glossary" in text
        assert "**tracer bullet**" in text

    def test_upsert_updates_existing(self, tmp_path: Path) -> None:
        path = tmp_path / "CONTEXT.md"
        path.write_text(
            "## Glossary\n\n- **term** — 旧定义\n",
            encoding="utf-8",
        )
        result = upsert_term(path, "term", "新定义")
        assert result["created"] is False
        text = path.read_text(encoding="utf-8")
        assert "旧定义" not in text
        assert "新定义" in text
        assert read_glossary(path)["term"] == "新定义"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert read_glossary(tmp_path / "nope.md") == {}


class TestAdrGate:
    def test_all_three_gates_required(self) -> None:
        assert (
            should_write_adr(reversible=False, obvious_without_context=True, real_tradeoff=True)
            is True
        )
        assert (
            should_write_adr(reversible=True, obvious_without_context=True, real_tradeoff=True)
            is False
        )
        assert (
            should_write_adr(reversible=False, obvious_without_context=False, real_tradeoff=True)
            is False
        )
        assert (
            should_write_adr(reversible=False, obvious_without_context=True, real_tradeoff=False)
            is False
        )


class TestWriteAdr:
    def test_writes_numbered_file(self, tmp_path: Path) -> None:
        draft = AdrDraft(
            title="用共享语言取代临时术语",
            context="agent 与团队术语不一致",
            decision="建立 CONTEXT.md 术语表",
            consequences="初期成本高, 后期收益大",
        )
        target = write_adr(tmp_path / "adr", draft)
        assert target.endswith("0001-用共享语言取代临时术语.md")
        content = Path(target).read_text(encoding="utf-8")
        assert "# 1. 用共享语言取代临时术语" in content
        assert "## Decision" in content

    def test_index_auto_increments(self, tmp_path: Path) -> None:
        (tmp_path / "adr").mkdir(parents=True)
        write_adr(tmp_path / "adr", AdrDraft("One", "c", "d", "e"))
        target2 = write_adr(tmp_path / "adr", AdrDraft("Two", "c", "d", "e"))
        assert "0002-" in target2
