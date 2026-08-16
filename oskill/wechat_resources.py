"""oskill.wechat_resources — 公众号创作资源目录装配 (agent_discovery 应用层).

把 wechat_theme / wechat_writing / wechat_publish 的能力注册进
Discovery-First 资源目录 (ResourceCatalog), 供 Agent 面对不确定先 discover
再行动 (md2wechat "do not guess" 原则):

  * kind="theme"   — 内置主题 (detail=WechatTheme, show 后可取样式数据);
  * kind="layout"  — ::: 布局模块 (detail=渲染器说明);
  * kind="prompt"  — 创作 prompt 工厂 (detail=可调用函数, 返回 {system, user}):
    write / title / humanize / cover / infographic / advise / reviewer /
    reviser;
  * kind="wechat-flow" — 端到端能力说明 (生产/检查/发布/闭环), 供主脑路由。

零 veya 反向依赖; register_wechat_resources 幂等 (重复调用不重复注册)。
"""

from __future__ import annotations

from typing import Any

from oskill.agent_discovery import Resource, ResourceCatalog

_PROMPT_DESCRIPTIONS: dict[str, str] = {
    "write": "公众号写手 prompt 工厂 (钩子/小节/配图 brief, JSON 契约)",
    "title": "标题候选 prompt 工厂 (hook-level 1-3, JSON 数组契约)",
    "humanize": "去 AI 味改写 prompt 工厂",
    "cover": "封面图生图 prompt 计划工厂 (plan 模式, 不开图)",
    "infographic": "信息图生图 prompt 计划工厂 (plan 模式, 不开图)",
    "advise": "文章改进建议 prompt 工厂 (可注入 inspect 报告)",
    "reviewer": "审核官 prompt 工厂 (只读不改, 四维标准, JSON 契约)",
    "reviser": "定向改写 prompt 工厂 (只改被点名章节, JSON 契约)",
}

_LAYOUT_DESCRIPTIONS: dict[str, str] = {
    "hero": "开篇卡片 (eyebrow/title/subtitle 字段)",
    "card": "普通卡片 (方括号标题 + 正文)",
    "tip": "提示块 (绿)",
    "warning": "注意块 (黄)",
    "danger": "警告块 (红)",
    "quote": "金句引用块",
    "divider": "分隔线 (可带文字)",
    "table": "表格块 (rows 用 | 分隔)",
    "list": "要点列表块",
    "steps": "步骤块 (自动编号)",
}

_FLOW_DESCRIPTIONS: dict[str, str] = {
    "produce": "写手→审核→打回闭环产出图文 (WechatReviewLoop, LLM 注入分离)",
    "convert": "Markdown → 微信 HTML (确定性纯函数, 可选主题/布局)",
    "inspect": "发布前完整检查 (readiness/标题长度/违禁词/图片数)",
    "publish": "微信草稿箱发布 (draft/add) + 永久素材上传",
    "image-post": "图文/多图消息组装 (create_image_post)",
}


def register_wechat_resources(
    catalog: ResourceCatalog | None = None,
) -> ResourceCatalog:
    """把公众号主题/布局/prompt/流程注册进资源目录 (幂等, 可重复调用).

    Args:
        catalog: 目标目录; None 则新建。

    Returns:
        填充后的 ResourceCatalog。
    """
    from oskill import wechat_theme
    from oskill import wechat_writing

    catalog = catalog or ResourceCatalog()

    for theme in wechat_theme.list_themes():
        try:
            catalog.show("theme", theme["name"])
        except KeyError:
            catalog.register(
                Resource(
                    name=theme["name"],
                    kind="theme",
                    description=theme["description"],
                ),
                detail=wechat_theme.get_theme(theme["name"]),
            )

    for name, desc in _LAYOUT_DESCRIPTIONS.items():
        try:
            catalog.show("layout", name)
        except KeyError:
            catalog.register(
                Resource(name=name, kind="layout", description=desc),
                detail=desc,
            )

    prompt_factories = {
        "write": wechat_writing.write_prompt,
        "title": wechat_writing.title_prompt,
        "humanize": wechat_writing.humanize_prompt,
        "cover": wechat_writing.cover_prompt,
        "infographic": wechat_writing.infographic_prompt,
        "advise": wechat_writing.advise_prompt,
        "reviewer": wechat_writing.reviewer_prompt,
        "reviser": wechat_writing.reviser_prompt,
    }
    for name, factory in prompt_factories.items():
        try:
            catalog.show("prompt", name)
        except KeyError:
            catalog.register(
                Resource(
                    name=name,
                    kind="prompt",
                    description=_PROMPT_DESCRIPTIONS[name],
                ),
                detail=factory,
            )

    for name, desc in _FLOW_DESCRIPTIONS.items():
        try:
            catalog.show("wechat-flow", name)
        except KeyError:
            catalog.register(
                Resource(name=name, kind="wechat-flow", description=desc),
                detail=desc,
            )
    return catalog


def wechat_catalog() -> ResourceCatalog:
    """标准公众号资源目录 (每次调用返回新目录, 互不污染)."""
    return register_wechat_resources()


def catalog_summary(catalog: ResourceCatalog | None = None) -> dict[str, Any]:
    """capabilities 聚合视图 (Agent 开场 discover 用)."""
    catalog = catalog or wechat_catalog()
    return catalog.capabilities()


__all__ = ["catalog_summary", "register_wechat_resources", "wechat_catalog"]
