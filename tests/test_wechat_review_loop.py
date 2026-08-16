"""Tests for wechat_review_loop (写手↔审核↔打回闭环状态机, LLM 注入分离)."""

from __future__ import annotations

import asyncio

from oskill.wechat_review_loop import (
    ReviewIssue,
    WechatReviewLoop,
    merge_revision,
    needs_full_rewrite,
    parse_verdict,
)

_DRAFT = {
    "title": "标题A",
    "sections": [
        {"heading": "第一节", "body": "内容一", "image_brief": "图一"},
        {"heading": "第二节", "body": "内容二", "image_brief": "图二"},
    ],
    "closing": "结尾",
}


def _verdict(passed: bool, issues: list[dict] | None = None) -> dict:
    return {"pass": passed, "issues": issues or []}


def _run(loop: WechatReviewLoop, topic="T", req="R") -> dict:
    return asyncio.run(loop.run(topic, req))


def test_patch_round_then_pass():
    review_calls = {"n": 0}

    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        review_calls["n"] += 1
        if review_calls["n"] == 1:
            return _verdict(False, [{
                "criterion": "readability", "section": "第二节",
                "detail": "太短", "fix_instruction": "补充细节",
            }])
        return _verdict(True)

    async def reviser(draft, issues, topic, req):
        return [{"heading": "第二节", "body": "补充后的内容二"}]

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer, reviser=reviser))
    assert result["passed"] is True
    assert result["iterations"] == 2
    assert result["best_effort"] is False
    assert result["draft"]["sections"][1]["body"] == "补充后的内容二"
    actions = [r["action"] for r in result["action_log"]]
    assert actions == ["patch", "passed"]


def test_full_rewrite_on_topic_mismatch():
    writer_calls = {"n": 0}

    async def writer(topic, req, constraints):
        writer_calls["n"] += 1
        draft = dict(_DRAFT)
        draft["title"] = f"第{writer_calls['n']}版"
        return draft

    async def reviewer(draft, images, topic, req, miss_streak):
        if writer_calls["n"] == 1:
            return _verdict(False, [{
                "criterion": "topic_match", "section": None,
                "detail": "跑题", "fix_instruction": "重新围绕主题",
            }])
        return _verdict(True)

    async def reviser(draft, issues, topic, req):
        raise AssertionError("不应走 patch 分支")

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer, reviser=reviser))
    assert result["passed"] is True
    assert result["draft"]["title"] == "第2版"
    assert [r["action"] for r in result["action_log"]] == ["full_rewrite", "passed"]


def test_capped_best_effort_with_remaining_issues():
    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        return _verdict(False, [{
            "criterion": "readability", "section": "第一节",
            "detail": "不够好", "fix_instruction": "重写",
        }])

    async def reviser(draft, issues, topic, req):
        return [{"heading": "第一节", "body": "改写后"}]

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer,
                                   reviser=reviser, max_iterations=2))
    assert result["passed"] is False
    assert result["best_effort"] is True
    assert result["iterations"] == 2
    actions = [r["action"] for r in result["action_log"]]
    assert actions[-1] == "capped"
    assert result["issues"][0].detail == "不够好"


def test_patch_failed_does_not_crash():
    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        return _verdict(False, [{
            "criterion": "readability", "section": "第一节",
            "detail": "d", "fix_instruction": "f",
        }])

    async def reviser(draft, issues, topic, req):
        return None  # LLM 输出无法解析

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer,
                                   reviser=reviser, max_iterations=3))
    assert result["passed"] is False
    assert result["best_effort"] is True
    assert any(r["action"] == "patch_failed" for r in result["action_log"])


def test_writer_failure_returns_issue_not_crash():
    async def writer(topic, req, constraints):
        return None

    async def reviewer(draft, images, topic, req, miss_streak):
        raise AssertionError("writer 失败时不应调 reviewer")

    async def reviser(draft, issues, topic, req):
        raise AssertionError("writer 失败时不应调 reviser")

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer, reviser=reviser))
    assert result["draft"] is None
    assert result["passed"] is False
    assert result["issues"][0].criterion == "writer_output"


def test_missing_images_do_not_block():
    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        assert all(i["status"] == "missing" for i in images)
        return _verdict(True)

    async def reviser(draft, issues, topic, req):
        raise AssertionError

    loop = WechatReviewLoop(writer=writer, reviewer=reviewer, reviser=reviser)
    result = _run(loop)
    assert result["passed"] is True
    assert result["image_results"][0]["status"] == "missing"


def test_resolve_image_injected():
    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        assert images[0]["status"] == "ok"
        return _verdict(True)

    async def reviser(draft, issues, topic, req):
        raise AssertionError

    async def resolve(brief):
        return {"status": "ok", "path": f"/tmp/{brief}.png"}

    loop = WechatReviewLoop(writer=writer, reviewer=reviewer, reviser=reviser,
                            resolve_image=resolve)
    result = _run(loop)
    assert result["passed"] is True
    assert result["image_results"][0]["path"] == "/tmp/图一.png"


def test_unparseable_reviewer_treated_as_fail():
    async def writer(topic, req, constraints):
        return _DRAFT

    async def reviewer(draft, images, topic, req, miss_streak):
        return None  # 审核输出无法解析

    async def reviser(draft, issues, topic, req):
        return [{"heading": "第一节", "body": "x"}]

    result = _run(WechatReviewLoop(writer=writer, reviewer=reviewer,
                                   reviser=reviser, max_iterations=1))
    assert result["passed"] is False
    assert result["issues"][0].criterion == "reviewer_output"


def test_parse_verdict_and_needs_full_rewrite():
    passed, issues = parse_verdict(_verdict(False, [
        {"criterion": "topic_match", "section": None, "detail": "d"},
    ]))
    assert passed is False
    assert needs_full_rewrite(issues) is True
    assert parse_verdict(_verdict(True)) == (True, [])


def test_merge_revision_only_touches_named_sections():
    merged = merge_revision(_DRAFT, [
        {"heading": "第一节", "body": "新一"},
        {"heading": "title", "body": "新标题"},
        {"heading": "closing", "body": "新结尾"},
    ])
    assert merged["title"] == "新标题"
    assert merged["closing"] == "新结尾"
    assert merged["sections"][0]["body"] == "新一"
    assert merged["sections"][1]["body"] == "内容二"      # 未点名不动
    assert _DRAFT["title"] == "标题A"                      # 原稿不污染
