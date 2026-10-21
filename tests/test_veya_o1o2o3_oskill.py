"""O1/O2/O3 oskill 层测试: _mus_shrink_algorithm, _backtranslate_diff, _puct_tree_search."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestMusShrinkAlgorithm:
    def test_shrinks_to_mus(self):
        from oskill._mus_shrink_algorithm import _mus_shrink_algorithm

        def oracle(subset):
            if "c3" not in subset:
                return "sat"
            return "unsat"

        constraints = ["c1", "c2", "c3"]
        result = _mus_shrink_algorithm(constraints, oracle_checker=oracle, max_checks=100)
        assert result["verified"] is True
        assert "c3" in result["mus"]

    def test_protected_constraints(self):
        from oskill._mus_shrink_algorithm import _mus_shrink_algorithm

        def oracle(subset):
            if "critical" not in subset:
                return "sat"
            return "unsat"

        result = _mus_shrink_algorithm(
            ["a", "critical", "b"],
            oracle_checker=oracle,
            protected_ids=frozenset(["critical"]),
        )
        assert "critical" in result["mus"]

    def test_max_checks_limit(self):
        from oskill._mus_shrink_algorithm import _mus_shrink_algorithm

        def oracle(subset):
            return "unsat"

        result = _mus_shrink_algorithm(
            ["c1", "c2", "c3", "c4", "c5"],
            oracle_checker=oracle,
            max_checks=2,
        )
        assert result["verified"] is False


class TestBacktranslateDiff:
    def test_no_diff(self):
        from oskill._backtranslate_diff import _backtranslate_diff

        mock_store = MagicMock()
        mock_store.diff.return_value = {"added": {}, "removed": {}, "changed": {}}
        llm = MagicMock(return_value="No action needed.")
        result = _backtranslate_diff("entity-1", 1, 2, snapshot_store=mock_store, llm_caller=llm)
        assert result["rollback_possible"] is True

    def test_with_changes(self):
        from oskill._backtranslate_diff import _backtranslate_diff

        mock_store = MagicMock()
        mock_store.diff.return_value = {
            "added": {"new_field": "val"},
            "removed": {},
            "changed": {"status": {"from": "A", "to": "B"}},
        }
        llm = MagicMock(return_value="1. Review status change.")
        result = _backtranslate_diff("e1", 1, 2, snapshot_store=mock_store, llm_caller=llm)
        assert result["rollback_possible"] is True

    def test_removed_not_rollbackable(self):
        from oskill._backtranslate_diff import _backtranslate_diff

        mock_store = MagicMock()
        mock_store.diff.return_value = {"added": {}, "removed": {"deleted": "gone"}, "changed": {}}
        llm = MagicMock(return_value="Cannot rollback.")
        result = _backtranslate_diff("e1", 1, 2, snapshot_store=mock_store, llm_caller=llm)
        assert result["rollback_possible"] is False


class TestPuctTreeSearch:
    def test_basic_search(self):
        from oskill._puct_tree_search import _puct_tree_search

        def oracle(sid):
            return {"reward": 0.7, "terminal": False}

        llm = MagicMock(return_value='["action_left", "action_right"]')
        result = _puct_tree_search(
            "root", oracle_evaluator=oracle, llm_caller=llm, max_simulations=20
        )
        assert "best_path" in result
        assert result["simulations"] > 0

    def test_llm_fallback(self):
        from oskill._puct_tree_search import _puct_tree_search

        def oracle(sid):
            return {"reward": 0.5, "terminal": False}

        def broken_llm(prompt, **kwargs):
            raise RuntimeError("LLM down")

        result = _puct_tree_search(
            "root", oracle_evaluator=oracle, llm_caller=broken_llm, max_simulations=10
        )
        assert "best_path" in result

    def test_tree_size_grows(self):
        from oskill._puct_tree_search import _puct_tree_search

        def oracle(sid):
            return {"reward": 0.3, "terminal": False}

        llm = MagicMock(return_value='["go_left", "go_right"]')
        result = _puct_tree_search(
            "start", oracle_evaluator=oracle, llm_caller=llm, max_simulations=30
        )
        assert result["tree_size"] >= 1
