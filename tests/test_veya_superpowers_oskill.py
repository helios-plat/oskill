"""Tests for oskill.code_review_gate, long_context_compress, vlm_page_nav, proactive_deep_reach."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from oskill._code_review_gate import code_review_gate
from oskill._long_context_compress import long_context_compress
from oskill._proactive_deep_reach import proactive_deep_reach
from oskill._vlm_page_nav import vlm_page_nav

# ============================================================================
# Helpers
# ============================================================================


def _make_llm(return_value: str):
    """Create a mock LLM caller that returns a specific string."""
    mock = MagicMock()
    mock.return_value = return_value
    return mock


# ============================================================================
# code_review_gate
# ============================================================================


class TestCodeReviewGate:
    def test_approved_review(self):
        llm = _make_llm(
            json.dumps(
                {
                    "approved": True,
                    "critical_issues": [],
                    "suggestions": "Looks good.",
                }
            )
        )
        result = code_review_gate("diff --git a/test.py b/test.py", llm_caller=llm)
        assert result["approved"] is True
        assert result["issues"] == []
        assert result["suggestions"] == "Looks good."

    def test_rejected_review(self):
        llm = _make_llm(
            json.dumps(
                {
                    "approved": False,
                    "critical_issues": ["SQL injection risk"],
                    "suggestions": "Use parameterized queries.",
                }
            )
        )
        result = code_review_gate("some diff", llm_caller=llm)
        assert result["approved"] is False
        assert len(result["issues"]) == 1
        assert "SQL injection" in result["issues"][0]

    def test_llm_returns_markdown_wrapped_json(self):
        llm = _make_llm("""
```json
{"approved": true, "critical_issues": [], "suggestions": "ok"}
```
""")
        result = code_review_gate("diff", llm_caller=llm)
        assert result["approved"] is True

    def test_llm_returns_invalid_json(self):
        llm = _make_llm("not valid json at all")
        result = code_review_gate("diff", llm_caller=llm)
        assert result["approved"] is False
        assert "parse" in result["issues"][0].lower()

    def test_empty_diff(self):
        llm = _make_llm(
            json.dumps(
                {
                    "approved": True,
                    "critical_issues": [],
                    "suggestions": "Empty diff.",
                }
            )
        )
        result = code_review_gate("", llm_caller=llm)
        assert result["approved"] is True

    def test_llm_called_with_diff_content(self):
        llm = _make_llm(
            json.dumps(
                {
                    "approved": True,
                    "critical_issues": [],
                    "suggestions": "",
                }
            )
        )
        code_review_gate("+bad_function()", llm_caller=llm)
        call_arg = llm.call_args[0][0] if llm.call_args[0] else ""
        assert "+bad_function()" in call_arg


# ============================================================================
# long_context_compress
# ============================================================================


class TestLongContextCompress:
    def test_short_history_no_compression(self):
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        llm = _make_llm("summary")
        result = long_context_compress(history, llm_caller=llm, max_keep_recent=5)
        assert result["compressed"] is False
        assert result["compacted_history"] == history
        assert result["saved_tokens_est"] == 0

    def test_long_history_compressed(self):
        history = []
        for i in range(10):
            history.append({"role": "user", "content": f"msg {i}"})
            history.append({"role": "assistant", "content": f"reply {i}"})

        llm = _make_llm("Compressed summary of the conversation.")
        result = long_context_compress(history, llm_caller=llm, max_keep_recent=3)
        assert result["compressed"] is True
        assert len(result["compacted_history"]) < len(history)
        assert result["saved_tokens_est"] > 0

    def test_summary_message_present(self):
        history = []
        for i in range(10):
            history.append({"role": "user", "content": f"msg {i}"})
            history.append({"role": "assistant", "content": f"reply {i}"})

        llm = _make_llm("Compressed: user asked about AI, assistant explained.")
        result = long_context_compress(history, llm_caller=llm, max_keep_recent=2)
        assert result["compressed"] is True
        # First message should be the summary
        first_role = result["compacted_history"][0]["role"]
        assert first_role == "system"
        assert "LONG_HORIZON_SUMMARY" in result["compacted_history"][0]["content"]

    def test_llm_failure_still_compresses(self):
        history = []
        for i in range(10):
            history.append({"role": "user", "content": f"msg {i}"})
            history.append({"role": "assistant", "content": f"reply {i}"})

        def raise_llm(prompt, **kwargs):
            raise RuntimeError("LLM down")

        result = long_context_compress(history, llm_caller=raise_llm, max_keep_recent=2)
        assert result["compressed"] is True
        assert "LLM unavailable" in result["compacted_history"][0]["content"]

    def test_empty_history(self):
        result = long_context_compress([], llm_caller=_make_llm("x"))
        assert result["compressed"] is False
        assert result["compacted_history"] == []


# ============================================================================
# vlm_page_nav
# ============================================================================


class TestVlmPageNav:
    def test_navigates_to_element(self):
        page_state = {
            "url": "https://example.com",
            "elements": [
                {"id": "search-input", "type": "input", "box": [100, 50, 400, 40], "text": ""},
                {"id": "submit-btn", "type": "button", "box": [510, 50, 80, 40], "text": "Go"},
            ],
        }
        llm = _make_llm(
            json.dumps(
                {
                    "action": "click",
                    "target_id": "submit-btn",
                    "value": "",
                }
            )
        )
        result = vlm_page_nav(page_state, "Search for cats", llm_caller=llm)
        assert result["status"] == "success"
        assert result["action_spec"]["action"] == "click"
        assert result["action_spec"]["target_id"] == "submit-btn"

    def test_type_action(self):
        page_state = {
            "url": "https://example.com",
            "elements": [
                {"id": "search-input", "type": "input", "box": [100, 50, 400, 40], "text": ""},
            ],
        }
        llm = _make_llm(
            json.dumps(
                {
                    "action": "type",
                    "target_id": "search-input",
                    "value": "cats",
                }
            )
        )
        result = vlm_page_nav(page_state, "Search for cats", llm_caller=llm)
        assert result["action_spec"]["action"] == "type"
        assert result["action_spec"]["value"] == "cats"

    def test_invalid_llm_response(self):
        page_state = {
            "url": "https://example.com",
            "elements": [{"id": "btn", "type": "button", "box": [0, 0, 10, 10], "text": "X"}],
        }
        llm = _make_llm("just some text")
        result = vlm_page_nav(page_state, "click the button", llm_caller=llm)
        assert result["status"] == "failed"
        assert result["action_spec"]["action"] == "wait"

    def test_empty_elements(self):
        page_state = {"url": "https://empty.com", "elements": []}
        llm = _make_llm(json.dumps({"action": "navigate", "target_id": "", "value": ""}))
        result = vlm_page_nav(page_state, "go somewhere", llm_caller=llm)
        assert result["status"] == "success"

    def test_markdown_wrapped_json(self):
        page_state = {
            "url": "https://test.com",
            "elements": [{"id": "btn", "type": "button", "box": [0, 0, 10, 10], "text": "OK"}],
        }
        llm = _make_llm('```json\n{"action": "click", "target_id": "btn", "value": ""}\n```')
        result = vlm_page_nav(page_state, "click ok", llm_caller=llm)
        assert result["status"] == "success"
        assert result["action_spec"]["target_id"] == "btn"


# ============================================================================
# proactive_deep_reach
# ============================================================================


class TestProactiveDeepReach:
    def test_single_depth_search(self):
        def fetch_op(query):
            return {"content_markdown": f"Results for: {query}"}

        llm = _make_llm("DONE")
        result = proactive_deep_reach(
            "AI Safety",
            fetch_op=fetch_op,
            llm_caller=llm,
            max_depth=1,
        )
        assert result["status"] == "completed"
        assert result["depth_reached"] == 1
        assert len(result["collected_info"]) == 1

    def test_multi_depth_search(self):
        call_count = [0]
        responses = ["https://example.com/ai-safety-2", "Sub-topic: alignment", "DONE"]

        def fetch_op(query):
            return {"content_markdown": f"Content about: {query}"}

        def llm_fn(prompt, **kwargs):
            idx = min(call_count[0], len(responses) - 1)
            resp = responses[idx]
            call_count[0] += 1
            return resp

        result = proactive_deep_reach(
            "AI Safety",
            fetch_op=fetch_op,
            llm_caller=llm_fn,
            max_depth=3,
        )
        assert result["status"] == "completed"
        assert result["depth_reached"] >= 1

    def test_fetch_op_failure_does_not_crash(self):
        def fetch_op(query):
            raise RuntimeError("network error")

        llm = _make_llm("DONE")
        result = proactive_deep_reach(
            "test",
            fetch_op=fetch_op,
            llm_caller=llm,
            max_depth=3,
        )
        assert result["status"] == "completed"
        # First fetch fails, loop breaks
        assert result["depth_reached"] >= 1

    def test_done_breaks_loop(self):
        def fetch_op(query):
            return {"content_markdown": "data"}

        llm = _make_llm("DONE")
        result = proactive_deep_reach(
            "test",
            fetch_op=fetch_op,
            llm_caller=llm,
            max_depth=5,
        )
        # Should stop at depth 1 because LLM says DONE
        assert result["depth_reached"] == 1

    def test_llm_error_breaks_loop(self):
        def fetch_op(query):
            return {"content_markdown": "data"}

        def bad_llm(prompt, **kwargs):
            raise RuntimeError("LLM error")

        result = proactive_deep_reach(
            "test",
            fetch_op=fetch_op,
            llm_caller=bad_llm,
            max_depth=5,
        )
        # Should stop at depth 1 regardless
        assert result["depth_reached"] == 1

    def test_max_depth_respected(self):
        def fetch_op(query):
            return {"content_markdown": f"data for {query}"}

        llm = _make_llm("https://next-topic.com")
        result = proactive_deep_reach(
            "start",
            fetch_op=fetch_op,
            llm_caller=llm,
            max_depth=3,
        )
        assert result["depth_reached"] <= 3

    def test_collected_info_has_required_fields(self):
        def fetch_op(query):
            return {"content_markdown": "test data"}

        llm = _make_llm("DONE")
        result = proactive_deep_reach("topic", fetch_op=fetch_op, llm_caller=llm, max_depth=1)
        for item in result["collected_info"]:
            assert "depth" in item
            assert "target" in item
            assert "content" in item
