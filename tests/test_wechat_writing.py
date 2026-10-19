"""Tests for wechat_writing (prompt 工厂 + 确定性合规扫描)."""

from __future__ import annotations

import json

from oskill.wechat_writing import (
    advise_prompt,
    compliance_report,
    cover_prompt,
    humanize_prompt,
    infographic_prompt,
    scan_compliance,
    title_prompt,
    write_prompt,
)


def test_write_prompt_contract():
    p = write_prompt("AI 编程", audience="程序员", style="口语化", requirements="800字")
    assert "AI 编程" in p["user"]
    assert "目标读者: 程序员" in p["user"]
    assert "image_brief" in p["system"]          # 默认带配图 brief
    assert '"title"' in p["system"]              # JSON 契约
    assert '"sections"' in p["system"]
    assert '"closing"' in p["system"]


def test_write_prompt_no_image_brief():
    p = write_prompt("主题", with_image_brief=False)
    assert "image_brief" not in p["system"]


def test_title_prompt_clamps_and_hook():
    p = title_prompt("# 文章\n正文", n_candidates=99, hook_level=9)
    assert "10 个" in p["system"]                 # 钳制到上限
    assert "强冲突" in p["system"]                # hook_level=3 描述
    assert "文章" in p["user"]
    p2 = title_prompt("正文", n_candidates=2, hook_level=1)
    assert "2 个" in p2["system"]
    assert "平实直接" in p2["system"]


def test_humanize_prompt_rules():
    p = humanize_prompt("首先, 总而言之这是一段很长的正确的废话。")
    assert "首先/其次/最后" in p["system"]
    assert "原文" in p["user"]
    assert "正确废话" in p["system"] or "空泛金句" in p["system"]


def test_cover_prompt_contract():
    p = cover_prompt("AI 写作", style="极简", palette="黑白")
    assert "AI 写作" in p["user"]
    assert "2.35:1" in p["system"]               # 封面比例契约
    assert "aspect_ratio" in p["system"]


def test_infographic_prompt_contract():
    p = infographic_prompt("公众号排版", ["要点1", "要点2", "要点3"])
    assert "要点1" in p["user"]
    assert "max_points" in p["system"]


def test_advise_prompt_with_report():
    report = {
        "title_length": 70,
        "title_ok": False,
        "readiness": {"ready": False, "targets": ["title"], "blockers": ["cover"]},
        "compliance": {"hits": [{"criterion": "absolute", "keyword": "最", "snippet": "最好"}]},
    }
    p = advise_prompt("# 标题\n正文", inspect_report=report)
    assert "70 字" in p["user"]
    assert "绝对" in p["user"] or "违禁" in p["user"]


def test_scan_compliance_hits_categories():
    text = "全网最低价, 治愈你的烦恼, 稳赚不赔"
    hits = scan_compliance(text)
    criteria = {h.criterion for h in hits}
    assert "absolute" in criteria
    assert "medical" in criteria
    assert "finance" in criteria
    assert all(h.snippet and h.position >= 0 for h in hits)


def test_scan_compliance_sorted_and_empty():
    assert scan_compliance("完全正常的文章内容") == []
    hits = scan_compliance("最好 然后 最低价")
    positions = [h.position for h in hits]
    assert positions == sorted(positions)


def test_compliance_report_shape():
    report = compliance_report("顶级服务, 治疗一切")
    assert report["pass"] is False
    assert report["criteria"] == ["absolute", "medical"]
    assert report["hits"][0]["keyword"] == "顶级"


def test_compliance_report_pass():
    report = compliance_report("今天天气不错")
    assert report["pass"] is True
    assert report["hits"] == []
    assert report["criteria"] == []


def test_prompt_outputs_parseable_contracts():
    # 关键: prompt 里的 JSON 契约片段本身要合法 (system 以契约行结尾)
    p = write_prompt("主题")
    sys = p["system"]
    start = sys.find('{"title"')
    contract = json.loads(sys[start:])
    assert set(contract) == {"title", "sections", "closing"}
    assert "image_brief" in contract["sections"][0]
