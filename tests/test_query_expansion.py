from oskill._query_expansion import query_expansion


def test_empty():
    assert query_expansion(query="") == []


def test_basic():
    res = query_expansion(query="machine learning", max_subqueries=3)
    assert isinstance(res, list)
    assert len(res) <= 3
    assert "machine learning" in res


def test_llm_caller():
    def caller(**kw):
        return {"content": "sub1\nsub2\n"}
    res = query_expansion(query="q", llm_caller=caller, max_subqueries=3)
    assert "sub1" in res
