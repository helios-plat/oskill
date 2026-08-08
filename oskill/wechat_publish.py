"""oskill.wechat_publish — 微信公众号内容生产管道 + 发布 (md2wechat 机制 3O 内化)。

管道: Markdown → Article (标题/摘要/封面/HTML) → 草稿箱发布。
  * md_to_wechat_html — 确定性 Markdown→微信 HTML 转换 (标题/段落/粗斜体/
    代码块/行内码/图片/引用/有序无序列表/链接), 纯函数可验证;
  * produce_article — 组装 Article (标题/摘要/封面/作者/HTML);
  * publish_draft — 微信草稿 API 调用 (access_token 注入, 无副作用校验:
    调用方先 produce 再 publish, 两阶段分离);
  * ArticleStore — 本地草稿暂存 (JSON), 发布前检查 readiness。

零 veya 反向依赖: HTTP 调用由调用方注入 client; 转换与组装纯确定性。
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Markdown → 微信 HTML (确定性纯函数) ──────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_HR_RE = re.compile(r"^---+$")
_CODE_FENCE_RE = re.compile(r"^```(\w*)")
_TABLE_ROW_RE = re.compile(r"^\|.*\|$")
_TASK_ITEM_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*]|\d+[.)])\s+(.*)$")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*([^*\n]+)\*")
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def md_to_wechat_html(markdown: str) -> str:
    """把 Markdown 转成微信 HTML (确定性, 无外部依赖)。

    Args:
        markdown: markdown 文本。

    Returns:
        微信 HTML 字符串 (section 包裹, 支持标题/段落/列表/代码/图片/引用)。

    Example:
        >>> "<h1>" in md_to_wechat_html("# 标题\\n正文")
        True
    """
    lines = markdown.splitlines()
    html_lines: list[str] = []
    in_code = False
    in_quote = False
    in_list_ul: int = 0  # 0=不在列表, 1=ul, 2=ol
    list_type = ""

    def close_list() -> None:
        nonlocal in_list_ul
        if in_list_ul:
            html_lines.append(f"</{list_type}>")
            in_list_ul = 0

    def close_quote() -> None:
        nonlocal in_quote
        if in_quote:
            html_lines.append("</blockquote>")
            in_quote = False

    in_table = False
    for raw in lines:
        line = raw.rstrip()
        if in_code:
            if line.startswith("```"):
                html_lines.append("</code></pre>")
                in_code = False
            else:
                html_lines.append(html.escape(line))
            continue
        fence = _CODE_FENCE_RE.match(line)
        if fence:
            close_list()
            close_quote()
            lang = fence.group(1) or ""
            html_lines.append(f'<pre><code class="language-{html.escape(lang)}">')
            in_code = True
            continue
        if _TABLE_ROW_RE.match(line):
            close_list()
            close_quote()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r"[-:]+", c) for c in cells):
                continue
            if not in_table:
                html_lines.append("<table><tbody>")
                in_table = True
            html_lines.append(
                "<tr>" + "".join(f"<td>{_inline_format(c)}</td>" for c in cells) + "</tr>"
            )
            continue
        if in_table:
            html_lines.append("</tbody></table>")
            in_table = False
        if not line.strip():
            close_list()
            close_quote()
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            close_list()
            close_quote()
            level = len(heading.group(1))
            text = _inline_format(heading.group(2).strip())
            html_lines.append(f"<h{level}>{text}</h{level}>")
            continue
        if _HR_RE.match(line):
            close_list()
            close_quote()
            html_lines.append("<hr/>")
            continue
        if line.startswith(">"):
            close_list()
            if not in_quote:
                html_lines.append("<blockquote>")
                in_quote = True
            html_lines.append(f"<p>{_inline_format(line.lstrip('> ').strip())}</p>")
            continue
        task = _TASK_ITEM_RE.match(line)
        if task:
            checked = "checked" if task.group(1).lower() == "x" else ""
            content = _inline_format(task.group(2).strip())
            if not in_list_ul or list_type != "ul":
                close_list()
                html_lines.append("<ul>")
                in_list_ul = 1
                list_type = "ul"
            html_lines.append(f'<li><input type="checkbox" disabled {checked}/> {content}</li>')
            continue
        quote_or_list = _LIST_ITEM_RE.match(line)
        if quote_or_list:
            marker = quote_or_list.group(2)
            content = _inline_format(quote_or_list.group(3).strip())
            target = "ul" if marker in ("-", "*") else "ol"
            if not in_list_ul or list_type != target:
                close_list()
                html_lines.append(f"<{target}>")
                in_list_ul = 1
                list_type = target
            html_lines.append(f"<li>{content}</li>")
            continue
        close_list()
        close_quote()
        image = _IMAGE_RE.match(line.strip())
        if image:
            alt, src, title = image.groups()
            title_text = f' title="{html.escape(title)}"' if title else ""
            html_lines.append(
                f'<p><img src="{html.escape(src)}" alt="{html.escape(alt)}"{title_text}/></p>'
            )
            continue
        html_lines.append(f"<p>{_inline_format(line.strip())}</p>")
    close_list()
    close_quote()
    if in_code:
        html_lines.append("</code></pre>")
    return "<section>" + "\n".join(html_lines) + "</section>"


def _inline_format(text: str) -> str:
    """行内格式: 图片/链接/粗体/斜体/行内码 → HTML (顺序敏感)。"""
    text = _IMAGE_RE.sub(
        lambda m: f'<img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}"/>',
        text,
    )
    text = _LINK_RE.sub(
        lambda m: f'<a href="{html.escape(m.group(2))}">{html.escape(m.group(1))}</a>',
        text,
    )
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _INLINE_CODE_RE.sub(r"<code>\1</code>", text)
    return text


# ── Article 组装 ─────────────────────────────────────────────────────


@dataclass
class Article:
    """一篇公众号文章 (生产管道产物)。

    Attributes:
        title: 标题。
        content_html: 正文 HTML。
        summary: 摘要 (可选)。
        cover_url: 封面图 URL (可选)。
        author: 作者。
        thumb_media_id: 封面 media_id (发布时用, 可选)。
    """

    title: str
    content_html: str
    summary: str = ""
    cover_url: str = ""
    author: str = ""
    thumb_media_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content_html,
            "digest": self.summary,
            "author": self.author,
            "thumb_media_id": self.thumb_media_id,
            "cover_url": self.cover_url,
        }


def produce_article(
    markdown: str,
    *,
    title: str,
    summary: str = "",
    cover_url: str = "",
    author: str = "",
) -> Article:
    """从 Markdown 组装一篇 Article (转换 + 元数据)。

    Args:
        markdown: markdown 正文。
        title: 标题。
        summary / cover_url / author: 元数据。

    Returns:
        Article (content_html 由 md_to_wechat_html 生成)。
    """
    return Article(
        title=title,
        content_html=md_to_wechat_html(markdown),
        summary=summary,
        cover_url=cover_url,
        author=author,
    )


# ── 本地草稿暂存 + readiness ────────────────────────────────────────


class ArticleStore:
    """本地草稿暂存 (JSON), 发布前 readiness 检查。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.articles: dict[str, Article] = {}
        if self.path and self.path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for key, item in data.items():
                item = dict(item)
                if "digest" in item and "summary" not in item:
                    item["summary"] = item.pop("digest")
                if "content" in item and "content_html" not in item:
                    item["content_html"] = item.pop("content")
                self.articles[key] = Article(**item)
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    def save_article(self, key: str, article: Article) -> None:
        """暂存草稿。"""
        self.articles[key] = article
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {k: v.to_dict() for k, v in self.articles.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def get_article(self, key: str) -> Article | None:
        return self.articles.get(key)

    def readiness(self, key: str) -> dict[str, Any]:
        """发布前检查: 标题/正文/摘要/封面是否就绪。

        Args:
            key: 草稿键。

        Returns:
            {ready, targets, blockers} — targets 为已就绪项, blockers 为缺失项。
        """
        article = self.articles.get(key)
        if article is None:
            return {"ready": False, "targets": [], "blockers": ["article not found"]}
        targets: list[str] = []
        blockers: list[str] = []
        if article.title:
            targets.append("title")
        else:
            blockers.append("title")
        if article.content_html:
            targets.append("content")
        else:
            blockers.append("content")
        if article.summary:
            targets.append("summary")
        else:
            blockers.append("summary")
        if article.cover_url or article.thumb_media_id:
            targets.append("cover")
        else:
            blockers.append("cover")
        return {"ready": not blockers, "targets": targets, "blockers": blockers}


# ── 微信草稿发布 ─────────────────────────────────────────────────────


def publish_draft(
    article: Article,
    *,
    access_token: str,
    client: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """把 Article 发布到微信公众号草稿箱。

    Args:
        article: 待发布文章。
        access_token: 微信接口 access_token (调用方获取)。
        client: HTTP 调用注入 (默认用 urllib); 返回值须为响应 dict
            (含 media_id 或 errcode)。

    Returns:
        {ok, media_id?, errcode?, errmsg?}。

    Example:
        >>> r = publish_draft(Article("t", "<p>x</p>"), access_token="tok",
        ...                    client=lambda **kw: {"media_id": "m1"})
        >>> r["ok"]
        True
    """
    payload = {
        "articles": [
            {
                "title": article.title,
                "author": article.author,
                "digest": article.summary,
                "content": article.content_html,
                "thumb_media_id": article.thumb_media_id,
            }
        ],
    }
    if client is not None:
        response = client(url="draft/add", access_token=access_token, payload=payload)
    else:
        import urllib.request

        req = urllib.request.Request(
            f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = json.loads(resp.read().decode("utf-8"))
    media_id = response.get("media_id")
    if media_id:
        return {"ok": True, "media_id": media_id}
    return {
        "ok": False,
        "errcode": response.get("errcode"),
        "errmsg": response.get("errmsg", "unknown error"),
    }


__all__ = ["Article", "ArticleStore", "md_to_wechat_html", "produce_article", "publish_draft"]
