from oskill._template_scene_compose import template_scene_compose


def test_basic():
    tpl = {"scenes": [{"id": 1, "duration": 2, "text": "Hello {{name}}", "asset_key": "img"}]}
    res = template_scene_compose(template=tpl, assets={"img": "X"}, variables={"name": "Bob"})
    assert res[0]["asset"] == "X"
    assert res[0]["text"] == "Hello Bob"


def test_empty():
    assert template_scene_compose(template={}) == []
