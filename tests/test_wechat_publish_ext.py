"""Tests for wechat_publish 扩展 (upload_image / create_image_post /
账号注册表 / inspect_article)."""

from __future__ import annotations

import json

import pytest

from oskill.wechat_publish import (
    Article,
    WechatAccountRegistry,
    create_image_post,
    inspect_article,
    produce_article,
    upload_image,
)


def test_upload_image_injected_client_ok():
    captured = {}

    def client(**kw):
        captured.update(kw)
        return {"media_id": "m1", "url": "http://img/x.png"}

    result = upload_image("/tmp/a.png", access_token="tok", client=client)
    assert result["ok"] is True
    assert result["media_id"] == "m1"
    assert captured["url"] == "material/add_material"
    assert captured["type"] == "image"


def test_upload_image_error():
    result = upload_image("/tmp/a.png", access_token="tok",
                          client=lambda **kw: {"errcode": 40001, "errmsg": "bad token"})
    assert result["ok"] is False
    assert result["errcode"] == 40001


def test_upload_image_missing_file_default_client():
    result = upload_image("/no/such/file.png", access_token="tok")
    assert result["ok"] is False
    assert "not found" in result["errmsg"]


def test_create_image_post_pure_assembly():
    result = create_image_post(["media://m1", "media://m2"], title="多图",
                               upload=False)
    assert result["ok"] is True
    articles = result["draft"]["articles"]
    assert len(articles) == 2
    assert articles[0]["title"] == "多图"
    assert articles[1]["title"] == "多图 (2)"
    assert all(a["thumb_media_id"] for a in articles)


def test_create_image_post_uploads_then_assembles():
    def client(**kw):
        return {"media_id": "up-" + kw.get("path", "x").split("/")[-1],
                "url": "http://img"}

    result = create_image_post(["/tmp/a.png", "/tmp/b.png"], title="T",
                               access_token="tok", client=client)
    assert result["ok"] is True
    assert result["media_ids"] == ["up-a.png", "up-b.png"]


def test_create_image_post_empty():
    assert create_image_post([], title="T", upload=False)["ok"] is False


def test_account_registry_no_secret(tmp_path):
    registry = WechatAccountRegistry(tmp_path / "accounts.json")
    registry.add_account("主号", app_id="wx123", secret_hint="****abcd", url="https://x")
    registry.add_account("备用", app_id="wx456")
    listed = registry.list_accounts()
    assert len(listed) == 2
    # 不输出 secret 本体 (只有 hint)
    text = json.dumps(listed)
    assert "abcd" not in text.replace("****abcd", "")
    assert registry.get("主号").app_id == "wx123"
    with pytest.raises(KeyError) as exc:
        registry.get("nope")
    assert "available" in str(exc.value)
    reloaded = WechatAccountRegistry(tmp_path / "accounts.json")
    assert reloaded.get("主号").url == "https://x"


def test_account_remove(tmp_path):
    registry = WechatAccountRegistry(tmp_path / "a.json")
    registry.add_account("x", app_id="1")
    assert registry.remove("x") is True
    assert registry.remove("x") is False


def test_inspect_article_full():
    article = produce_article("# 标题\n\n正文带 <img src='http://i'/>",
                              title="T" * 70, summary="S", cover_url="http://c")
    report = inspect_article(article)
    assert report["title_length"] == 70
    assert report["title_ok"] is False            # 超 64 字
    assert report["summary_ok"] is True
    assert report["cover_ok"] is True
    assert report["content_ok"] is True
    assert report["image_count"] == 1
    assert report["readiness"]["ready"] is True


def test_inspect_article_compliance_scan():
    article = produce_article("# 标题\n\n全网最好的服务\n", title="好",
                              summary="", cover_url="")
    report = inspect_article(article)
    assert report["compliance"]["pass"] is False
    assert any(h["keyword"] in ("最", "最好") for h in report["compliance"]["hits"])


def test_inspect_article_no_compliance():
    article = produce_article("正文", title="T")
    report = inspect_article(article, include_compliance=False)
    assert "compliance" not in report
    assert report["readiness"]["blockers"] == ["summary", "cover"]
