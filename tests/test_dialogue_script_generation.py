from oskill._dialogue_script_generation import dialogue_script_generation


def test_empty():
    assert dialogue_script_generation(content="") == []


def test_heuristic():
    res = dialogue_script_generation(content="one two three four five six", max_turns=2)
    assert len(res) == 2
    assert all("speaker" in r and "text" in r for r in res)


def test_llm_caller():
    def caller(**kw):
        return {"content": "Host: hi\nGuest: hello\n"}
    res = dialogue_script_generation(content="x", llm_caller=caller, max_turns=5)
    assert any(r["speaker"] == "Host" for r in res)
