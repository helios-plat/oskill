"""Tests for social_publish (AiToEarn 多平台发布 + 变现 3O 内化)。"""

from __future__ import annotations

import pytest

from oskill.social_publish import (
    ENV_CN,
    ENV_INTL,
    PLATFORM_TIKTOK,
    PLATFORM_WECHAT,
    PLATFORM_XIAOHONGSHU,
    PLATFORM_YOUTUBE,
    SETTLEMENT_FIXED,
    SETTLEMENT_PER_UNIT,
    SETTLEMENT_REVENUE_SHARE,
    PlatformAdapter,
    PlatformCapabilities,
    PlatformCredential,
    PublishResult,
    SocialTask,
    WechatAdapter,
    batch_draft,
    content_limits,
    get_platform,
    list_platforms,
    mark_settled,
    publish_to,
    register_platform,
    settle,
)

# ── 平台注册表 (Discovery-First) ─────────────────────────────────────


def test_default_platforms_registered():
    platforms = list_platforms()
    assert {"wechat", "xiaohongshu", "tiktok", "youtube"} <= set(platforms)


def test_get_unknown_platform_raises():
    with pytest.raises(ValueError, match="unknown platform"):
        get_platform("nope")


def test_register_custom_platform():
    class _Custom(PlatformAdapter):
        platform_id = "custom"
        capabilities = PlatformCapabilities(supports_text=True)

        def convert(self, content):
            return content

        def publish(self, content, credential):
            return PublishResult(ok=True, platform=self.platform_id, content_id="c1")

    register_platform(_Custom())
    assert "custom" in list_platforms()
    assert get_platform("custom").publish({}, PlatformCredential("custom", "t")).ok is True


# ── 平台能力差异路由 ────────────────────────────────────────────────


def test_content_limits_differ_by_platform():
    xhs = content_limits(PLATFORM_XIAOHONGSHU)
    youtube = content_limits(PLATFORM_YOUTUBE)
    assert xhs["max_images"] == 18  # 小红书图多
    assert youtube["max_video_sec"] == 43200  # YouTube 视频长
    assert xhs["max_video_sec"] is None


def test_generic_adapter_clips_by_capabilities():
    adapter = get_platform(PLATFORM_XIAOHONGSHU)
    content = {"title": "x" * 100, "text": "y" * 5000, "images": list(range(30))}
    converted = adapter.convert(content)
    assert len(converted["title"]) == 20  # xhs 标题 20
    assert len(converted["images"]) == 18  # xhs 图 18


def test_tiktok_video_only():
    adapter = get_platform(PLATFORM_TIKTOK)
    content = {"title": "t", "text": "x", "video": "/v.mp4"}
    converted = adapter.convert(content)
    assert converted["video"] == "/v.mp4"
    assert converted["images"] == []  # tiktok 无图片字段


# ── 环境分离 (cn/intl) ──────────────────────────────────────────────


def test_env_mismatch_rejected():
    credential = PlatformCredential(platform=PLATFORM_WECHAT, token="cn-token", env=ENV_CN)
    result = publish_to({"title": "t", "text": "x", "env": ENV_INTL}, credential)
    assert result.ok is False
    assert "环境不匹配" in result.error


def test_env_match_passes_to_publish():
    calls = []

    class _Spy(PlatformAdapter):
        platform_id = "spy"
        capabilities = PlatformCapabilities()

        def convert(self, content):
            return content

        def publish(self, content, credential):
            calls.append((content, credential.env))
            return PublishResult(ok=True, platform=self.platform_id)

    register_platform(_Spy())
    result = publish_to(
        {"title": "t", "env": ENV_INTL},
        PlatformCredential("spy", "intl-token", env=ENV_INTL),
    )
    assert result.ok is True
    assert calls[0][1] == ENV_INTL


# ── 微信适配器 (复用 wechat_publish) ────────────────────────────────


def test_wechat_adapter_convert():
    adapter = WechatAdapter()
    converted = adapter.convert({"title": "标题", "markdown": "# 标题\n正文", "env": ENV_CN})
    assert "<section>" in converted["article"]["content"]
    assert converted["article"]["title"] == "标题"


def test_wechat_adapter_publish_error_without_token():
    adapter = WechatAdapter()
    # 空 token → 微信 API 401 (或 client 错误), 返回 ok=False 不崩
    result = adapter.publish(
        {"title": "t", "markdown": "x", "env": ENV_CN},
        PlatformCredential(PLATFORM_WECHAT, "", env=ENV_CN),
    )
    assert result.ok is False


# ── 批量草稿生成 ─────────────────────────────────────────────────────


def test_batch_draft_multi_platform():
    credentials = {
        PLATFORM_WECHAT: PlatformCredential(PLATFORM_WECHAT, "tok", env=ENV_CN),
        PLATFORM_XIAOHONGSHU: PlatformCredential(PLATFORM_XIAOHONGSHU, "tok", env=ENV_CN),
        PLATFORM_YOUTUBE: PlatformCredential(PLATFORM_YOUTUBE, "tok", env=ENV_CN),
    }
    results = batch_draft(
        {"title": "夏日新品", "text": "正文", "images": list(range(30)), "env": ENV_CN},
        [PLATFORM_WECHAT, PLATFORM_XIAOHONGSHU, PLATFORM_YOUTUBE],
        credentials,
    )
    assert len(results) == 3
    assert all(r["ok"] for r in results)
    xhs = next(r for r in results if r["platform"] == PLATFORM_XIAOHONGSHU)
    assert len(xhs["drafted"]["images"]) == 18  # 平台限制裁剪


def test_batch_draft_env_mismatch_flags():
    results = batch_draft(
        {"title": "t", "text": "x", "env": ENV_INTL},
        [PLATFORM_WECHAT],
        {PLATFORM_WECHAT: PlatformCredential(PLATFORM_WECHAT, "tok", env=ENV_CN)},
    )
    assert results[0]["ok"] is False
    assert "环境不匹配" in results[0]["error"]


# ── 变现结算 ─────────────────────────────────────────────────────────


def test_settle_fixed():
    task = SocialTask("t1", "商家", price=100, settlement=SETTLEMENT_FIXED)
    assert settle(task) == 100


def test_settle_per_unit():
    task = SocialTask("t2", "商家", price=50, settlement=SETTLEMENT_PER_UNIT)
    assert settle(task, units=10) == 500
    assert settle(task) == 0  # 无 units


def test_settle_revenue_share():
    task = SocialTask("t3", "商家", price=0.3, settlement=SETTLEMENT_REVENUE_SHARE)
    assert settle(task, revenue=1000) == 300  # 30% 分成


def test_mark_settled():
    task = SocialTask("t4", "商家")
    mark_settled(task)
    assert task.status == "settled"
    assert task.to_dict()["status"] == "settled"
