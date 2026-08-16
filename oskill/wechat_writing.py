"""oskill.wechat_writing — 公众号创作增强: prompt 工厂 + 确定性合规扫描
(md2wechat write/humanize/title/cover/infographic/advise 3O 内化增强)。

对标 md2wechat:
  * write — 按主题/风格生成写作 prompt;
  * title suggest — 标题候选 prompt (hook-level 参数化);
  * humanize — 去 AI 味 prompt;
  * generate_cover / generate_infographic — 封面/信息图生图 prompt 计划
    (plan 模式: 只产出 prompt, 交给宿主生图工具);
  * advise — 基于 inspect 报告的建议 prompt。
更强:
  * 全部 prompt 工厂化: 只产出 (system, user) prompt 文本 + 输出契约,
    **不调模型** — LLM 由调用方注入, 任何项目可复用;
  * 确定性合规扫描器 scan_compliance: 微信广告法常见违禁用语规则表
    (绝对化/医疗功效/金融承诺/夸大宣传/诱导分享), 正则命中 + 上下文
    snippet, 可测可解释 — md2wechat inspect 只查元数据不查违禁词;
  * 写作 prompt 吸收主链路 produce_wechat_article 的成熟设定 (钩子开头/
    小节结构/配图 brief), 输出 JSON 契约可直接用于闭环。

零 veya 反向依赖: 纯标准库, 全部纯函数。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ── prompt 工厂 ──────────────────────────────────────────────────────


def write_prompt(
    topic: str,
    *,
    audience: str = "",
    style: str = "",
    structure: str = "",
    requirements: str = "",
    with_image_brief: bool = True,
) -> dict[str, str]:
    """公众号写作 prompt (写手).

    Args:
        topic: 文章主题。
        audience: 目标读者 (可选)。
        style: 风格要求 (口语化/专业/幽默... 可选)。
        structure: 小节结构要求 (可选, 如 "3 个小节: 问题/方法/案例")。
        requirements: 其他硬性要求。
        with_image_brief: 是否要求每节带配图 brief。

    Returns:
        {"system": ..., "user": ...} — 输出契约: 单 JSON 对象
        {title, sections[{heading, body, image_brief?}], closing}。
    """
    sys_lines = [
        "你是资深公众号(微信公众号)编辑与新媒体写手。根据用户给的主题与要求撰写一篇完整的公众号图文文章。",
        "写作规范:",
        '- 开头必须有钩子(痛点/悬念/数据), 避免"大家好"式寒暄',
        "- 正文分 3-6 个小节, 每节一个小标题(heading)",
    ]
    if with_image_brief:
        sys_lines.append(
            '- 每节标注一句配图需求 image_brief (具体到"这张图该展示什么", 不要写"配图"这种空话)'
        )
    sys_lines += [
        "- 结尾要有互动引导或行动号召(closing)",
        "- 语言口语化、短句为主, 适合手机阅读",
        "只返回一个 JSON 对象, 不要任何其他文字:",
        '{"title": "...", "sections": [{"heading": "...", "body": "..."'
        + (', "image_brief": "..."' if with_image_brief else "")
        + '}], "closing": "..."}',
    ]
    user = f"主题: {topic}"
    if audience:
        user += f"\n目标读者: {audience}"
    if style:
        user += f"\n风格: {style}"
    if structure:
        user += f"\n结构要求: {structure}"
    if requirements:
        user += f"\n其他要求: {requirements}"
    return {"system": "\n".join(sys_lines), "user": user}


def title_prompt(article: str, *, n_candidates: int = 5, hook_level: int = 2) -> dict[str, str]:
    """标题候选 prompt (title suggest).

    Args:
        article: 文章全文 (Markdown 或纯文本)。
        n_candidates: 候选数 (1-10)。
        hook_level: 钩子强度 1-3 (1=平实, 2=悬念/数据, 3=强冲突/反差)。

    Returns:
        {"system": ..., "user": ...} — 输出契约: JSON 数组
        [{title, hook_type, reason}]。
    """
    n_candidates = max(1, min(int(n_candidates), 10))
    hook_level = max(1, min(int(hook_level), 3))
    hook_desc = {
        1: "平实直接, 说清文章内容即可",
        2: "带悬念/数据/痛点, 提升点击欲",
        3: "强冲突/反差/反常识, 冲击力优先(注意不要标题党到违规)",
    }[hook_level]
    system = (
        "你是公众号标题专家。根据文章内容生成标题候选, 只做建议不做最终选择。\n"
        f"钩子强度: {hook_desc}\n"
        "标题规范: 不超过 64 字; 不用绝对化用语(最/第一/唯一/绝对); "
        "不用低俗/恐吓/诱导分享词; 保留文章核心信息。\n"
        "只返回一个 JSON 数组, 不要任何其他文字:\n"
        f'[{{"title": "...", "hook_type": "悬念|数据|痛点|反差|平实", "reason": "为什么有效"}}] (共 {n_candidates} 个)'
    )
    return {"system": system, "user": f"文章内容:\n{article[:6000]}"}


def humanize_prompt(text: str) -> dict[str, str]:
    """去 AI 味 prompt (humanize).

    Returns:
        {"system": ..., "user": ...} — 输出契约: 改写后的纯文本, 无其他文字。
    """
    system = (
        "你是公众号文字编辑, 负责去除文章的 AI 味, 保留原意与结构。\n"
        "改写规则:\n"
        "- 删除 '首先/其次/最后/总而言之/综上所述/值得一提的是' 等模板连接词\n"
        "- 打破过于整齐的排比与对仗, 让节奏有变化\n"
        "- 删除空泛金句与正确废话 (如 '在当今快节奏的社会')\n"
        "- 短句化: 一句话超过 40 字就拆分\n"
        "- 加入口语化表达与具体细节, 像真人聊天一样自然\n"
        "只返回改写后的全文, 不要任何解释、前后缀或 Markdown 代码围栏。"
    )
    return {"system": system, "user": f"原文:\n{text}"}


def cover_prompt(topic: str, *, style: str = "", palette: str = "") -> dict[str, str]:
    """封面图 prompt 计划 (generate_cover 的 plan 模式: 只产出 prompt).

    Returns:
        {"system": ..., "user": ...} — 输出契约: JSON 对象
        {prompt, negative_prompt, aspect_ratio, style_tags}。
    """
    system = (
        "你是公众号封面设计策划。为文章设计封面图生图 prompt (供生图工具使用), "
        "不开图、不调模型。\n"
        "设计原则: 主体突出(3-5 个词)、留白、大字标题位、品牌统一、符合公众号封面 2.35:1 或 1:1。\n"
        "只返回一个 JSON 对象, 不要任何其他文字:\n"
        '{"prompt": "...", "negative_prompt": "...", "aspect_ratio": "2.35:1", '
        '"style_tags": ["..."], "title_hint": "适合压在封面上的 4-8 字短标题"}'
    )
    user = f"主题: {topic}"
    if style:
        user += f"\n风格: {style}"
    if palette:
        user += f"\n配色: {palette}"
    return {"system": system, "user": user}


def infographic_prompt(topic: str, points: list[str]) -> dict[str, str]:
    """信息图 prompt 计划 (generate_infographic 的 plan 模式).

    Args:
        topic: 信息图主题。
        points: 要呈现的核心要点 (3-8 条)。

    Returns:
        {"system": ..., "user": ...} — 输出契约: JSON 对象
        {prompt, layout, max_points}。
    """
    system = (
        "你是公众号信息图设计师。把要点设计成一张信息图生图 prompt, "
        "不开图、不调模型。\n"
        "设计原则: 一图一主题; 要点分层(主数字/次结论); 阅读顺序明确; 微信宽度适配。\n"
        "只返回一个 JSON 对象, 不要任何其他文字:\n"
        '{"prompt": "...", "layout": "vertical-steps|grid|flow|hierarchy", '
        '"max_points": 5, "accent_style": "..."}'
    )
    user = f"主题: {topic}\n要点:\n" + "\n".join(f"- {p}" for p in points[:8])
    return {"system": system, "user": user}


def reviewer_prompt() -> dict[str, str]:
    """审核官 prompt (只读不改; 供审核闭环 reviewer 注入).

    四维审核标准: topic_match / compliance / image_match / readability。
    输出契约: JSON 对象 {pass, issues[{criterion, section, detail,
    fix_instruction}]}。compliance 可另注入 scan_compliance 的确定性命中
    作为证据 (见 review_draft 的拼接约定)。

    Returns:
        {"system": ..., "user_extra": ...} — user_extra 为调用方拼进
        user prompt 的占位模板 (含 {sections}/{image_miss_streak} 槽位)。
    """
    system = (
        "你是公众号内容审核官, 只审核不改写。依据下面四项标准判断这篇文章能否发布:\n"
        "1. topic_match: 是否严格贴合给定主题与要求\n"
        "2. compliance: 是否含公众号违禁/风险用语(如医疗功效极限词、金融收益承诺、"
        "政治敏感话题、\"最/第一/唯一/绝对\"等绝对化用语)\n"
        "3. image_match: 各小节配图是否与文字内容相关; 若某节配图状态是 missing 且"
        '\"配图连续缺失轮次\">=2, 这属于外部图片服务的已知限制, 不应仅因为缺图就判不通过\n'
        "4. readability: 分段、小标题、开头钩子、结尾引导是否符合公众号写作规范\n"
        "只返回 JSON, 不要任何其他文字:\n"
        '{"pass": true/false, "issues": [{"criterion": "topic_match|compliance|'
        'image_match|readability", "section": "对应小节标题, 或 title/closing, 或 null '
        '表示整体性问题", "detail": "问题描述", "fix_instruction": "具体怎么改"}]}'
    )
    user_extra = (
        "主题: {topic}\n要求: {requirements}\n\n标题: {title}\n\n{sections}\n\n"
        "结尾: {closing}\n\n配图连续缺失轮次: {image_miss_streak}"
    )
    return {"system": system, "user_extra": user_extra}


def reviser_prompt() -> dict[str, str]:
    """定向改写 prompt (只改写被点名章节; 供审核闭环 reviser 注入).

    Returns:
        {"system": ..., "user_extra": ...} — user_extra 含
        {topic}/{requirements}/{draft_json}/{issues} 槽位。
    """
    system = (
        "你是资深公众号编辑。这是一篇已写好的文章, 审核官指出了具体章节的问题。"
        "请只改写被指出的章节, 不要改动其他章节的措辞。\n"
        "只返回一个 JSON 数组, 每项对应一个需要改写的章节:\n"
        '[{"heading": "必须与原标题完全一致, 或 title/closing 表示改标题/结尾", '
        '"body": "新的正文(heading=title/closing 时这里放新标题/新结尾文本)", '
        '"image_brief": "可选, 只有需要换配图方向时才带这个字段"}]'
    )
    user_extra = (
        "主题: {topic}\n要求: {requirements}\n\n当前文章 JSON:\n{draft_json}\n\n"
        "审核指出以下具体章节问题, 请只改写涉及的章节:\n{issues}"
    )
    return {"system": system, "user_extra": user_extra}


def advise_prompt(article: str, inspect_report: dict[str, Any] | None = None) -> dict[str, str]:
    """文章改进建议 prompt (advise; 建议仅供参考, 发布门槛以 inspect 为准).

    Args:
        article: 文章全文。
        inspect_report: wechat_publish.inspect_article 的输出 (可选, 注入
            结构性阻塞/合规命中作为证据)。

    Returns:
        {"system": ..., "user": ...} — 输出契约: JSON 数组
        [{priority, area, detail, action}]。
    """
    system = (
        "你是公众号编辑顾问。基于文章与检查报告给出改进建议, 只做建议不改写。\n"
        "输出格式: 每条建议含优先级(high/medium/low)、领域(标题/开头/结构/合规/配图/结尾)、"
        "问题与具体动作。\n"
        "只返回一个 JSON 数组, 不要任何其他文字:\n"
        '[{"priority": "high", "area": "...", "detail": "...", "action": "..."}]'
    )
    user = f"文章:\n{article[:6000]}"
    if inspect_report:
        user += (
            f"\n\n检查报告:\n"
            f"标题长度: {inspect_report.get('title_length')} 字 "
            f"({'合规' if inspect_report.get('title_ok') else '超限'})"
            f"\nreadiness: {inspect_report.get('readiness')}"
        )
        hits = inspect_report.get("compliance", {}).get("hits") or []
        if hits:
            user += "\n违禁用语命中:\n" + "\n".join(
                f"- [{h['criterion']}] {h['keyword']}: …{h['snippet']}…" for h in hits[:10]
            )
    return {"system": system, "user": user}


# ── 确定性合规扫描 ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ComplianceHit:
    """一次违禁用语命中。

    Attributes:
        criterion: 违规类别 (absolute/medical/finance/overclaim/share-bait)。
        keyword: 命中的关键词。
        snippet: 命中处上下文 (±15 字符)。
        position: 命中位置 (字符偏移)。
    """

    criterion: str
    keyword: str
    snippet: str
    position: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "keyword": self.keyword,
            "snippet": self.snippet,
            "position": self.position,
        }


# (criterion, 关键词表) — 微信广告法/平台规则常见风险用语。
# 注意: 命中=风险提示, 不自动等于违规; 是否违规由发布方/人工复核确认。
_COMPLIANCE_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "absolute",
        (
            "最", "第一", "唯一", "绝对", "100%", "百分之百", "国家级", "世界级",
            "顶级", "极致", "首选", "全网", "史上", "空前", "绝无仅有", "最佳",
            "最好", "最强", "最低价", "全网最低",
        ),
    ),
    (
        "medical",
        (
            "治疗", "治愈", "根治", "药到病除", "包治", "疗效", "痊愈", "抗癌",
            "降糖", "降压", "消炎", "除根", "立竿见影",
        ),
    ),
    (
        "finance",
        (
            "稳赚", "保本", "无风险", "收益保证", "躺赚", "暴富", "翻倍赚",
            "理财高回报", "稳收益",
        ),
    ),
    (
        "overclaim",
        ("全网第一", "销量第一", "免费领取", "点击即得", "人人可做", "简单到爆", "零基础秒懂"),
    ),
    (
        "share-bait",
        ("转发必得", "不转不是", "分享抽奖", "转发抽奖", "必须转发", "不转后悔"),
    ),
]

_COMPILED_RULES: list[tuple[str, re.Pattern[str]]] = [
    (criterion, re.compile("|".join(re.escape(k) for k in keywords)))
    for criterion, keywords in _COMPLIANCE_RULES
]


def scan_compliance(text: str) -> list[ComplianceHit]:
    """扫描文本中的违禁/风险用语 (确定性, 无外部依赖).

    Args:
        text: 要扫描的文本 (标题/正文/摘要均可)。

    Returns:
        命中列表 (按位置排序)。空列表 = 未命中任何已知风险用语。

    Example:
        >>> hits = scan_compliance("全网最低价, 治愈你的烦恼")
        >>> {h.criterion for h in hits} == {"absolute", "medical"}
        True
    """
    hits: list[ComplianceHit] = []
    for criterion, pattern in _COMPILED_RULES:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            snippet = text[max(0, start - 15): end + 15].replace("\n", " ")
            hits.append(
                ComplianceHit(
                    criterion=criterion,
                    keyword=text[start:end],
                    snippet=snippet,
                    position=start,
                )
            )
    hits.sort(key=lambda h: h.position)
    return hits


def compliance_report(text: str) -> dict[str, Any]:
    """合规扫描报告 (供 inspect/advise/审核闭环当证据).

    Returns:
        {"pass": bool, "hits": [...], "criteria": [去重类别]}。
    """
    hits = scan_compliance(text)
    return {
        "pass": not hits,
        "hits": [h.to_dict() for h in hits],
        "criteria": sorted({h.criterion for h in hits}),
    }


__all__ = [
    "ComplianceHit",
    "advise_prompt",
    "compliance_report",
    "cover_prompt",
    "humanize_prompt",
    "infographic_prompt",
    "reviewer_prompt",
    "reviser_prompt",
    "scan_compliance",
    "title_prompt",
    "write_prompt",
]
