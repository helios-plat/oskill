from oskill._search_synthesize_loop import search_synthesize_loop


def test_no_search_fn():
    res = search_synthesize_loop(query="q", max_iterations=2)
    assert "iterations" in res
    assert len(res["iterations"]) == 1


def test_with_search_and_synthesize():
    res = search_synthesize_loop(
        query="q",
        search_fn=lambda q: ["r1"],
        synthesize_fn=lambda q, r: "synth",
        max_iterations=2,
    )
    assert res["final"] == "synth"
    assert res["iterations"][0]["results"] == ["r1"]
