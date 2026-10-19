"""Tests for rulebooks (agent-rules-books 3O 内化)."""

from __future__ import annotations

import pytest

from oskill.review_double_axis import review_diff
from oskill.rulebooks import (
    RULEBOOK_KEYWORDS,
    get_rulebook,
    list_rulebooks,
    rules_sections,
    select_rulebooks,
    standards_rules,
)


class TestList:
    def test_fourteen_books(self) -> None:
        books = list_rulebooks()
        assert len(books) == 14
        assert "refactoring" in books
        assert "a-philosophy-of-software-design" in books

    def test_keywords_aligned(self) -> None:
        assert set(list_rulebooks()) == set(RULEBOOK_KEYWORDS)


class TestGet:
    def test_full_loaded(self) -> None:
        text = get_rulebook("a-philosophy-of-software-design")
        assert text.startswith("# OBEY")
        assert len(text) > 1000

    def test_unknown_book_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown rulebook"):
            get_rulebook("nope")

    def test_other_tier_not_packaged(self) -> None:
        with pytest.raises(ValueError, match="only tier 'full'"):
            get_rulebook("refactoring", tier="mini")


class TestSections:
    def test_parses_headings(self) -> None:
        sections = rules_sections(get_rulebook("refactoring"))
        assert "preamble" in sections
        assert len(sections) > 3  # 多段

    def test_custom_text(self) -> None:
        text = "# OBEY X\n\npre\n\n## When to use\n\nuse it\n\n## Decision rules\n\n- a\n"
        sections = rules_sections(text)
        assert sections["When to use"] == "use it"
        assert "- a" in sections["Decision rules"]


class TestSelect:
    def test_refactor_task_picks_refactoring(self) -> None:
        books = select_rulebooks("refactor legacy module and add characterization test", top_k=3)
        assert "refactoring" in books
        # legacy 特征测试任务: 遗留代码书应排最前
        assert books[0] == "working-effectively-with-legacy-code"

    def test_data_task_picks_ddia(self) -> None:
        books = select_rulebooks("design a partition scheme for a data stream")
        assert "designing-data-intensive-applications" in books

    def test_top_k_limits(self) -> None:
        books = select_rulebooks("refactor legacy code with reliability fixes", top_k=1)
        assert len(books) == 1


class TestStandards:
    def test_auto_select_and_inject(self) -> None:
        result = standards_rules(task="review refactoring of a legacy module")
        assert result["books"]
        for book in result["books"]:
            assert book in result["sections"]
            assert result["sections"][book]

    def test_explicit_books(self) -> None:
        result = standards_rules(books=["clean-code"])
        assert result["books"] == ["clean-code"]


class TestReviewIntegration:
    def test_review_carries_baseline(self) -> None:
        baseline = standards_rules(books=["a-philosophy-of-software-design"])
        report = review_diff("+print('x')\n", spec="", standards_rules=str(baseline))
        assert report.standards_baseline is not None
        assert "a-philosophy-of-software-design" in report.standards_baseline
