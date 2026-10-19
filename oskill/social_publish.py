"""oskill.social_publish — 多平台内容发布 + 变现结算 (AiToEarn 机制 3O 内化)。

把 veya 的单平台 wechat_publish 扩展为**多平台发布注册表**:
  * **平台适配器** — PlatformAdapter ABC (convert/draft/publish/limits),
    可插拔注册 (Discovery-First: register_platform/get_platform/list_platforms);
  * **平台能力差异路由** — PlatformCapabilities (视频/图文/文本支持 + 平台
    限制表: 标题长度/视频时长/图片数), content_limits 确定性查询;
  * **批量草稿生成** — batch_draft (多平台批量, 平台限制内裁剪);
  * **环境分离** — cn/intl 两套 URL + Key 匹配校验 (Key-环境不匹配拒绝);
  * **变现结算** — SocialTask (商家任务: 价格/状态) + Settlement (结算模式:
    fixed/按量/分成)。

零 veya 反向依赖: 平台发布函数由适配器实现/调用方注入; 限制表确定性。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

ENV_CN = "cn"
ENV_INTL = "intl"
ENVIRONMENTS = (ENV_CN, ENV_INTL)

PLATFORM_WECHAT = "wechat"
PLATFORM_XIAOHONGSHU = "xiaohongshu"
PLATFORM_TIKTOK = "tiktok"
PLATFORM_YOUTUBE = "youtube"
PLATFORM_DOUYIN = "douyin"

# ── 平台能力与限制 ───────────────────────────────────────────────────


@dataclass(frozen=True)
class PlatformCapabilities:
    """平台能力面 (路由依据: 平台支持什么, 内容怎么发)。

    Attributes:
        supports_video / supports_image / supports_text: 内容形态支持。
        max_title_len: 标题最大字符。
        max_video_sec: 视频最长秒数。
        max_images: 图文最大图片数。
        max_text_len: 纯文本最大字符。
        needs_cover: 是否需要封面。
    """

    supports_video: bool = False
    supports_image: bool = True
    supports_text: bool = True
    max_title_len: int = 80
    max_video_sec: int | None = None
    max_images: int = 9
    max_text_len: int = 2000
    needs_cover: bool = False


@dataclass(frozen=True)
class PlatformCredential:
    """平台凭证 (含环境绑定)。

    Attributes:
        platform: 平台 id。
        token: 访问令牌/密钥。
        env: cn / intl (环境与 Key 不匹配拒绝)。
        meta: 附加 (账号/频道 id 等)。
    """

    platform: str
    token: str
    env: str = ENV_CN
    meta: dict[str, Any] = field(default_factory=dict)


# ── 平台适配器 ───────────────────────────────────────────────────────


@dataclass
class PublishResult:
    """发布结果。"""

    ok: bool
    platform: str
    content_id: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "platform": self.platform,
            "content_id": self.content_id,
            "error": self.error[:300],
            "details": self.details,
        }


class PlatformAdapter(ABC):
    """平台适配器抽象 (convert/draft/publish/limits)。"""

    platform_id: str = ""
    capabilities: PlatformCapabilities = PlatformCapabilities()

    @abstractmethod
    def convert(self, content: dict[str, Any]) -> Any:
        """内容 → 平台格式 (HTML/接口 payload)。"""

    @abstractmethod
    def publish(self, content: dict[str, Any], credential: PlatformCredential) -> PublishResult:
        """发布到平台 (调用方注入 HTTP 或真实实现)。"""


class WechatAdapter(PlatformAdapter):
    """微信适配器: 复用 wechat_publish 的 md→HTML 转换。"""

    platform_id = PLATFORM_WECHAT
    capabilities = PlatformCapabilities(supports_text=True, max_title_len=64, max_text_len=10000)

    def convert(self, content: dict[str, Any]) -> dict[str, Any]:
        from oskill.wechat_publish import produce_article

        markdown = content.get("markdown", content.get("text", ""))
        article = produce_article(
            markdown,
            title=content.get("title", "未命名"),
            summary=content.get("summary", ""),
            cover_url=content.get("cover_url", ""),
        )
        return {"article": article.to_dict(), "env": content.get("env", ENV_CN)}

    def publish(self, content: dict[str, Any], credential: PlatformCredential) -> PublishResult:
        from oskill.wechat_publish import Article, publish_draft

        article_dict = self.convert(content)["article"]
        article = Article(
            title=article_dict["title"],
            content_html=article_dict["content"],
            summary=article_dict.get("digest", ""),
            author=article_dict.get("author", ""),
            cover_url=article_dict.get("cover_url", ""),
            thumb_media_id=article_dict.get("thumb_media_id", ""),
        )
        result = publish_draft(
            article,
            access_token=credential.token,
        )
        if result["ok"]:
            return PublishResult(ok=True, platform=self.platform_id, content_id=result["media_id"])
        return PublishResult(
            ok=False, platform=self.platform_id, error=result.get("errmsg", "publish failed")
        )


class GenericHttpAdapter(PlatformAdapter):
    """通用 HTTP 适配器 (小红书/抖音/TikTok/YouTube 等占位): 发布函数注入。"""

    def __init__(
        self,
        platform_id: str,
        capabilities: PlatformCapabilities,
        publish_fn: Callable[[dict[str, Any], PlatformCredential], PublishResult] | None = None,
    ) -> None:
        self.platform_id = platform_id
        self.capabilities = capabilities
        self._publish_fn = publish_fn

    def convert(self, content: dict[str, Any]) -> dict[str, Any]:
        # 按平台能力裁剪内容
        caps = self.capabilities
        title = content.get("title", "")[: caps.max_title_len]
        text = content.get("text", "")[: caps.max_text_len]
        images = content.get("images", [])[: caps.max_images] if caps.supports_image else []
        return {
            "title": title,
            "text": text,
            "images": images,
            "video": content.get("video") if caps.supports_video else None,
            "env": content.get("env", ENV_CN),
        }

    def publish(self, content: dict[str, Any], credential: PlatformCredential) -> PublishResult:
        converted = self.convert(content)
        if self._publish_fn is None:
            return PublishResult(
                ok=False, platform=self.platform_id, error="publish_fn 未注入 (占位适配器)"
            )
        try:
            result = self._publish_fn(converted, credential)
            return result
        except Exception as exc:  # noqa: BLE001
            return PublishResult(
                ok=False, platform=self.platform_id, error=f"{exc.__class__.__name__}: {exc}"
            )


# ── 注册表 (Discovery-First) ─────────────────────────────────────────

_ADAPTERS: dict[str, PlatformAdapter] = {}


def register_platform(adapter: PlatformAdapter) -> None:
    """注册平台适配器 (幂等覆盖)。"""
    _ADAPTERS[adapter.platform_id] = adapter


def get_platform(platform_id: str) -> PlatformAdapter:
    """取适配器; 未知平台抛 ValueError (列出可用)。"""
    if platform_id not in _ADAPTERS:
        raise ValueError(f"unknown platform: {platform_id!r}; available: {list_platforms()}")
    return _ADAPTERS[platform_id]


def list_platforms() -> list[str]:
    """已注册平台 (Discovery-First)。"""
    return sorted(_ADAPTERS)


def content_limits(platform_id: str) -> dict[str, Any]:
    """平台内容限制 (确定性查询, 供 LLM 路由前裁剪)。"""
    adapter = get_platform(platform_id)
    caps = adapter.capabilities
    return {
        "max_title_len": caps.max_title_len,
        "max_video_sec": caps.max_video_sec,
        "max_images": caps.max_images,
        "max_text_len": caps.max_text_len,
        "needs_cover": caps.needs_cover,
    }


# ── 发布路由 + 环境校验 ──────────────────────────────────────────────


def _check_env(content: dict[str, Any], credential: PlatformCredential) -> str | None:
    """环境-凭证匹配校验 (cn Key 只能配 cn URL, 不匹配拒绝)。"""
    content_env = content.get("env", ENV_CN)
    if content_env != credential.env:
        return f"环境不匹配: 内容={content_env}, 凭证={credential.env} (cn/intl 必须一致)"
    return None


def publish_to(content: dict[str, Any], credential: PlatformCredential) -> PublishResult:
    """路由到平台适配器发布 (含环境校验)。

    Args:
        content: 内容 (title/text/images/video/env...)。
        credential: 平台凭证 (含环境)。

    Returns:
        PublishResult。
    """
    env_error = _check_env(content, credential)
    if env_error:
        return PublishResult(ok=False, platform=credential.platform, error=env_error)
    adapter = get_platform(credential.platform)
    return adapter.publish(content, credential)


# ── 批量草稿生成 ─────────────────────────────────────────────────────


def batch_draft(
    content: dict[str, Any],
    platforms: list[str],
    credentials: dict[str, PlatformCredential],
) -> list[dict[str, Any]]:
    """多平台批量草稿: 按各平台限制裁剪 → 逐平台生成草稿 (不发, 仅草稿)。

    Args:
        content: 内容 (title/text/images/video/env)。
        platforms: 目标平台列表。
        credentials: 平台 → 凭证。

    Returns:
        每平台结果 [{platform, ok, drafted, limits, error}]。
    """
    results: list[dict[str, Any]] = []
    for platform_id in platforms:
        try:
            adapter = get_platform(platform_id)
            credential = credentials.get(platform_id)
            if credential is None:
                results.append({"platform": platform_id, "ok": False, "error": "无凭证"})
                continue
            env_error = _check_env(content, credential)
            if env_error:
                results.append({"platform": platform_id, "ok": False, "error": env_error})
                continue
            converted = adapter.convert(content)  # 按能力裁剪
            results.append(
                {
                    "platform": platform_id,
                    "ok": True,
                    "drafted": converted,
                    "limits": content_limits(platform_id),
                }
            )
        except ValueError as exc:
            results.append({"platform": platform_id, "ok": False, "error": str(exc)})
    return results


# ── 变现结算 ─────────────────────────────────────────────────────────

SETTLEMENT_FIXED = "fixed"
SETTLEMENT_PER_UNIT = "per_unit"
SETTLEMENT_REVENUE_SHARE = "revenue_share"
SETTLEMENT_MODES = (SETTLEMENT_FIXED, SETTLEMENT_PER_UNIT, SETTLEMENT_REVENUE_SHARE)


@dataclass
class SocialTask:
    """一个变现任务 (商家发布的需求)。

    Attributes:
        id: 任务 id。
        merchant: 商家。
        description: 需求描述。
        price: 任务价格 (固定/单价/分成基数)。
        settlement: 结算模式 (fixed/per_unit/revenue_share)。
        status: pending/in_progress/completed/settled。
    """

    id: str
    merchant: str
    description: str = ""
    price: float = 0.0
    settlement: str = SETTLEMENT_FIXED
    status: str = "pending"
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "merchant": self.merchant,
            "description": self.description,
            "price": self.price,
            "settlement": self.settlement,
            "status": self.status,
        }


def settle(task: SocialTask, *, units: int | None = None, revenue: float | None = None) -> float:
    """按结算模式计算应付金额。

    Args:
        task: 任务。
        units: per_unit 模式的完成量。
        revenue: revenue_share 模式的分成基数。

    Returns:
        应付金额。

    Example:
        >>> t = SocialTask("t1", "商家", price=100, settlement="fixed")
        >>> settle(t)
        100.0
    """
    if task.settlement == SETTLEMENT_FIXED:
        return task.price
    if task.settlement == SETTLEMENT_PER_UNIT:
        return task.price * (units or 0)
    if task.settlement == SETTLEMENT_REVENUE_SHARE:
        return (revenue or 0) * task.price  # price 为分成比例
    return 0.0


def mark_settled(task: SocialTask) -> SocialTask:
    """任务置为 settled (结算完成)。"""
    task.status = "settled"
    return task


# ── 默认装配 ─────────────────────────────────────────────────────────


def _ensure_default_platforms() -> None:
    if PLATFORM_WECHAT not in _ADAPTERS:
        register_platform(WechatAdapter())
    if PLATFORM_XIAOHONGSHU not in _ADAPTERS:
        register_platform(
            GenericHttpAdapter(
                PLATFORM_XIAOHONGSHU,
                PlatformCapabilities(supports_image=True, max_title_len=20, max_images=18),
            )
        )
    if PLATFORM_TIKTOK not in _ADAPTERS:
        register_platform(
            GenericHttpAdapter(
                PLATFORM_TIKTOK,
                PlatformCapabilities(supports_video=True, max_video_sec=600, max_title_len=80),
            )
        )
    if PLATFORM_YOUTUBE not in _ADAPTERS:
        register_platform(
            GenericHttpAdapter(
                PLATFORM_YOUTUBE,
                PlatformCapabilities(supports_video=True, max_video_sec=43200, max_title_len=100),
            )
        )


_ensure_default_platforms()


__all__ = [
    "ENV_CN",
    "ENV_INTL",
    "GenericHttpAdapter",
    "PLATFORM_DOUYIN",
    "PLATFORM_TIKTOK",
    "PLATFORM_WECHAT",
    "PLATFORM_XIAOHONGSHU",
    "PLATFORM_YOUTUBE",
    "PlatformAdapter",
    "PlatformCapabilities",
    "PlatformCredential",
    "PublishResult",
    "SETTLEMENT_FIXED",
    "SETTLEMENT_PER_UNIT",
    "SETTLEMENT_REVENUE_SHARE",
    "SocialTask",
    "WechatAdapter",
    "batch_draft",
    "content_limits",
    "get_platform",
    "list_platforms",
    "mark_settled",
    "publish_to",
    "register_platform",
    "settle",
]
