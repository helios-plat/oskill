"""oskill.smart_web_scraping — 自适应抗封锁网抓与智能 HTML 内容抽取复合技能.

Stateless 纯算法。依赖 AdaptiveScraper + extractor_op + LLMCallerProtocol 注入.

组合: scraper_op (注入) + extractor_op (注入) + LLM caller (注入).

遵循 oskill 红线: 依赖必须函数内惰性 + Protocol 注入.
"""

from __future__ import annotations

from typing import Any, Protocol


class ScraperProtocol(Protocol):
    """自适应抓取器 Protocol — 不 import obase，由调用方注入."""

    def fetch_with_stealth(self, url: str) -> dict[str, Any]: ...


class ExtractorProtocol(Protocol):
    """节点抽取器 Protocol."""

    def __call__(
        self, html_content: str, *, target_semantic: str = "article-content"
    ) -> dict[str, Any]: ...


class LLMCallerProtocol(Protocol):
    """LLM 调用 Protocol."""

    def __call__(self, prompt: str, *, temperature: float = 0.0, **kwargs: Any) -> str: ...


def smart_web_scraping(
    target_url: str,
    *,
    scraper_op: ScraperProtocol,
    extractor_op: ExtractorProtocol,
    llm_caller: LLMCallerProtocol,
) -> dict[str, Any]:
    """自适应抗封锁网抓与智能 HTML 内容抽取复合技能 (Scrapling).

    流程:
    1. 带伪造指纹抓取原始 HTML
    2. 自适应语义节点抽离核心内容
    3. LLM 提炼总结

    Args:
        target_url: 目标网页 URL
        scraper_op: 自适应抓取器（注入）
        extractor_op: HTML 节点抽取器（注入）
        llm_caller: LLM 调用接口（注入）

    Returns:
        {
            "url": str,
            "anchor_confidence": float,
            "summary": str,
            "status": "success" | "fallback" | "failed",
        }
    """
    try:
        # Step 1: 带伪造指纹抓取
        raw_page = scraper_op.fetch_with_stealth(target_url)
    except Exception as e:
        return {
            "url": target_url,
            "anchor_confidence": 0.0,
            "summary": "",
            "status": "failed",
            "error": f"Fetch failed: {type(e).__name__}: {e}",
        }

    html = raw_page.get("html", "")
    if not html:
        return {
            "url": target_url,
            "anchor_confidence": 0.0,
            "summary": "",
            "status": "failed",
            "error": "Empty response body",
        }

    # Step 2: 自适应节点抽离
    try:
        extracted = extractor_op(html, target_semantic="article-content")
    except Exception:
        extracted = {
            "status": "fallback",
            "extracted_content": html[:1000],
            "anchor_confidence": 0.2,
        }

    extracted_text = extracted.get("extracted_content", html[:500])

    # Step 3: LLM 提炼总结
    try:
        prompt = (
            f"Summarize the following extracted web content from {target_url} "
            f"in 2-3 sentences:\n\n{extracted_text[:1500]}"
        )
        summary = llm_caller(prompt, temperature=0.1).strip()
    except Exception:
        summary = extracted_text[:200]

    return {
        "url": target_url,
        "anchor_confidence": extracted.get("anchor_confidence", 0.5),
        "summary": summary,
        "status": extracted.get("status", "success"),
    }
