"""Tests for wechat_theme (md2wechat themes/layout 3O 内化增强)."""

from __future__ import annotations

import pytest

from oskill.wechat_theme import (
    WechatTheme,
    apply_theme,
    get_theme,
    layout_modules,
    list_themes,
    parse_layout_blocks,
    register_layout_module,
    register_theme,
    render_layout_block,
    render_markdown_with_layout,
)
from oskill.wechat_publish import md_to_wechat_html


def test_builtin_themes_routable():
    names = {t["name"] for t in list_themes()}
    assert "default" in names and "tech" in names
    assert len(names) >= 8


def test_get_theme_unknown_lists_available():
    with pytest.raises(KeyError) as exc:
        get_theme("no-such-theme")
    assert "available" in str(exc.value)
    assert "default" in str(exc.value)


def test_register_theme_override_and_restore():
    register_theme(WechatTheme(name="test-only", description="临时"))
    assert get_theme("test-only").description == "临时"
    register_theme(WechatTheme(name="test-only", description="覆盖"))
    assert get_theme("test-only").description == "覆盖"


def test_apply_theme_injects_inline_styles():
    html = md_to_wechat_html("# 标题\n\n正文段落\n")
    themed = apply_theme(html, "tech")
    assert 'style="font-size:22px' in themed          # h1 主题字号
    assert "#5b21b6" in themed                        # tech 标题色
    assert "line-height:1.8" in themed                # 正文行高


def test_apply_theme_idempotent_and_skips_styled():
    html = md_to_wechat_html("# 标题\n\n> 引用\n")
    once = apply_theme(html, "default")
    twice = apply_theme(once, "news")
    # 已带 style 的标签不再重复注入 (幂等)
    assert once.count("style=") == twice.count("style=")
    # 换主题必须从原始 HTML 重新套 (已注入的不覆盖)
    fresh = apply_theme(html, "news")
    assert "1e3a8a" in fresh


def test_apply_theme_accepts_theme_object():
    html = md_to_wechat_html("# 标题\n\n正文\n")
    themed = apply_theme(html, get_theme("elegant"))
    assert "#8a6d1a" in themed                        # 优雅主题标题色
    assert "text-align:center" in themed             # 居中标题


def test_parse_layout_blocks_basic():
    md = "正文\n\n:::tip\n- title: 小贴士\n这是提示内容\n:::\n\n后文"
    blocks = parse_layout_blocks(md)
    assert len(blocks) == 1
    b = blocks[0]
    assert b.module == "tip"
    assert b.opener == {"title": "小贴士"}
    assert b.body == ["这是提示内容"]


def test_parse_layout_blocks_caption_and_rows():
    md = "::::card[对照表]\nA | B\n1 | 2\n::::"
    blocks = parse_layout_blocks(md)
    assert blocks[0].module == "card"
    assert blocks[0].caption == "对照表"
    assert blocks[0].body == ["A | B", "1 | 2"]


def test_render_unknown_module_lists_available():
    block = parse_layout_blocks(":::no-such-mod\nx\n:::")[0]
    with pytest.raises(KeyError) as exc:
        render_layout_block(block, "default")
    assert "available" in str(exc.value)


def test_render_layout_block_tip():
    block = parse_layout_blocks(":::tip\n这是提示\n:::")[0]
    html = render_layout_block(block, "default")
    assert "这是提示" in html
    assert "border-left:4px" in html


def test_render_markdown_with_layout_end_to_end():
    md = (
        "# 标题\n\n正文\n\n:::tip\n记得按时\n:::\n\n- a\n- b\n"
        ":::hero\n-eyebrow: 深度\n-title: 大标题\n:::\n"
    )
    html, used = render_markdown_with_layout(md, "clean")
    assert used == ["tip", "hero"]
    assert "记得按时" in html
    assert "深度" in html
    assert "<li" in html                    # 普通 md 列表仍在
    assert "#1f6f43" in html                # clean 主题标题色
    assert "<!--LAYOUT" not in html         # 占位符全部替换


def test_render_markdown_with_layout_unknown_module_fails():
    md = ":::bogus\nx\n:::"
    with pytest.raises(KeyError):
        render_markdown_with_layout(md, "default")


def test_register_layout_module_custom():
    def renderer(block, theme):
        return f'<div class="custom">{block.caption}:{";".join(block.body)}</div>'

    register_layout_module("custom-x", renderer)
    assert "custom-x" in layout_modules()
    block = parse_layout_blocks(":::custom-x[标题]\n内容\n:::")[0]
    html = render_layout_block(block, "default")
    assert "标题:内容" in html


def test_layout_modules_lists_builtin():
    mods = layout_modules()
    for expected in ("hero", "card", "tip", "warning", "danger",
                     "quote", "divider", "table", "list", "steps"):
        assert expected in mods
