"""Tests for agent_discovery / wechat_publish (md2wechat 3O 内化)。"""

from __future__ import annotations

from pathlib import Path

from oskill.agent_discovery import (
    AntiNoiseValidator,
    Resource,
    ResourceCatalog,
)
from oskill.wechat_publish import (
    Article,
    ArticleStore,
    md_to_wechat_html,
    produce_article,
    publish_draft,
)

# ── Discovery-First 资源目录 ─────────────────────────────────────────


def test_catalog_register_and_discover():
    catalog = ResourceCatalog()
    catalog.register(Resource("zhipu", "provider", "GLM 系列"))
    catalog.register(Resource("default", "theme", "默认排版"))
    catalog.register(Resource("wechat-title-expert", "prompt", "标题建议"))

    kinds = catalog.kinds()
    assert kinds == ["prompt", "provider", "theme"]
    providers = catalog.discover("provider")
    assert providers[0].name == "zhipu"
    assert len(catalog.discover()) == 3
    caps = catalog.capabilities()
    assert caps["counts"]["theme"] == 1


def test_catalog_show_and_detail():
    catalog = ResourceCatalog()
    catalog.register(Resource("t", "theme", "x"), detail={"colors": ["#fff"]})
    assert catalog.show("theme", "t").description == "x"
    assert catalog.detail("theme", "t") == {"colors": ["#fff"]}
    import pytest

    with pytest.raises(KeyError, match="unknown resource"):
        catalog.show("theme", "nope")


# ── Anti-Noise 验证器 ────────────────────────────────────────────────


def test_subjective_decision_fails():
    validator = AntiNoiseValidator()
    decision = "建议用更简洁的排版, 更美观"
    assert validator.is_observable(decision) is False
    verdict = validator.validate(decision)
    assert verdict.ok is False
    assert "observable" in verdict.failures


def test_side_effect_decision_fails():
    validator = AntiNoiseValidator()
    decision = "直接把草稿发布到公众号"
    assert validator.no_side_effect(decision) is False
    verdict = validator.validate(decision)
    assert "no_side_effect" in verdict.failures


def test_deterministic_with_evidence():
    validator = AntiNoiseValidator()
    # 证据含可观察信号 (数字/路径/状态)
    verdict = validator.validate(
        "标题超过 64 字符, 建议截断",
        evidence=["title length = 72", "wechat limit 64"],
    )
    assert verdict.checks["deterministic"] is True
    assert verdict.checks["explainable"] is True
    assert verdict.checks["prevents_real_error"] is True
    assert verdict.ok is True


def test_no_evidence_pure_rule_passes():
    validator = AntiNoiseValidator()
    verdict = validator.validate("代码块必须闭合 ```")
    assert verdict.ok is True  # 纯规则决策, 无证据依赖


# ── Markdown → 微信 HTML ─────────────────────────────────────────────


def test_md_html_headings_and_paragraph():
    html_text = md_to_wechat_html("# 标题\n\n正文段落\n")
    assert "<h1>标题</h1>" in html_text
    assert "<p>正文段落</p>" in html_text
    assert html_text.startswith("<section>")


def test_md_html_code_block():
    html_text = md_to_wechat_html("```python\nprint(1 < 2)\n```\n")
    assert "<pre><code>" in html_text
    assert "&lt;" in html_text  # 转义


def test_md_html_lists_and_quote():
    html_text = md_to_wechat_html("- a\n- b\n\n> 引用\n")
    assert "<ul>" in html_text and "<li>a</li>" in html_text
    assert "<blockquote>" in html_text


def test_md_html_image_and_inline():
    html_text = md_to_wechat_html("![图](/img/a.png)\n\n**粗体** `code` [链接](https://x.com)\n")
    assert '<img src="/img/a.png"' in html_text
    assert "<strong>粗体</strong>" in html_text
    assert "<code>code</code>" in html_text
    assert '<a href="https://x.com">链接</a>' in html_text


# ── Article 组装 + Store ─────────────────────────────────────────────


def test_produce_article():
    article = produce_article("# 标题\n正文", title="T", summary="S", cover_url="http://c")
    assert article.content_html.startswith("<section>")
    assert article.title == "T"
    assert article.summary == "S"


def test_article_store_ready_and_persist(tmp_path: Path):
    store = ArticleStore(tmp_path / "drafts.json")
    article = produce_article("# t\nb", title="T", summary="S", cover_url="http://c")
    store.save_article("a1", article)

    readiness = store.readiness("a1")
    assert readiness["ready"] is True
    assert set(readiness["targets"]) == {"title", "content", "summary", "cover"}

    # 持久化 + 重建
    reloaded = ArticleStore(tmp_path / "drafts.json")
    assert reloaded.get_article("a1").title == "T"

    # 缺封面 → blocker
    bare = produce_article("# t\nb", title="T", summary="S")
    store.save_article("a2", bare)
    assert "cover" in store.readiness("a2")["blockers"]


def test_publish_draft_injected_client():
    calls = []

    def fake_client(**kw):
        calls.append(kw)
        return {"media_id": "media-123"}

    result = publish_draft(
        Article("标题", "<p>正文</p>", summary="摘要"),
        access_token="tok-1",
        client=fake_client,
    )
    assert result["ok"] is True
    assert result["media_id"] == "media-123"
    assert calls[0]["payload"]["articles"][0]["title"] == "标题"


def test_publish_draft_error():
    def fake_client(**kw):
        return {"errcode": 40001, "errmsg": "invalid token"}

    result = publish_draft(Article("t", "<p>x</p>"), access_token="bad", client=fake_client)
    assert result["ok"] is False
    assert result["errcode"] == 40001
