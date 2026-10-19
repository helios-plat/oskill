from oskill._highlight_detection_algorithm import highlight_detection_algorithm


def test_empty():
    assert highlight_detection_algorithm(segments=[]) == []


def test_keywords():
    segs = [
        {"start": 0, "end": 5, "text": "hello world"},
        {"start": 5, "end": 10, "text": "amazing breakthrough!"},
    ]
    res = highlight_detection_algorithm(segments=segs, keywords=["breakthrough"], top_k=1)
    assert res[0]["text"] == "amazing breakthrough!"
    assert res[0]["score"] > 0


def test_top_k():
    segs = [{"start": i, "end": i+1, "text": f"t{i}"} for i in range(10)]
    res = highlight_detection_algorithm(segments=segs, top_k=3)
    assert len(res) == 3
