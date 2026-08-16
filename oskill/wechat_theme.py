"""oskill.wechat_theme — 公众号主题 + 布局模块系统 (md2wechat themes/layout 3O 内化增强)。

对标 md2wechat:
  * themes/ — 一组可切换的公众号排版主题 (default/spring-fresh/sports/...);
  * layout — 53 个 `:::` 布局模块语法 (hero/card/tip/...), opener 字段 +
    方括号 caption + 正文 (rows/json/plain)。
更强:
  * 主题是纯数据 (WechatTheme dataclass), 非远端 API; 内置 8 个 + 运行时
    register_theme 扩展;
  * apply_theme 把主题注入为**内联样式** HTML (公众号编辑器过滤 <style>,
    必须内联, 与 wechat_publish.md_to_wechat_html 的输出兼容), 幂等可反复套;
  * 布局模块解析器 + 注册表: 未知模块/未知主题报错时给出可用列表
    (md2wechat "do not guess" 原则), 不再用正则蒙混。

零 veya 反向依赖: 纯标准库, 所有渲染为确定性纯函数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 主题 ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WechatTheme:
    """一个公众号排版主题 (数据驱动, 全部映射为内联样式)。

    Attributes:
        name: 主题名 (get_theme 路由键)。
        description: 一句话说明。
        title_color / title_size / title_align / title_border: 大标题
            (h1) 样式; title_align=center 居中, title_border=True 左侧竖线。
        heading_color / heading_size: 小节标题 (h2-h6)。
        body_color / body_size / line_height: 正文。
        accent_color: 链接/加粗强调色。
        quote_color / quote_bg / quote_border: 引用块。
        code_bg / code_color: 代码块。
        divider_color: 分隔线。
        card_bg / card_border: 卡片/提示块。
        cover_palette: 封面图 prompt 风格提示 (供 wechat_writing.cover_prompt 用)。
    """

    name: str
    description: str = ""
    title_color: str = "#1a1a1a"
    title_size: int = 22
    title_align: str = "left"
    title_border: bool = False
    heading_color: str = "#1a1a1a"
    heading_size: int = 18
    body_color: str = "#333333"
    body_size: int = 16
    line_height: float = 1.8
    accent_color: str = "#2e6be6"
    quote_color: str = "#666666"
    quote_bg: str = "#f7f7f7"
    quote_border: str = "#cccccc"
    code_bg: str = "#f6f8fa"
    code_color: str = "#24292e"
    divider_color: str = "#e5e5e5"
    card_bg: str = "#f7f7f7"
    card_border: str = "#e0e0e0"
    cover_palette: str = ""

    def to_dict(self) -> dict[str, Any]:
        """路由元数据 (Discovery-First 只暴露路由字段)。"""
        return {"name": self.name, "description": self.description}


# 内置主题表 (对标 md2wechat themes/*.yaml 的常用风格)
_BUILTIN_THEMES: list[WechatTheme] = [
    WechatTheme(
        name="default",
        description="微信默认极简风: 黑字白底, 无装饰",
        cover_palette="clean white background, black bold text, minimal editorial",
    ),
    WechatTheme(
        name="clean",
        description="清新绿: 标题墨绿, 强调草绿, 适合生活方式/健康类",
        title_color="#1f6f43",
        heading_color="#1f6f43",
        accent_color="#2e9e5b",
        quote_bg="#f0faf4",
        quote_border="#2e9e5b",
        card_bg="#f4fbf6",
        card_border="#bfe6cd",
        cover_palette="fresh green palette, soft natural light, modern minimal",
    ),
    WechatTheme(
        name="news",
        description="新闻蓝: 标题深蓝加左侧竖线, 适合资讯/观点类",
        title_color="#1e3a8a",
        title_border=True,
        heading_color="#1e3a8a",
        accent_color="#2563eb",
        quote_bg="#f0f4ff",
        quote_border="#2563eb",
        cover_palette="deep blue editorial, bold headline, clean press layout",
    ),
    WechatTheme(
        name="tech",
        description="科技紫: 深紫标题, 深底代码块, 适合技术/数码类",
        title_color="#5b21b6",
        heading_color="#5b21b6",
        accent_color="#7c3aed",
        code_bg="#1e1e2e",
        code_color="#e4e4e7",
        quote_bg="#f5f3ff",
        quote_border="#7c3aed",
        card_bg="#f5f3ff",
        card_border="#ddd6fe",
        cover_palette="dark violet gradient, futuristic tech aesthetic, neon accent",
    ),
    WechatTheme(
        name="elegant",
        description="金典: 标题金色居中, 适合品牌/文化/深度内容",
        title_color="#8a6d1a",
        title_align="center",
        heading_color="#8a6d1a",
        accent_color="#b8860b",
        quote_bg="#fdf9ec",
        quote_border="#d4af37",
        card_bg="#fdf9ec",
        card_border="#e8d9a8",
        cover_palette="gold on dark navy, luxury serif, refined classic",
    ),
    WechatTheme(
        name="spring",
        description="春色: 粉绿渐变感, 适合情感/亲子/生活类",
        title_color="#c2410c",
        heading_color="#0f766e",
        accent_color="#0d9488",
        quote_bg="#fdf6f0",
        quote_border="#fb923c",
        card_bg="#f0fdfa",
        card_border="#99f6e4",
        cover_palette="soft spring pastel, warm light, gentle gradients",
    ),
    WechatTheme(
        name="ocean",
        description="海洋: 青色系, 适合旅行/科普类",
        title_color="#0e7490",
        heading_color="#0e7490",
        accent_color="#0891b2",
        quote_bg="#ecfeff",
        quote_border="#22d3ee",
        card_bg="#ecfeff",
        card_border="#a5f3fc",
        cover_palette="ocean blue gradient, deep sea tones, fresh airy",
    ),
    WechatTheme(
        name="bold-red",
        description="字节红: 高对比红, 适合活动/电商/强号召",
        title_color="#dc2626",
        heading_color="#dc2626",
        accent_color="#e63b2e",
        quote_bg="#fef2f2",
        quote_border="#f87171",
        card_bg="#fef2f2",
        card_border="#fecaca",
        cover_palette="vivid red, high contrast, bold promotion energy",
    ),
]

_THEMES: dict[str, WechatTheme] = {t.name: t for t in _BUILTIN_THEMES}


def get_theme(name: str) -> WechatTheme:
    """取主题; 不存在抛 KeyError 并附可用列表 (do not guess)。"""
    theme = _THEMES.get(name)
    if theme is None:
        raise KeyError(
            f"unknown theme {name!r}; available: {sorted(_THEMES)}"
        )
    return theme


def list_themes() -> list[dict[str, str]]:
    """全部主题的路由元数据 (Discovery-First: themes list)。"""
    return [t.to_dict() for t in _BUILTIN_THEMES]


def register_theme(theme: WechatTheme) -> None:
    """注册/覆盖一个主题 (幂等)。"""
    _THEMES[theme.name] = theme
    for i, t in enumerate(_BUILTIN_THEMES):
        if t.name == theme.name:
            _BUILTIN_THEMES[i] = theme
            return
    _BUILTIN_THEMES.append(theme)


# ── 主题 → 内联样式注入 ─────────────────────────────────────────────

_TAG_STYLE = re.compile(r"<(?P<tag>h[1-6]|p|li|blockquote|pre|code|a|hr|table|td|th|img|ul|ol)"
                        r"(?P<attrs>[^>]*)>")


def _style_of(match: re.Match, theme: WechatTheme) -> str:
    """为一个标签生成注入后的完整标签串 (已有 style= 的标签跳过, 幂等)。"""
    tag, attrs = match.group("tag"), match.group("attrs")
    if re.search(r"\bstyle=", attrs):
        return match.group(0)
    if tag == "h1":
        align = "text-align:center;" if theme.title_align == "center" else ""
        border = (
            f"border-left:4px solid {theme.accent_color};padding-left:12px;"
            if theme.title_border
            else ""
        )
        style = (f"font-size:{theme.title_size}px;font-weight:700;line-height:1.4;"
                 f"margin:0 0 16px;color:{theme.title_color};{align}{border}")
    elif tag in ("h2", "h3", "h4", "h5", "h6"):
        style = (f"font-size:{max(theme.heading_size - (int(tag[1]) - 2) * 2, 14)}px;"
                 f"font-weight:700;margin:24px 0 12px;color:{theme.heading_color};")
    elif tag == "blockquote":
        style = (f"margin:16px 0;padding:12px 16px;color:{theme.quote_color};"
                 f"background:{theme.quote_bg};border-left:4px solid {theme.quote_border};"
                 f"border-radius:4px;font-size:{theme.body_size}px;")
    elif tag == "pre":
        style = (f"background:{theme.code_bg};color:{theme.code_color};padding:14px 16px;"
                 f"border-radius:8px;overflow-x:auto;margin:16px 0;font-size:14px;")
    elif tag == "code":
        style = f"background:{theme.code_bg};color:{theme.code_color};font-size:14px;"
    elif tag == "a":
        style = f"color:{theme.accent_color};text-decoration:underline;"
    elif tag == "strong":
        style = f"color:{theme.accent_color};font-weight:700;"
    elif tag == "li":
        style = f"font-size:{theme.body_size}px;line-height:{theme.line_height};color:{theme.body_color};"
    elif tag == "hr":
        style = f"border:none;border-top:1px solid {theme.divider_color};margin:24px 0;"
    elif tag == "table":
        style = ("width:100%;border-collapse:collapse;margin:16px 0;"
                 f"font-size:{max(theme.body_size - 1, 13)}px;color:{theme.body_color};")
    elif tag in ("td", "th"):
        style = (f"border:1px solid {theme.divider_color};padding:8px 10px;"
                 f"text-align:left;line-height:1.6;")
    elif tag == "img":
        style = "max-width:100%;border-radius:8px;"
    elif tag == "ul":
        style = f"font-size:{theme.body_size}px;line-height:{theme.line_height};color:{theme.body_color};margin:0 0 16px;padding-left:24px;"
    else:  # ol
        style = f"font-size:{theme.body_size}px;line-height:{theme.line_height};color:{theme.body_color};margin:0 0 16px;padding-left:24px;"
    return f"<{tag}{attrs} style=\"{style}\">"


def apply_theme(html: str, theme: WechatTheme | str) -> str:
    """把主题注入为内联样式 (微信要求内联, <style> 会被编辑器过滤)。

    纯函数 + 幂等: 已带 style= 的标签跳过; 可对同一 HTML 反复套主题。

    Args:
        html: wechat_publish.md_to_wechat_html 输出或任意微信 HTML。
        theme: WechatTheme 或主题名。

    Returns:
        注入内联样式后的 HTML。
    """
    if isinstance(theme, str):
        theme = get_theme(theme)
    return _TAG_STYLE.sub(lambda m: _style_of(m, theme), html)


# ── 布局模块 (::: 语法) ─────────────────────────────────────────────


@dataclass(frozen=True)
class LayoutBlock:
    """一个解析出的 ::: 布局块。

    Attributes:
        module: 模块名 (card/tip/hero/...)。
        caption: 方括号标题, 如 :::card[卡片标题]。
        opener: 字段行键值 (如 eyebrow/title/subtitle)。
        body: 正文行 (rows 用 " | " 分隔, plain 为原文)。
        raw: 原始块文本 (含围栏)。
    """

    module: str
    opener: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    caption: str = ""
    raw: str = ""


_LAYOUT_FENCE_OPEN = re.compile(r"^:{3,4}\s*([\w-]+)(?:\[([^\]]*)\])?\s*$")
_LAYOUT_FENCE_CLOSE = re.compile(r"^:{3,4}\s*$")
_OPENER_LINE = re.compile(r"^-\s*([\w-]+)\s*:\s*(.+)$")


def parse_layout_blocks(markdown: str) -> list[LayoutBlock]:
    """解析 Markdown 中的 ::: 布局块 (3 或 4 冒号围栏)。

    Args:
        markdown: 原始 Markdown。

    Returns:
        布局块列表 (文档顺序)。未闭合围栏按块收尾处理, 不抛错。
    """
    blocks: list[LayoutBlock] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        m = _LAYOUT_FENCE_OPEN.match(lines[i].strip())
        if not m:
            i += 1
            continue
        module, caption = m.group(1), m.group(2) or ""
        opener: dict[str, str] = {}
        body: list[str] = []
        j = i + 1
        while j < len(lines) and not _LAYOUT_FENCE_CLOSE.match(lines[j].strip()):
            om = _OPENER_LINE.match(lines[j].strip())
            if om and not body:
                opener[om.group(1)] = om.group(2).strip()
            else:
                body.append(lines[j].rstrip())
            j += 1
        blocks.append(
            LayoutBlock(
                module=module,
                opener=opener,
                body=[b for b in body if b.strip()],
                caption=caption,
                raw="\n".join(lines[i:j + 1]),
            )
        )
        i = j + 1
    return blocks


def _esc(text: Any) -> str:
    import html as _html

    return _html.escape(str(text or ""), quote=False)


def _rows_of(block: LayoutBlock) -> list[list[str]]:
    return [[c.strip() for c in line.split("|")] for line in block.body]


def _render_rows(rows: list[list[str]], theme: WechatTheme) -> str:
    cells = "".join(f"<td>{_esc(c)}</td>" for c in rows[0])
    html = [f"<table><tbody><tr>{cells}</tr>"]
    for row in rows[1:]:
        html.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)


def _module_renderers() -> dict[str, Callable[[LayoutBlock, WechatTheme], str]]:
    """内置布局模块渲染器 (注册表可扩展)。"""

    def hero(block: LayoutBlock, theme: WechatTheme) -> str:
        title = block.opener.get("title") or block.caption or ""
        subtitle = block.opener.get("subtitle", "")
        eyebrow = block.opener.get("eyebrow", "")
        body = "\n".join(block.body)
        parts = [
            f'<div style="background:{theme.card_bg};border:1px solid {theme.card_border};'
            f'border-radius:12px;padding:24px 20px;margin:16px 0;">'
        ]
        if eyebrow:
            parts.append(
                f'<p style="font-size:13px;color:{theme.accent_color};margin:0 0 8px;'
                f'font-weight:700;">{_esc(eyebrow)}</p>'
            )
        if title:
            parts.append(
                f'<p style="font-size:20px;font-weight:700;color:{theme.heading_color};'
                f'margin:0 0 8px;line-height:1.4;">{_esc(title)}</p>'
            )
        if subtitle:
            parts.append(
                f'<p style="font-size:16px;color:{theme.body_color};margin:0 0 8px;'
                f'line-height:1.7;">{_esc(subtitle)}</p>'
            )
        if body:
            parts.append(
                f'<p style="font-size:15px;color:{theme.quote_color};margin:0;'
                f'line-height:1.7;">{_esc(body)}</p>'
            )
        parts.append("</div>")
        return "\n".join(parts)

    def card(block: LayoutBlock, theme: WechatTheme) -> str:
        caption = block.caption
        body = "<br/>".join(_esc(b) for b in block.body)
        parts = [
            f'<div style="background:{theme.card_bg};border:1px solid {theme.card_border};'
            f'border-radius:10px;padding:16px 18px;margin:16px 0;">'
        ]
        if caption:
            parts.append(
                f'<p style="font-size:16px;font-weight:700;color:{theme.heading_color};'
                f'margin:0 0 8px;">{_esc(caption)}</p>'
            )
        parts.append(
            f'<p style="font-size:15px;color:{theme.body_color};margin:0;'
            f'line-height:1.7;">{body}</p>'
        )
        parts.append("</div>")
        return "\n".join(parts)

    def callout(block: LayoutBlock, theme: WechatTheme, kind: str, color: str) -> str:
        bg = {"tip": "#f0fdf4", "warning": "#fffbeb", "danger": "#fef2f2"}.get(
            kind, theme.card_bg
        )
        border = {"tip": "#86efac", "warning": "#fcd34d", "danger": "#fca5a5"}.get(
            kind, theme.card_border
        )
        label = {"tip": "提示", "warning": "注意", "danger": "警告"}.get(kind, "")
        caption = block.caption or label
        body = "<br/>".join(_esc(b) for b in block.body)
        return (
            f'<div style="background:{bg};border-left:4px solid {border};'
            f'border-radius:6px;padding:12px 16px;margin:16px 0;">'
            f'<p style="font-size:15px;font-weight:700;color:{color};margin:0 0 4px;">'
            f'{_esc(caption)}</p>'
            f'<p style="font-size:15px;color:{theme.body_color};margin:0;'
            f'line-height:1.7;">{body}</p></div>'
        )

    def tip(block: LayoutBlock, theme: WechatTheme) -> str:
        return callout(block, theme, "tip", "#15803d")

    def warning(block: LayoutBlock, theme: WechatTheme) -> str:
        return callout(block, theme, "warning", "#b45309")

    def danger(block: LayoutBlock, theme: WechatTheme) -> str:
        return callout(block, theme, "danger", "#b91c1c")

    def quote(block: LayoutBlock, theme: WechatTheme) -> str:
        body = "<br/>".join(_esc(b) for b in block.body)
        return (
            f'<blockquote style="margin:16px 0;padding:12px 16px;color:{theme.quote_color};'
            f'background:{theme.quote_bg};border-left:4px solid {theme.quote_border};'
            f'border-radius:4px;font-size:16px;">{body}</blockquote>'
        )

    def divider(block: LayoutBlock, theme: WechatTheme) -> str:
        text = _esc(block.caption or block.opener.get("text", ""))
        if text:
            return (
                f'<p style="text-align:center;color:{theme.quote_color};margin:24px 0;'
                f'font-size:14px;">— {text} —</p>'
            )
        return (
            f'<hr style="border:none;border-top:1px solid {theme.divider_color};'
            f'margin:24px 0;"/>'
        )

    def table(block: LayoutBlock, theme: WechatTheme) -> str:
        rows = _rows_of(block)
        if not rows:
            return ""
        return _render_rows(rows, theme)

    def list_(block: LayoutBlock, theme: WechatTheme) -> str:
        items = "".join(
            f'<li style="font-size:15px;line-height:1.8;color:{theme.body_color};'
            f'margin:4px 0;">{_esc(b)}</li>'
            for b in block.body
        )
        caption = (
            f'<p style="font-size:16px;font-weight:700;color:{theme.heading_color};'
            f'margin:0 0 8px;">{_esc(block.caption)}</p>'
            if block.caption
            else ""
        )
        return (
            f'<div style="margin:16px 0;">{caption}'
            f'<ul style="margin:0;padding-left:22px;">{items}</ul></div>'
        )

    def steps(block: LayoutBlock, theme: WechatTheme) -> str:
        items = "".join(
            f'<li style="font-size:15px;line-height:1.8;color:{theme.body_color};'
            f'margin:6px 0;padding-left:4px;">{i}. {_esc(b)}</li>'
            for i, b in enumerate(block.body, 1)
        )
        return (
            f'<div style="margin:16px 0;background:{theme.card_bg};'
            f'border-radius:10px;padding:14px 18px;">'
            f'<ul style="margin:0;padding-left:8px;list-style:none;">{items}</ul></div>'
        )

    return {
        "hero": hero,
        "card": card,
        "tip": tip,
        "warning": warning,
        "danger": danger,
        "quote": quote,
        "divider": divider,
        "table": table,
        "list": list_,
        "steps": steps,
    }


_LAYOUT_RENDERERS = _module_renderers()


def register_layout_module(
    name: str, renderer: Callable[[LayoutBlock, WechatTheme], str]
) -> None:
    """注册/覆盖一个布局模块渲染器 (幂等)。"""
    _LAYOUT_RENDERERS[name] = renderer


def layout_modules() -> list[str]:
    """已注册布局模块名 (Discovery-First: layout list)。"""
    return sorted(_LAYOUT_RENDERERS)


def render_layout_block(block: LayoutBlock, theme: WechatTheme | str) -> str:
    """渲染单个布局块; 未知模块抛 KeyError 并附可用列表。"""
    if isinstance(theme, str):
        theme = get_theme(theme)
    renderer = _LAYOUT_RENDERERS.get(block.module)
    if renderer is None:
        raise KeyError(
            f"unknown layout module {block.module!r}; available: {layout_modules()}"
        )
    return renderer(block, theme)


def render_markdown_with_layout(
    markdown: str,
    theme: WechatTheme | str = "default",
) -> tuple[str, list[str]]:
    """端到端: Markdown (含 ::: 布局块) → 主题化微信 HTML。

    布局块替换为渲染 HTML; 其余 Markdown 走确定性转换
    (wechat_publish.md_to_wechat_html), 再统一套主题内联样式。

    Args:
        markdown: 原始 Markdown (可含 ::: 布局块)。
        theme: 主题名或 WechatTheme。

    Returns:
        (html, used_modules) — used_modules 为实际命中的布局模块名列表。

    Raises:
        KeyError: 未知主题或未知布局模块。
    """
    if isinstance(theme, str):
        theme = get_theme(theme)
    blocks = parse_layout_blocks(markdown)
    used: list[str] = []
    for block in blocks:
        # 先校验模块存在 (do not guess), 再替换
        render_layout_block(block, theme)
        used.append(block.module)
    from oskill.wechat_publish import md_to_wechat_html

    # 替换布局块为占位标记, 避免 md 转换器把 ::: 当正文
    remaining = markdown
    for block in blocks:
        remaining = remaining.replace(block.raw, f"\n<!--LAYOUT:{block.module}-->\n", 1)
    html = md_to_wechat_html(remaining)
    for block, mod in zip(blocks, used, strict=True):
        rendered = render_layout_block(block, theme)
        html = html.replace(f"<!--LAYOUT:{mod}-->", rendered, 1)
    return apply_theme(html, theme), used


__all__ = [
    "LayoutBlock",
    "WechatTheme",
    "apply_theme",
    "get_theme",
    "layout_modules",
    "list_themes",
    "parse_layout_blocks",
    "register_layout_module",
    "register_theme",
    "render_layout_block",
    "render_markdown_with_layout",
]
