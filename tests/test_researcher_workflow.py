"""Tests for oskill.researcher_workflow."""

from unittest.mock import patch

from oskill.researcher_workflow import researcher_workflow

MOCK_SEARCH = {
    "query": "test query",
    "results": [
        {
            "title": "Source 1",
            "url": "https://s1.example.com",
            "content": "Python programming",
            "engine": "bing",
            "score": 0.9,
        },
        {
            "title": "Source 2",
            "url": "https://s2.example.com",
            "content": "Machine learning basics",
            "engine": "ddg",
            "score": 0.8,
        },
    ],
    "total": 2,
    "error": None,
}
MOCK_FETCH = {
    "url": "...",
    "status_code": 200,
    "content_type": "text/html",
    "body_bytes": b"full page",
    "body_text": "Full page content here",
    "error": None,
}
MOCK_CONCEPTS = {
    "concepts": ["Python", "Programming"],
    "count": 2,
    "provider_used": "stub",
    "error": None,
}


def _patch_all(search=None, fetch=None, concepts=None):
    """Helper: return a tuple of patchers for all three oprim calls."""
    return (
        patch("oskill.researcher_workflow.searxng_search", return_value=search or MOCK_SEARCH),
        patch("oskill.researcher_workflow.url_fetch_ssrf_safe", return_value=fetch or MOCK_FETCH),
        patch(
            "oskill.researcher_workflow.concept_extractor", return_value=concepts or MOCK_CONCEPTS
        ),
    )


# --- Test 1: result has required top-level keys ---
def test_returns_required_keys():
    with _patch_all()[0], _patch_all()[1], _patch_all()[2]:
        p_search, p_fetch, p_cx = _patch_all()
        with p_search as ms, p_fetch, p_cx:
            ms.return_value = MOCK_SEARCH
            res = researcher_workflow(query="test query", searxng_url="http://sx")
    assert set(res.keys()) >= {"query", "sources", "all_concepts", "total_sources", "error"}


# --- Test 2: sources list has one entry per search result ---
def test_sources_count_matches_search_results():
    p_search, p_fetch, p_cx = _patch_all()
    with p_search, p_fetch, p_cx:
        res = researcher_workflow(query="q", searxng_url="http://sx")
    assert len(res["sources"]) == 2


# --- Test 3: total_sources matches len(sources) ---
def test_total_sources_matches_len_sources():
    p_search, p_fetch, p_cx = _patch_all()
    with p_search, p_fetch, p_cx:
        res = researcher_workflow(query="q", searxng_url="http://sx")
    assert res["total_sources"] == len(res["sources"])


# --- Test 4: search error propagates to result.error ---
def test_search_error_propagates():
    error_search = {**MOCK_SEARCH, "results": [], "error": "connection refused"}
    p_search, p_fetch, p_cx = _patch_all(search=error_search)
    with p_search, p_fetch, p_cx:
        res = researcher_workflow(query="q", searxng_url="http://sx")
    assert res["error"] is not None
    assert "search failed" in res["error"]
    assert "connection refused" in res["error"]


# --- Test 5: fetch_content=False → url_fetch_ssrf_safe not called ---
def test_fetch_content_false_skips_fetch():
    p_search, p_fetch, p_cx = _patch_all()
    with p_search, p_fetch as mock_fetch, p_cx:
        researcher_workflow(query="q", searxng_url="http://sx", fetch_content=False)
    mock_fetch.assert_not_called()


# --- Test 6: extract_concepts=False → concept_extractor not called ---
def test_extract_concepts_false_skips_extractor():
    p_search, p_fetch, p_cx = _patch_all()
    with p_search, p_fetch, p_cx as mock_cx:
        researcher_workflow(query="q", searxng_url="http://sx", extract_concepts=False)
    mock_cx.assert_not_called()


# --- Test 7: all_concepts is deduplicated union across sources ---
def test_all_concepts_deduplicated():
    concepts_a = {**MOCK_CONCEPTS, "concepts": ["Alpha", "Beta"]}
    concepts_b = {**MOCK_CONCEPTS, "concepts": ["Beta", "Gamma"]}

    call_count = 0

    def cx_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        return concepts_a if call_count == 1 else concepts_b

    p_search, p_fetch, _ = _patch_all()
    with (
        p_search,
        p_fetch,
        patch("oskill.researcher_workflow.concept_extractor", side_effect=cx_side_effect),
    ):
        res = researcher_workflow(query="q", searxng_url="http://sx")

    assert sorted(res["all_concepts"]) == ["Alpha", "Beta", "Gamma"]


# --- Test 8: each source has required keys ---
def test_source_has_required_keys():
    p_search, p_fetch, p_cx = _patch_all()
    with p_search, p_fetch, p_cx:
        res = researcher_workflow(query="q", searxng_url="http://sx")
    for src in res["sources"]:
        assert set(src.keys()) >= {"title", "url", "snippet", "concepts", "fetch_error"}


# --- Test 9: fetch error sets fetch_error in source, workflow continues ---
def test_fetch_error_sets_source_fetch_error_and_continues():
    fetch_err = {**MOCK_FETCH, "body_text": None, "error": "timeout"}
    p_search, p_fetch, p_cx = _patch_all(fetch=fetch_err)
    with p_search, p_fetch, p_cx:
        res = researcher_workflow(query="q", searxng_url="http://sx")
    # All sources processed (no raise)
    assert res["total_sources"] == 2
    # Both sources have fetch_error set
    for src in res["sources"]:
        assert src["fetch_error"] == "timeout"
