"""Tests for wechat_resources (公众号资源目录装配) + reviewer/reviser prompt."""

from __future__ import annotations

import pytest

from oskill.agent_discovery import ResourceCatalog
from oskill.wechat_resources import (
    catalog_summary,
    register_wechat_resources,
    wechat_catalog,
)
from oskill.wechat_writing import reviewer_prompt, reviser_prompt


def test_catalog_has_all_kinds():
    catalog = wechat_catalog()
    kinds = catalog.kinds()
    for expected in ("theme", "layout", "prompt", "wechat-flow"):
        assert expected in kinds


def test_catalog_theme_details_loadable():
    catalog = wechat_catalog()
    theme = catalog.show("theme", "tech")
    assert "科技" in theme.description
    detail = catalog.detail("theme", "tech")
    assert detail.name == "tech"
    assert detail.title_color == "#5b21b6"          # 详情可加载为 WechatTheme


def test_catalog_layout_and_prompt():
    catalog = wechat_catalog()
    assert catalog.show("layout", "tip").description
    assert catalog.show("prompt", "write").description
    factory = catalog.detail("prompt", "write")
    assert callable(factory)
    p = factory("主题", requirements="800字")
    assert "主题" in p["user"] and p["system"]


def test_catalog_idempotent():
    catalog = wechat_catalog()
    before = len(catalog.discover())
    register_wechat_resources(catalog)              # 重复注册不膨胀
    register_wechat_resources(catalog)
    assert len(catalog.discover()) == before


def test_catalog_reuses_existing_catalog():
    shared = ResourceCatalog()
    shared.register_wechat = None
    register_wechat_resources(shared)
    assert shared.kinds()                            # 注入既有目录


def test_catalog_summary_shape():
    summary = catalog_summary()
    assert summary["counts"]["theme"] >= 8
    assert summary["counts"]["prompt"] == 8
    assert "wechat-flow" in summary["kinds"]


def test_reviewer_prompt_contract():
    p = reviewer_prompt()
    assert "审核官" in p["system"]                    # 主链路测试依赖该关键词
    assert "topic_match" in p["system"]
    assert "image_miss_streak" in p["user_extra"]    # 槽位模板
    assert "{sections}" in p["user_extra"]


def test_reviser_prompt_contract():
    p = reviser_prompt()
    assert "只改写" in p["system"]                    # 主链路测试依赖该关键词
    assert "{draft_json}" in p["user_extra"]
    assert "{issues}" in p["user_extra"]
