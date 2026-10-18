from oskill._multimodal_index_pipeline import multimodal_index_pipeline


def test_basic():
    items = [{"id": "1", "text": "a"}, {"id": "2", "text": "b"}]
    store = []
    res = multimodal_index_pipeline(items=items, embed_fn=lambda it: [1.0, 2.0], store=store)
    assert len(res) == 2
    assert len(store) == 2
    assert res[0]["vector"] == [1.0, 2.0]


def test_no_embed():
    res = multimodal_index_pipeline(items=[{"id": "1"}])
    assert res[0]["vector"] == []
